-- GameVault D1 Schema

CREATE TABLE IF NOT EXISTS users (
    uid TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    coins INTEGER DEFAULT 0,
    is_vip INTEGER DEFAULT 0,
    created_at INTEGER
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT,
    item TEXT,
    amount INTEGER,
    type TEXT,
    ts INTEGER
);

CREATE TABLE IF NOT EXISTS leaderboard (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT,
    uid TEXT,
    username TEXT,
    score INTEGER,
    ts INTEGER
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id TEXT PRIMARY KEY,
    game_id TEXT,
    host_uid TEXT,
    status TEXT,
    players TEXT,
    created_at INTEGER,
    data TEXT
);

CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    file_path TEXT,
    thumbnail TEXT,
    is_vip INTEGER DEFAULT 0,
    category TEXT,
    plays INTEGER DEFAULT 0,
    created_at INTEGER
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_tx_uid ON transactions(uid);
CREATE INDEX IF NOT EXISTS idx_lb_game ON leaderboard(game_id);
