-- Run this code in the Supabase SQL Editor exactly as is to prepare your database!

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    username TEXT,
    warnings INTEGER DEFAULT 0,
    role TEXT DEFAULT 'member',
    first_seen TEXT,
    reputation INTEGER DEFAULT 0,
    is_banned BOOLEAN DEFAULT FALSE,
    banned_reason TEXT,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS groups (
    chat_id TEXT PRIMARY KEY,
    name TEXT DEFAULT 'Unknown Group',
    rules TEXT DEFAULT 'No rules set yet. Use /setrules to set them.',
    welcome_message TEXT DEFAULT 'Welcome {name}! 👋',
    welcome_type TEXT DEFAULT 'text',
    welcome_file_id TEXT DEFAULT '',
    leave_message TEXT DEFAULT 'Goodbye {name}!',
    leave_type TEXT DEFAULT 'text',
    leave_file_id TEXT DEFAULT '',
    antispam INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    member_count INTEGER DEFAULT 0,
    filter_count INTEGER DEFAULT 0,
    language TEXT DEFAULT 'en',
    strict_mode BOOLEAN DEFAULT FALSE,
    log_channel_id TEXT,
    max_warnings INTEGER DEFAULT 3,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS filters (
    id SERIAL PRIMARY KEY,
    chat_id TEXT,
    trigger TEXT,
    filter_data TEXT,
    UNIQUE(chat_id, trigger)
);

CREATE TABLE IF NOT EXISTS bad_words (
    id SERIAL PRIMARY KEY,
    chat_id TEXT,
    word TEXT,
    UNIQUE(chat_id, word)
);

CREATE TABLE IF NOT EXISTS global_bans (
    user_id TEXT PRIMARY KEY,
    reason TEXT,
    banned_by TEXT,
    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    event TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Note: The setup is now safely fully customized for Render and Supabase with advanced features!
