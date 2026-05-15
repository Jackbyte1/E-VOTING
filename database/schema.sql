PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    institution_id TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'admin')),
    reg_number TEXT,
    course TEXT,
    has_voted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS elections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'closed',
    is_active INTEGER NOT NULL DEFAULT 0,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    ,FOREIGN KEY (created_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    election_id INTEGER NOT NULL,
    position TEXT NOT NULL,
    manifesto TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (election_id) REFERENCES elections (id)
);

CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    candidate_id INTEGER NOT NULL,
    election_id INTEGER NOT NULL,
    position TEXT NOT NULL,
    voter_blind_hash TEXT NOT NULL,
    encrypted_vote TEXT NOT NULL,
    encrypted_key TEXT NOT NULL,
    vote_hash TEXT NOT NULL UNIQUE,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (candidate_id) REFERENCES candidates (id),
    FOREIGN KEY (election_id) REFERENCES elections (id),
    UNIQUE (user_id, election_id, position)
);

CREATE TRIGGER IF NOT EXISTS prevent_vote_update
BEFORE UPDATE ON votes
BEGIN
    SELECT RAISE(ABORT, 'Votes are append-only and cannot be updated');
END;

CREATE TRIGGER IF NOT EXISTS prevent_vote_delete
BEFORE DELETE ON votes
BEGIN
    SELECT RAISE(ABORT, 'Votes are append-only and cannot be deleted');
END;

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    user_id INTEGER,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    previous_hash TEXT NOT NULL,
    current_hash TEXT NOT NULL UNIQUE,
    merkle_root TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS merkle_roots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id INTEGER NOT NULL,
    merkle_root TEXT NOT NULL,
    computed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (election_id) REFERENCES elections (id)
);

CREATE TABLE IF NOT EXISTS otp_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    otp_code TEXT NOT NULL,
    expiry_time TEXT NOT NULL,
    is_used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_candidates_election ON candidates (election_id);
CREATE INDEX IF NOT EXISTS idx_votes_election ON votes (election_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_time ON audit_logs (timestamp);
CREATE INDEX IF NOT EXISTS idx_otp_sessions_user ON otp_sessions (user_id);
