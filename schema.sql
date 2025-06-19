CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT,
    progress TEXT,
    deadline TEXT,
    estimate REAL,
    actual REAL,
    memo TEXT,
    cost TEXT,
    start TEXT,
    done INTEGER,
    parent TEXT,
    children TEXT,
    shown INTEGER,
    del INTEGER,
    created_at TEXT,
    updated_at TEXT
);
