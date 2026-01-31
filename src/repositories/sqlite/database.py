"""
Database initialization and migration utilities.
Clean Architecture - Repository Layer Implementation.
"""
import sqlite3
import os
import uuid
from pathlib import Path
from typing import Optional, List
from datetime import datetime

class DatabaseManager:
    """Manages SQLite database initialization and migrations."""
    
    def __init__(self, db_path: str = "meal_planner.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent / "migrations"
        
    def initialize_database(self) -> None:
        """Initialize database with schema and run migrations."""
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        
        # Create database connection
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create migrations table if it doesn't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Run migrations
            self._run_migrations(conn)
            
            conn.commit()
    
    def _run_migrations(self, conn: sqlite3.Connection) -> None:
        """Run all pending migrations."""
        # Get applied migrations
        cursor = conn.execute("SELECT version FROM schema_migrations")
        applied_migrations = {row[0] for row in cursor.fetchall()}
        
        # Get all migration files
        migration_files = sorted([
            f for f in os.listdir(self.migrations_dir) 
            if f.endswith('.sql')
        ])
        
        # Run pending migrations
        for migration_file in migration_files:
            version = migration_file.replace('.sql', '')
            
            if version not in applied_migrations:
                print(f"Running migration: {migration_file}")
                
                # Read and execute migration
                migration_path = self.migrations_dir / migration_file
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                
                # Execute migration in transaction
                conn.executescript(migration_sql)
                
                # Record migration as applied
                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?)",
                    (version,)
                )
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        return conn
    
    def generate_id(self) -> str:
        """Generate unique ID for database records."""
        return str(uuid.uuid4())
    
    def reset_database(self) -> None:
        """Reset database by dropping all tables and re-initializing."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.initialize_database()
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT version FROM schema_migrations ORDER BY applied_at"
            )
            return [row[0] for row in cursor.fetchall()]
    
    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create database backup."""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.backup_{timestamp}"
        
        # Create backup using SQLite backup API
        with sqlite3.connect(self.db_path) as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
        
        return backup_path
