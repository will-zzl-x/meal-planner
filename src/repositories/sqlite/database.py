"""
Database initialization, connection management, and migrations.

The backend is chosen by the constructor's `db_path` argument:
  - A SQLite file path ("meal_planner.db", "/data/x.db", ":memory:") →
    local SQLite via SQLAlchemy.
  - A full SQLAlchemy URL containing "://" ("postgresql://...",
    "sqlite:///..." ) → that backend.

Repositories keep using the same execute() API they had with raw
sqlite3 — `?` placeholders, tuple params, dict-accessible rows — via
a thin wrapper around SQLAlchemy. That lets us swap SQLite for
Postgres (hosted on Neon) for production without touching repo code
or test code.
"""
import os
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection as SAConnection, Engine


def _normalize_url(raw: str) -> str:
    """Map common Postgres URL forms to the SQLAlchemy 2.0 driver name."""
    if raw.startswith("postgres://"):
        return "postgresql+psycopg://" + raw[len("postgres://"):]
    if raw.startswith("postgresql://") and "+" not in raw.split("://", 1)[0]:
        return "postgresql+psycopg://" + raw[len("postgresql://"):]
    return raw


def _split_sql_statements(script: str) -> List[str]:
    """Split a multi-statement SQL script on `;`, respecting string literals
    and line comments. Used to feed migrations into Postgres one statement
    at a time (SQLite has executescript()  natively)."""
    out, buf = [], []
    in_str: Optional[str] = None
    i, n = 0, len(script)
    while i < n:
        ch = script[i]
        if in_str:
            buf.append(ch)
            if ch == in_str:
                if i + 1 < n and script[i + 1] == in_str:
                    buf.append(script[i + 1])
                    i += 2
                    continue
                in_str = None
        elif ch in ("'", '"'):
            in_str = ch
            buf.append(ch)
        elif ch == "-" and i + 1 < n and script[i + 1] == "-":
            while i < n and script[i] != "\n":
                buf.append(script[i])
                i += 1
            continue
        elif ch == ";":
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    if buf:
        out.append("".join(buf))
    return out


class _Row:
    """sqlite3.Row-like wrapper: supports both `row[0]` (positional) and
    `row['col_name']` (key access), plus iteration."""
    __slots__ = ("_row", "_mapping")

    def __init__(self, sa_row):
        self._row = sa_row
        self._mapping = sa_row._mapping

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._row[key]
        return self._mapping[key]

    def __iter__(self):
        return iter(self._row)

    def __len__(self):
        return len(self._row)

    def __contains__(self, key) -> bool:
        if isinstance(key, int):
            return 0 <= key < len(self._row)
        return key in self._mapping

    def keys(self):
        return list(self._mapping.keys())


class _Cursor:
    """Mimics the sqlite3.Cursor API the repositories rely on.

    Can be constructed in two ways:
      - From an SA Result (returned by `_Connection.execute()`): already
        pre-populated, supports fetch*/rowcount/iteration.
      - From an SA Connection (returned by `_Connection.cursor()`): empty,
        supports a subsequent `execute()` then fetch*/iteration.
    """

    def __init__(self, conn_or_result):
        if isinstance(conn_or_result, SAConnection):
            self._sa_conn: Optional[SAConnection] = conn_or_result
            self._result = None
        else:
            self._sa_conn = None
            self._result = conn_or_result
        self._update_rowcount()

    def execute(self, sql: str, params: Sequence[Any] = ()) -> "_Cursor":
        if self._sa_conn is None:
            raise RuntimeError("This cursor was created from a result and cannot execute.")
        if params:
            translated, param_dict = _Connection._translate_placeholders(sql, params)
            self._result = self._sa_conn.execute(text(translated), param_dict)
        else:
            self._result = self._sa_conn.execute(text(sql))
        self._update_rowcount()
        return self

    def fetchone(self):
        if self._result is None:
            return None
        row = self._result.fetchone()
        return _Row(row) if row is not None else None

    def fetchall(self):
        if self._result is None:
            return []
        return [_Row(r) for r in self._result.fetchall()]

    def __iter__(self):
        if self._result is None:
            return iter(())
        return (_Row(r) for r in self._result)

    @property
    def rowcount(self) -> int:
        return self._rowcount

    def _update_rowcount(self) -> None:
        if self._result is not None:
            try:
                self._rowcount = self._result.rowcount
            except Exception:
                self._rowcount = -1
        else:
            self._rowcount = -1


