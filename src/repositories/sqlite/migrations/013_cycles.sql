-- Slice A1: flexible planning cycles.
-- A cycle is a date range the household plans around (replaces the fixed
-- Mon→Sun week). Only one cycle per household is 'active' at a time;
-- the old one is archived when a new one is created.
CREATE TABLE IF NOT EXISTS cycles (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active', 'archived')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cycles_household
    ON cycles(household_id, start_date);
