-- Add weight tracking table for TDEE estimation and progress monitoring

-- Weight tracking table for weigh-ins and progress
CREATE TABLE IF NOT EXISTS weight_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    weight DECIMAL(5,2) NOT NULL, -- Weight in lbs or kg
    notes TEXT, -- Optional notes about weigh-in conditions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, date) -- One weigh-in per day per user
);

-- Index for efficient weight tracking queries
CREATE INDEX IF NOT EXISTS idx_weight_logs_user_date ON weight_logs(user_id, date);

-- Add trigger for weight logs
CREATE TRIGGER IF NOT EXISTS update_weight_logs_timestamp 
    AFTER UPDATE ON weight_logs
    BEGIN
        UPDATE weight_logs SET created_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;