class _Connection:
    """Wraps a SQLAlchemy Connection so repositories can keep writing
    `conn.execute("... WHERE x = ?", (val,))` regardless of backend.

    - `?` placeholders are translated to `:p0, :p1, ...` and the params
      tuple is packed into a dict before SQLAlchemy sees it.
    - Returned rows are SQLAlchemy `RowMapping` objects, which support
      `row['col_name']` access (same as sqlite3.Row used to).
    - Acts as a context manager: commits on clean exit, rolls back on
      error, then returns the underlying connection to the pool.
    """

    def __init__(self, sa_conn: SAConnection, dialect: str):
        self._conn = sa_conn
        self.dialect = dialect

    def execute(self, sql: str, params: Sequence[Any] = ()) -> _Cursor:
        if params:
            translated_sql, param_dict = self._translate_placeholders(sql, params)
            result = self._conn.execute(text(translated_sql), param_dict)
        else:
            result = self._conn.execute(text(sql))
        return _Cursor(result)

    def cursor(self) -> _Cursor:
        """Return an empty cursor bound to this connection (sqlite3 parity)."""
        return _Cursor(self._conn)

    def executescript(self, script: str) -> None:
        """Run a multi-statement SQL script. Used by the migration runner."""
        if self.dialect == "sqlite":
            raw = self._conn.connection.driver_connection
            raw.executescript(script)
        else:
            for stmt in _split_sql_statements(script):
                if stmt.strip():
                    self._conn.execute(text(stmt))

    def commit(self) -> None:
        try:
            self._conn.commit()
        except Exception:
            pass

    def rollback(self) -> None:
        try:
            self._conn.rollback()
        except Exception:
            pass

    @staticmethod
    def _translate_placeholders(sql: str, params: Sequence[Any]):
        param_dict: dict = {}
        counter = [0]

        def repl(_match) -> str:
            i = counter[0]
            param_dict[f"p{i}"] = params[i]
            counter[0] += 1
            return f":p{i}"

        translated = re.sub(r"\?", repl, sql)
        return translated, param_dict

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        try:
            self._conn.close()
        except Exception:
            pass


class DatabaseManager:
    """Initializes and connects to the meal-planner database.

    `db_path` accepts either a SQLite file path (backward-compatible) or
    a full SQLAlchemy URL (anything containing "://").
    """

    _engines: dict = {}  # url → Engine (cached so each URL has one pool)

    def __init__(self, db_path: str = "meal_planner.db"):
        if "://" in db_path:
            self.url = _normalize_url(db_path)
        else:
            self.url = f"sqlite:///{db_path}"
        self.db_path = db_path
        self.dialect = "sqlite" if self.url.startswith("sqlite") else "postgresql"
        self.migrations_dir = Path(__file__).parent / "migrations"
        self._engine = self._get_engine()

    def _get_engine(self) -> Engine:
        if self.url in DatabaseManager._engines:
            return DatabaseManager._engines[self.url]
        connect_args: dict = {}
        if self.dialect == "sqlite":
            connect_args["check_same_thread"] = False
        engine = create_engine(self.url, connect_args=connect_args, future=True)
        DatabaseManager._engines[self.url] = engine
        return engine

    def initialize_database(self) -> None:
        """Create the migrations table and run pending migrations.
        Safe to call repeatedly — repos call it from their constructors."""
        if self.dialect == "sqlite":
            sqlite_file = self.url[len("sqlite:///"):]
            if sqlite_file and sqlite_file != ":memory:":
                parent = os.path.dirname(sqlite_file)
                if parent:
                    os.makedirs(parent, exist_ok=True)

        with self.get_connection() as conn:
            if self.dialect == "sqlite":
                conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._run_migrations(conn)
            conn.commit()

    def _run_migrations(self, conn: _Connection) -> None:
        cursor = conn.execute("SELECT version FROM schema_migrations")
        applied = {row["version"] for row in cursor.fetchall()}

        migration_files = sorted(
            f for f in os.listdir(self.migrations_dir) if f.endswith(".sql")
        )

        for migration_file in migration_files:
            version = migration_file.replace(".sql", "")
            if version in applied:
                continue
            print(f"Running migration: {migration_file}")
            with open(self.migrations_dir / migration_file) as f:
                sql = f.read()
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (version,),
            )

    def get_connection(self) -> _Connection:
        """Open a new pooled connection. Caller should use as a context
        manager so it commits and is returned to the pool on exit."""
        sa_conn = self._engine.connect()
        if self.dialect == "sqlite":
            sa_conn.execute(text("PRAGMA foreign_keys = ON"))
        return _Connection(sa_conn, self.dialect)

    def generate_id(self) -> str:
        return str(uuid.uuid4())

    def reset_database(self) -> None:
        """Drop the local file (SQLite) or schema (Postgres) and re-init.
        For tests / dev only."""
        if self.dialect == "sqlite":
            sqlite_file = self.url[len("sqlite:///"):]
            if sqlite_file and sqlite_file != ":memory:" and os.path.exists(sqlite_file):
                os.remove(sqlite_file)
        else:
            with self.get_connection() as conn:
                conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
                conn.execute("CREATE SCHEMA public")
                conn.commit()
        self.initialize_database()

    def get_applied_migrations(self) -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT version FROM schema_migrations ORDER BY applied_at"
            )
            return [row["version"] for row in cursor.fetchall()]

    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """SQLite-only backup (Postgres has its own tooling)."""
        if self.dialect != "sqlite":
            raise NotImplementedError("backup_database is SQLite-only")
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.backup_{timestamp}"
        sqlite_file = self.url[len("sqlite:///"):]
        with sqlite3.connect(sqlite_file) as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
        return backup_path
