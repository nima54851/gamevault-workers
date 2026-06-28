-- ============================================================
-- GameVault GM 后台 完整 Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS players (
    uid TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    nickname TEXT DEFAULT '',
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    combat_power INTEGER DEFAULT 0,
    coins INTEGER DEFAULT 0,
    diamonds INTEGER DEFAULT 0,
    is_vip INTEGER DEFAULT 0,
    vip_expire_at INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',   -- active | banned_7d | banned_perm
    ban_reason TEXT DEFAULT '',
    ban_expire_at INTEGER DEFAULT 0,
    recharge_total INTEGER DEFAULT 0,
    login_count INTEGER DEFAULT 0,
    last_login_at INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT 0,
    updated_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS player_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    item_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    acquired_at INTEGER DEFAULT 0,
    UNIQUE(uid, item_id)
);

CREATE TABLE IF NOT EXISTS player_login_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    ip TEXT,
    device TEXT,
    login_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mail_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    sender TEXT DEFAULT '系统',
    items TEXT DEFAULT '',   -- JSON: [{"id":"item_001","name":"金币","count":100}]
    is_all INTEGER DEFAULT 0, -- 1=全服
    target_uids TEXT DEFAULT '', -- JSON array of uids, empty=all
    status TEXT DEFAULT 'draft', -- draft | sent | cancelled
    created_at INTEGER DEFAULT 0,
    sent_at INTEGER DEFAULT 0,
    expire_at INTEGER DEFAULT 0,
    read_count INTEGER DEFAULT 0,
    receive_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mail_box (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    mail_id TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    received_at INTEGER DEFAULT 0,
    UNIQUE(uid, mail_id)
);

CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    priority TEXT DEFAULT 'normal', -- normal | important | urgent
    img_url TEXT DEFAULT '',
    link_url TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    start_at INTEGER DEFAULT 0,
    end_at INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS shop_banners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    img_url TEXT NOT NULL,
    link_url TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    start_at INTEGER DEFAULT 0,
    end_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mall_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    desc TEXT DEFAULT '',
    price_type TEXT NOT NULL,  -- coins | diamonds | rmb
    price INTEGER DEFAULT 0,
    category TEXT DEFAULT 'item',
    stock INTEGER DEFAULT -1,  -- -1=无限
    sold_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    desc TEXT DEFAULT '',
    event_type TEXT DEFAULT 'limited', -- limited | daily | weekly | permanent
    start_at INTEGER DEFAULT 0,
    end_at INTEGER DEFAULT 0,
    conditions TEXT DEFAULT '', -- JSON: {"min_level":10,"vip_only":false}
    rewards TEXT DEFAULT '',     -- JSON array of rewards
    status TEXT DEFAULT 'draft',
    created_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS game_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    type TEXT DEFAULT 'string',  -- string | int | bool | json
    label TEXT DEFAULT '',
    desc TEXT DEFAULT '',
    updated_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS whitelist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    whitelist_type TEXT DEFAULT 'test', -- test | channel | dev
    note TEXT DEFAULT '',
    created_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS drop_tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    items TEXT NOT NULL,  -- JSON: [{"item_id":"x","item_name":"y","weight":10,"min":1,"max":1}]
    updated_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT,
    item TEXT,
    amount INTEGER,
    type TEXT,
    ts INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS player_recharge_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    order_id TEXT UNIQUE,
    amount INTEGER DEFAULT 0,
    currency TEXT DEFAULT 'CNY',
    status TEXT DEFAULT 'pending',
    paid_at INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS daily_stats (
    stat_date TEXT PRIMARY KEY,
    dau INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    recharge_count INTEGER DEFAULT 0,
    recharge_amount INTEGER DEFAULT 0,
    vip_count INTEGER DEFAULT 0,
    avg_online INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alert_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT DEFAULT 'warning', -- info | warning | critical
    resolved INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT 0,
    resolved_at INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_players_nickname ON players(nickname);
CREATE INDEX IF NOT EXISTS idx_players_status ON players(status);
CREATE INDEX IF NOT EXISTS idx_mail_status ON mail(status);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_stats_date ON daily_stats(stat_date);
CREATE INDEX IF NOT EXISTS idx_alert_resolved ON alert_log(resolved, severity);

-- ============================================================
-- 初始游戏配置数据
-- ============================================================
INSERT OR IGNORE INTO game_config (key, value, type, label, desc) VALUES
('match_enabled', 'true', 'bool', '全服匹配开关', '关闭后所有匹配请求将被拒绝'),
('chat_global_enabled', 'true', 'bool', '世界聊天开关', '全服聊天功能'),
('shop_event_active', 'true', 'bool', '商城活动开关', '限时商城活动'),
('whitelist_mode', 'false', 'bool', '白名单模式', '开启后仅白名单用户可登录'),
('resource_version', '1.0.0', 'string', '资源版本号', '客户端热更版本'),
('hotfix_enabled', 'false', 'bool', '热更开关', '是否启用热更新'),
('max_level', '100', 'int', '玩家最大等级', '服务器允许的最高等级'),
('daily_limit_coins', '10000', 'int', '每日金币上限', '每日获取金币上限');
