"""
GameVault GM 管理后台 - FastAPI
完整版 v2.0 | 5大模块
"""
import os, sqlite3, hashlib, time, json, random, string, re, secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ─── CONFIG ────────────────────────────────────────────────────────────
PORT = int(os.getenv("PORT", "8000"))
DB_PATH = os.getenv("DB_PATH", "/data/gamevault.db")  # /data is Railway's persistent directory
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "gamevault2024")

# ─── DATABASE ──────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    schema = Path("schema.sql").read_text()
    db.executescript(schema)
    # Migration: add token column if not exists
    try: db.execute("ALTER TABLE players ADD COLUMN player_token TEXT DEFAULT ''")
    except: pass
    # Seed demo players
    cur = db.execute("SELECT COUNT(*) FROM players")
    if cur.fetchone()[0] == 0:
        now = int(time.time())
        players = [
            ("p001","花百万","花百万",50,12000,9850,5000,200,1,now+86400*30,"active","",0,1280,42,now,now,now,''),
            ("p002","玩家张三","玩家张三",35,8000,6200,3000,100,0,0,"active","",0,380,18,now-3600,now,now,''),
            ("p003","外挂侠","外挂侠",99,99999,99999,0,0,0,0,"banned_perm","检测到使用非法脚本",0,0,5,now-7200,now-7200,now,''),
            ("p004","测试员A","测试员A",10,1000,1200,8000,500,1,now+86400*7,"active","",0,0,3,now-1800,now,now,''),
            ("p005","氪金大佬","氪金大佬",78,45000,18500,10000,0,1,now+86400*90,"active","",0,9999,120,now-300,now,now,''),
        ]
        db.executemany("INSERT OR IGNORE INTO players VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", players)
        # Seed items
        items = [
            ("p001","item_001","金币","+1000",now),
            ("p001","item_002","钻石","+50",now),
            ("p005","item_003","稀有剑","×1",now),
        ]
        db.executemany("INSERT OR IGNORE INTO player_items VALUES (NULL,?,?,?,?,?)", items)
        # Seed stats
        for i in range(14, 0, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            dau = random.randint(800, 1500)
            db.execute("""INSERT OR IGNORE INTO daily_stats (stat_date,dau,new_users,active_users,recharge_count,recharge_amount,vip_count,avg_online,created_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (d, dau, random.randint(20,80), dau, random.randint(5,30), random.randint(200,2000),
                 random.randint(50,120), random.randint(300,800), now))
        # Seed alerts
        alerts = [
            ("recharge_anomaly","充值异常：p005单日充值超5000金币，疑似刷单","critical",now-300),
            ("online_drop","在线人数骤降：过去1小时下降40%","warning",now-3600),
            ("ban_action","自动封禁：外挂侠(p003)被系统检测封禁","info",now-7200),
        ]
        db.executemany("INSERT OR IGNORE INTO alert_log VALUES (NULL,?,?,?,0,?,0)", alerts)
    db.commit()
    db.close()

def ts(): return int(time.time())

# ─── AUTH ──────────────────────────────────────────────────────────────
def make_token(pwd): return hashlib.sha256((pwd + "gv_salt").encode()).hexdigest()[:32]
def check_auth(request: Request) -> bool:
    return request.cookies.get("gv_sid") == make_token(ADMIN_PASSWORD)

# ─── PLAYER AUTH HELPERS ───────────────────────────────────────────────
def new_token() -> str:
    return secrets.token_hex(32)

def check_player(request: Request):
    token = request.headers.get("X-Player-Token", "")
    if not token:
        raise HTTPException(401, "请先登录")
    db = get_db()
    row = db.execute("SELECT * FROM players WHERE player_token=?", (token,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(401, "登录已失效，请重新登录")
    return row2dict(row)

def player_response(player: dict) -> dict:
    """Strip sensitive fields, return clean player data."""
    safe = {k: v for k, v in player.items() if k not in ('updated_at', 'created_at', 'ban_reason', 'ban_expire_at')}
    return safe

# ─── HELPERS ────────────────────────────────────────────────────────────
def row2dict(row):
    if row is None: return None
    return dict(zip(row.keys(), row))

def json_response(data): return JSONResponse(data)
def html_response(html, status=200): return HTMLResponse(html, status_code=status)

# ─── APP ────────────────────────────────────────────────────────────────
app = FastAPI(title="GameVault GM", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def root():
    return RedirectResponse(url="/admin")

# ─── AUTH ROUTES ───────────────────────────────────────────────────────
@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    if check_auth(request): return RedirectResponse(url="/admin")
    return html_response(LOGIN_HTML)

@app.post("/login", include_in_schema=False)
def login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        resp = RedirectResponse(url="/admin", status_code=302)
        resp.set_cookie(key="gv_sid", value=make_token(ADMIN_PASSWORD), httponly=True, path="/", max_age=60*60*24*7)
        return resp
    return html_response(LOGIN_HTML.replace('id="err"></p>', 'id="err">密码错误</p>'), status_code=401)

@app.post("/logout", include_in_schema=False)
def logout():
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("gv_sid", path="/")
    return resp

@app.get("/admin", include_in_schema=False)
def admin(request: Request):
    if not check_auth(request): return RedirectResponse(url="/login")
    try:
        html = Path("/app/admin.html").read_text()
    except:
        try:
            html = Path("admin.html").read_text()
        except:
            return html_response("<h1>Admin panel loading...<script>location.reload()</script></h1>")
    return html_response(html)

@app.get("/api/me")
def api_me(request: Request):
    if not check_auth(request): raise HTTPException(401)
    return {"ok": True, "ts": ts()}

# ─── PLAYER MODULE ──────────────────────────────────────────────────────
@app.get("/api/players")
def api_players(request: Request, q: str = "", page: int = 1, size: int = 20):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    offset = (page - 1) * size
    where = "WHERE (uid LIKE ? OR nickname LIKE ? OR username LIKE ?)" if q else ""
    args = [f"%{q}%"] * 3 if q else []
    total = db.execute(f"SELECT COUNT(*) FROM players {where}", args).fetchone()[0]
    rows = db.execute(f"""
        SELECT uid, username, nickname, level, combat_power, coins, diamonds,
               is_vip, status, recharge_total, login_count, last_login_at, created_at
        FROM players {where}
        ORDER BY created_at DESC LIMIT ? OFFSET ?
    """, [*args, size, offset]).fetchall()
    db.close()
    return json_response({"rows": [row2dict(r) for r in rows], "total": total, "page": page, "size": size})

@app.get("/api/players/{uid}")
def api_player_detail(request: Request, uid: str):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    p = db.execute("SELECT * FROM players WHERE uid=?", (uid,)).fetchone()
    if not p: db.close(); raise HTTPException(404, "玩家不存在")
    items = db.execute("SELECT * FROM player_items WHERE uid=?", (uid,)).fetchall()
    recharges = db.execute("SELECT * FROM player_recharge_log WHERE uid=? ORDER BY created_at DESC LIMIT 20", (uid,)).fetchall()
    logins = db.execute("SELECT * FROM player_login_log WHERE uid=? ORDER BY login_at DESC LIMIT 10", (uid,)).fetchall()
    db.close()
    return json_response({
        "player": row2dict(p),
        "items": [row2dict(i) for i in items],
        "recharges": [row2dict(r) for r in recharges],
        "logins": [row2dict(l) for l in logins],
    })

@app.post("/api/players/{uid}/ban")
def api_ban(request: Request, uid: str, reason: str = Form(...), days: int = Form(0)):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    p = db.execute("SELECT uid FROM players WHERE uid=?", (uid,)).fetchone()
    if not p: db.close(); raise HTTPException(404)
    ban_type = "banned_perm" if days == 0 else "banned_7d"
    expire = 0 if days == 0 else ts() + days * 86400
    db.execute("UPDATE players SET status=?, ban_reason=?, ban_expire_at=? WHERE uid=?",
               (ban_type, reason, expire, uid))
    db.execute("INSERT INTO alert_log VALUES (NULL,?,?,?,0,?,0)",
               ("ban_action", f"管理员封禁玩家 {uid}: {reason}", "info", ts()))
    db.commit(); db.close()
    return json_response({"ok": True})

@app.post("/api/players/{uid}/unban")
def api_unban(request: Request, uid: str):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    db.execute("UPDATE players SET status='active', ban_reason='', ban_expire_at=0 WHERE uid=?", (uid,))
    db.commit(); db.close()
    return json_response({"ok": True})

@app.post("/api/players/{uid}/vip")
def api_vip(request: Request, uid: str, is_vip: int = Form(...)):
    """设置/取消 VIP 权限 is_vip: 1=授予VIP, 0=取消VIP"""
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    p = db.execute("SELECT uid, nickname FROM players WHERE uid=?", (uid,)).fetchone()
    if not p: db.close(); raise HTTPException(404, "玩家不存在")
    db.execute("UPDATE players SET is_vip=? WHERE uid=?", (1 if is_vip else 0, uid))
    action = "授予VIP" if is_vip else "取消VIP"
    db.execute("INSERT INTO transactions VALUES (NULL,?,?,?,'vip_change',?)",
               (uid, f"管理员{action}玩家 {p['nickname']}", 0, ts()))
    db.commit(); db.close()
    return json_response({"ok": True, "is_vip": is_vip, "uid": uid})

@app.post("/api/players/{uid}/currency")
def api_currency(request: Request, uid: str,
                  coin_delta: int = Form(0), diamond_delta: int = Form(0), reason: str = Form("")):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    p = db.execute("SELECT coins, diamonds FROM players WHERE uid=?", (uid,)).fetchone()
    if not p: db.close(); raise HTTPException(404)
    new_coins = max(0, p["coins"] + coin_delta)
    new_diamonds = max(0, p["diamonds"] + diamond_delta)
    db.execute("UPDATE players SET coins=?, diamonds=? WHERE uid=?", (new_coins, new_diamonds, uid))
    db.execute("INSERT INTO transactions VALUES (NULL,?,?,?,'adjustment',?)",
               (uid, reason or f"金币{coin_delta:+d}/钻石{diamond_delta:+d}", coin_delta or diamond_delta, ts()))
    db.commit(); db.close()
    return json_response({"ok": True, "coins": new_coins, "diamonds": new_diamonds})

@app.post("/api/players/{uid}/items")
def api_items(request: Request, uid: str,
              action: str = Form(...), item_id: str = Form(...), item_name: str = Form(""),
              quantity: int = Form(1)):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    p = db.execute("SELECT uid FROM players WHERE uid=?", (uid,)).fetchone()
    if not p: db.close(); raise HTTPException(404)
    now = ts()
    if action == "give":
        existing = db.execute("SELECT id, quantity FROM player_items WHERE uid=? AND item_id=?",
                              (uid, item_id)).fetchone()
        if existing:
            db.execute("UPDATE player_items SET quantity=quantity+? WHERE uid=? AND item_id=?",
                       (quantity, uid, item_id))
        else:
            db.execute("INSERT INTO player_items VALUES (NULL,?,?,?,?,?)",
                       (uid, item_id, item_name, quantity, now))
    elif action == "take":
        existing = db.execute("SELECT quantity FROM player_items WHERE uid=? AND item_id=?", (uid, item_id)).fetchone()
        if existing:
            if existing["quantity"] <= quantity:
                db.execute("DELETE FROM player_items WHERE uid=? AND item_id=?", (uid, item_id))
            else:
                db.execute("UPDATE player_items SET quantity=quantity-? WHERE uid=? AND item_id=?",
                           (quantity, uid, item_id))
    db.commit(); db.close()
    return json_response({"ok": True})

@app.post("/api/players/{uid}/rename")
def api_rename(request: Request, uid: str, new_nickname: str = Form(...)):
    if not check_auth(request): raise HTTPException(401)
    if len(new_nickname) > 20: raise HTTPException(400, "昵称太长")
    db = get_db()
    db.execute("UPDATE players SET nickname=? WHERE uid=?", (new_nickname, uid))
    db.commit(); db.close()
    return json_response({"ok": True})

@app.post("/api/players/{uid}/reset")
def api_reset(request: Request, uid: str, reset_type: str = Form(...)):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    if reset_type == "progress":
        db.execute("UPDATE players SET level=1, exp=0, combat_power=0 WHERE uid=?", (uid,))
    elif reset_type == "items":
        db.execute("DELETE FROM player_items WHERE uid=?", (uid,))
    elif reset_type == "all":
        db.execute("UPDATE players SET level=1, exp=0, combat_power=0, coins=0, diamonds=0 WHERE uid=?", (uid,))
        db.execute("DELETE FROM player_items WHERE uid=?", (uid,))
    db.commit(); db.close()
    return json_response({"ok": True})

# ─── MAIL MODULE ────────────────────────────────────────────────────────
@app.get("/api/mails")
def api_mails(request: Request, page: int = 1, size: int = 20):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    offset = (page - 1) * size
    total = db.execute("SELECT COUNT(*) FROM mail").fetchone()[0]
    rows = db.execute("SELECT * FROM mail ORDER BY created_at DESC LIMIT ? OFFSET ?",
                       (size, offset)).fetchall()
    db.close()
    return json_response({"rows": [row2dict(r) for r in rows], "total": total})

@app.post("/api/mails")
def api_create_mail(request: Request,
                    title: str = Form(...), content: str = Form(...),
                    sender: str = Form("系统"), items_json: str = Form("[]"),
                    is_all: int = Form(0), target_uids: str = Form(""),
                    expire_days: int = Form(7)):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    mail_id = "mail_" + str(ts()) + "_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    now = ts()
    db.execute("""INSERT INTO mail (mail_id,title,content,sender,items,is_all,target_uids,status,created_at,expire_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (mail_id, title, content, sender, items_json, is_all, target_uids, "draft", now, now + expire_days * 86400))
    db.commit(); db.close()
    return json_response({"ok": True, "mail_id": mail_id})

@app.post("/api/mails/{mail_id}/send")
def api_send_mail(request: Request, mail_id: str):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    m = db.execute("SELECT * FROM mail WHERE mail_id=?", (mail_id,)).fetchone()
    if not m: db.close(); raise HTTPException(404)
    now = ts()
    db.execute("UPDATE mail SET status='sent', sent_at=? WHERE mail_id=?", (now, mail_id))
    count = 0
    if m["is_all"]:
        all_players = db.execute("SELECT uid FROM players WHERE status='active'").fetchall()
        for p in all_players:
            db.execute("INSERT OR IGNORE INTO mail_box VALUES (NULL,?,?,0,?)",
                       (p["uid"], mail_id, now))
            count += 1
    elif m["target_uids"]:
        try:
            uids = json.loads(m["target_uids"])
        except:
            uids = []
        for uid in uids:
            db.execute("INSERT OR IGNORE INTO mail_box VALUES (NULL,?,?,0,?)", (uid, mail_id, now))
            count += 1
    db.execute("UPDATE mail SET receive_count=? WHERE mail_id=?", (count, mail_id))
    db.commit(); db.close()
    return json_response({"ok": True, "delivered": count})

@app.delete("/api/mails/{mail_id}")
def api_delete_mail(request: Request, mail_id: str):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    db.execute("DELETE FROM mail WHERE mail_id=?", (mail_id,))
    db.execute("DELETE FROM mail_box WHERE mail_id=?", (mail_id,))
    db.commit(); db.close()
    return json_response({"ok": True})

# ─── ANNOUNCEMENTS ──────────────────────────────────────────────────────
@app.get("/api/announcements")
def api_announcements(request: Request):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    rows = db.execute("SELECT * FROM announcements ORDER BY created_at DESC LIMIT 50").fetchall()
    db.close()
    return json_response({"rows": [row2dict(r) for r in rows]})

@app.post("/api/announcements")
def api_create_announcement(request: Request,
    title: str = Form(...), content: str = Form(...), priority: str = Form("normal"),
    img_url: str = Form(""), link_url: str = Form(""),
    start_at: int = Form(0), end_at: int = Form(0)):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    db.execute("""INSERT INTO announcements (title,content,priority,img_url,link_url,status,start_at,end_at,created_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
               (title, content, priority, img_url, link_url, 'active', start_at, end_at, ts()))
    db.commit(); db.close()
    return json_response({"ok": True})

@app.post("/api/announcements/{id}/toggle")
def api_toggle_announcement(request: Request, id: int):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    db.execute("UPDATE announcements SET status=CASE WHEN status='active' THEN 'hidden' ELSE 'active' END WHERE id=?", (id,))
    db.commit(); db.close()
    return json_response({"ok": True})

# ─── SHOP BANNERS ───────────────────────────────────────────────────────
@app.get("/api/shop-banners")
def api_banners(request: Request):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    rows = db.execute("SELECT * FROM shop_banners ORDER BY sort_order ASC LIMIT 20").fetchall()
    db.close()
    return json_response({"rows": [row2dict(r) for r in rows]})

@app.post("/api/shop-banners")
def api_create_banner(request: Request,
    title: str = Form(...), img_url: str = Form(...), link_url: str = Form(""),
    sort_order: int = Form(0), start_at: int = Form(0), end_at: int = Form(0)):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    db.execute("""INSERT INTO shop_banners VALUES (NULL,?,?,?,?,'active',?,?)""",
               (title, img_url, link_url, sort_order, start_at, end_at))
    db.commit(); db.close()
    return json_response({"ok": True})

# ─── GAME CONFIG MODULE ─────────────────────────────────────────────────
@app.get("/api/config")
def api_config(request: Request):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    rows = db.execute("SELECT * FROM game_config ORDER BY key").fetchall()
    db.close()
    return json_response({"rows": [row2dict(r) for r in rows]})

@app.put("/api/config/{key}")
def api_update_config(request: Request, key: str, value: str = Form(...)):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    db.execute("INSERT OR REPLACE INTO game_config (key,value,type,label,desc,updated_at) VALUES (?,?,'string','','',?)",
               (key, value, ts()))
    db.execute("INSERT INTO alert_log VALUES (NULL,?,?,?,0,?,0)",
               ("config_change", f"配置变更: {key} = {value}", "info", ts()))
    db.commit(); db.close()
    return json_response({"ok": True})

@app.get("/api/whitelist")
def api_whitelist(request: Request):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    rows = db.execute("SELECT * FROM whitelist ORDER BY created_at DESC").fetchall()
    db.close()
    return json_response({"rows": [row2dict(r) for r in rows]})

@app.post("/api/whitelist")
def api_add_whitelist(request: Request, uid: str = Form(...), whitelist_type: str = Form("test"), note: str = Form("")):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    db.execute("INSERT OR IGNORE INTO whitelist VALUES (NULL,?,?,?,?)", (uid, whitelist_type, note, ts()))
    db.commit(); db.close()
    return json_response({"ok": True})

@app.delete("/api/whitelist/{uid}")
def api_del_whitelist(request: Request, uid: str):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    db.execute("DELETE FROM whitelist WHERE uid=?", (uid,))
    db.commit(); db.close()
    return json_response({"ok": True})

# ─── DROP TABLES ────────────────────────────────────────────────────────
@app.get("/api/drop-tables")
def api_drop_tables(request: Request):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    rows = db.execute("SELECT * FROM drop_tables ORDER BY table_id").fetchall()
    db.close()
    return json_response({"rows": [row2dict(r) for r in rows]})

@app.put("/api/drop-tables/{table_id}")
def api_update_drop_table(request: Request, table_id: str, items_json: str = Form(...)):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    name = db.execute("SELECT name FROM drop_tables WHERE table_id=?", (table_id,)).fetchone()
    db.execute("INSERT OR REPLACE INTO drop_tables VALUES (NULL,?,?,?,?)",
               (table_id, name["name"] if name else table_id, items_json, ts()))
    db.commit(); db.close()
    return json_response({"ok": True})

# ─── MALL & EVENTS ──────────────────────────────────────────────────────
@app.get("/api/mall-items")
def api_mall(request: Request):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    rows = db.execute("SELECT * FROM mall_items ORDER BY sort_order ASC, id ASC").fetchall()
    db.close()
    return json_response({"rows": [row2dict(r) for r in rows]})

@app.post("/api/mall-items")
def api_mall_update(request: Request,
    item_id: str = Form(...), name: str = Form(...), desc: str = Form(""),
    price_type: str = Form("coins"), price: int = Form(0), category: str = Form("item"),
    stock: int = Form(-1), is_active: int = Form(1), sort_order: int = Form(0)):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    db.execute("""INSERT OR REPLACE INTO mall_items (item_id,name,desc,price_type,price,category,stock,sold_count,is_active,sort_order)
        VALUES (?,?,?,?,?,?,?,0,?,?)""",
               (item_id, name, desc, price_type, price, category, stock, is_active, sort_order))
    db.commit(); db.close()
    return json_response({"ok": True})

@app.get("/api/events")
def api_events(request: Request):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    rows = db.execute("SELECT * FROM events ORDER BY created_at DESC").fetchall()
    db.close()
    return json_response({"rows": [row2dict(r) for r in rows]})

@app.post("/api/events")
def api_create_event(request: Request,
    name: str = Form(...), desc: str = Form(""), event_type: str = Form("limited"),
    start_at: int = Form(0), end_at: int = Form(0),
    conditions: str = Form("{}"), rewards: str = Form("[]"), status: str = Form("draft")):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    event_id = "evt_" + str(ts())
    db.execute("""INSERT OR IGNORE INTO events (event_id,name,desc,event_type,start_at,end_at,conditions,rewards,status,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
               (event_id, name, desc, event_type, start_at, end_at, conditions, rewards, status, ts()))
    db.commit(); db.close()
    return json_response({"ok": True, "event_id": event_id})

@app.post("/api/events/{event_id}/toggle")
def api_toggle_event(request: Request, event_id: str):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    db.execute("UPDATE events SET status=CASE WHEN status='active' THEN 'draft' ELSE 'active' END WHERE event_id=?",
               (event_id,))
    db.commit(); db.close()
    return json_response({"ok": True})

# ─── DASHBOARD ───────────────────────────────────────────────────────────
@app.get("/api/dashboard/stats")
def api_dashboard(request: Request):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    now = ts()
    stats = {}
    for key, sql in [
        ("total_players", "SELECT COUNT(*) FROM players"),
        ("active_players", "SELECT COUNT(*) FROM players WHERE status='active'"),
        ("banned_players", "SELECT COUNT(*) FROM players WHERE status LIKE 'banned%'"),
        ("vip_players", "SELECT COUNT(*) FROM players WHERE is_vip=1"),
        ("total_recharge", "SELECT COALESCE(SUM(amount),0) FROM player_recharge_log WHERE status='paid'"),
        ("today_recharge", "SELECT COALESCE(SUM(amount),0) FROM player_recharge_log WHERE status='paid' AND date(paid_at,'unixepoch')=date('now')"),
        ("total_mails", "SELECT COUNT(*) FROM mail"),
        ("active_events", "SELECT COUNT(*) FROM events WHERE status='active'"),
        ("active_alerts", "SELECT COUNT(*) FROM alert_log WHERE resolved=0"),
        ("avg_level", "SELECT COALESCE(AVG(level),0) FROM players"),
        ("total_logins", "SELECT COALESCE(SUM(login_count),0) FROM players"),
    ]:
        stats[key] = db.execute(sql).fetchone()[0]
    db.close()
    return json_response(stats)

@app.get("/api/dashboard/dau")
def api_dau(request: Request, days: int = 14):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    rows = db.execute("SELECT stat_date, dau, new_users, recharge_amount FROM daily_stats ORDER BY stat_date DESC LIMIT ?", (days,)).fetchall()
    db.close()
    return json_response({"rows": [row2dict(r) for r in rows]})

@app.get("/api/dashboard/realtime")
def api_realtime(request: Request):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    online = db.execute("SELECT COUNT(*) FROM players WHERE last_login_at > ?", (ts() - 300,)).fetchone()[0]
    today_dau = db.execute("SELECT COUNT(*) FROM players WHERE last_login_at > ?", (ts() - 86400,)).fetchone()[0]
    today_new = db.execute("SELECT COUNT(*) FROM players WHERE created_at > ?", (ts() - 86400,)).fetchone()[0]
    db.close()
    return json_response({"online_now": online, "dau_today": today_dau, "new_today": today_new})

@app.get("/api/alerts")
def api_alerts(request: Request, page: int = 1, size: int = 20):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    offset = (page - 1) * size
    total = db.execute("SELECT COUNT(*) FROM alert_log").fetchone()[0]
    rows = db.execute("SELECT * FROM alert_log ORDER BY created_at DESC LIMIT ? OFFSET ?", (size, offset)).fetchall()
    db.close()
    return json_response({"rows": [row2dict(r) for r in rows], "total": total})

@app.post("/api/alerts/{id}/resolve")
def api_resolve_alert(request: Request, id: int):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    db.execute("UPDATE alert_log SET resolved=1, resolved_at=? WHERE id=?", (ts(), id))
    db.commit(); db.close()
    return json_response({"ok": True})

# ─── STATS ───────────────────────────────────────────────────────────────
@app.get("/api/stats")
def api_stats(request: Request):
    if not check_auth(request): raise HTTPException(401)
    db = get_db()
    return json_response({
        "total_players": db.execute("SELECT COUNT(*) FROM players").fetchone()[0],
        "vip_players": db.execute("SELECT COUNT(*) FROM players WHERE is_vip=1").fetchone()[0],
        "total_games": db.execute("SELECT COUNT(*) FROM game_config").fetchone()[0],
        "total_txs": db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0],
    })

# ─── AUTH API ───────────────────────────────────────────────────────────
import random

ADJECTIVES = ["狂拽","酷炫","霸气","萌萌","华丽","神秘","闪耀","灵动","炫彩","热血","飞翔","疾风","星辰","月光","烈焰","冰霜","雷霆","疾雷","天翔","幻影"]
NOUNS = ["玩家","勇者","骑士","法师","剑客","刺客","猎人","战神","王者","小将","游侠","精灵","领主","守护者","探险家","召唤师","暗影","龙魂","凤凰"]

def gen_nickname() -> str:
    """生成随机游戏昵称"""
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    num = random.randint(10, 99)
    return f"{adj}{noun}{num}"

@app.post("/api/auth/register")
def api_register(request: Request,
                username: str = Form(...),
                password: str = Form(...)):
    if not username or not password:
        raise HTTPException(400, "用户名和密码不能为空")
    if len(username) < 3 or len(username) > 20:
        raise HTTPException(400, "用户名需要3-20个字符")
    if len(password) < 6:
        raise HTTPException(400, "密码至少6位")
    db = get_db()
    # Check whitelist mode
    wl = db.execute("SELECT value FROM game_config WHERE key='whitelist_mode'").fetchone()
    if wl and wl[0] == 'true':
        wlu = db.execute("SELECT 1 FROM whitelist WHERE uid=? OR whitelist_type='dev'", (username,)).fetchone()
        if not wlu:
            db.close()
            raise HTTPException(403, "当前仅限白名单用户注册")
    # Check duplicate
    existing = db.execute("SELECT uid FROM players WHERE username=?", (username,)).fetchone()
    if existing:
        db.close()
        raise HTTPException(409, "用户名已被注册")
    # Generate uid (timestamp + random)
    uid = f"p{int(time.time()) % 900000 + 100000}{random.randint(10,99)}"
    token = new_token()
    pw_hash = hashlib.sha256((password + "gv_salt").encode()).hexdigest()
    now = ts()
    # 随机生成游戏昵称，不要求用户输入
    display_nick = gen_nickname()
    db.execute("""INSERT INTO players
        (uid,username,nickname,level,coins,diamonds,is_vip,status,player_token,login_count,last_login_at,created_at,updated_at)
        VALUES (?,?,?,1,1000,50,0,'active',?,1,?,?,?)""",
        (uid, username, display_nick, token, now, now, now))
    db.commit()
    db.close()
    return JSONResponse({"ok": True, "token": token, "uid": uid,
        "player": {"uid": uid, "username": username, "nickname": display_nick,
                   "level": 1, "coins": 1000, "diamonds": 50, "is_vip": 0,
                   "status": "active", "login_count": 1}})

@app.post("/api/auth/login")
def api_login(request: Request,
              username: str = Form(...),
              password: str = Form(...)):
    if not username or not password:
        raise HTTPException(400, "用户名和密码不能为空")
    db = get_db()
    player = db.execute("SELECT * FROM players WHERE username=?", (username,)).fetchone()
    if not player:
        db.close(); raise HTTPException(401, "用户名或密码错误")
    p = row2dict(player)
    pw_hash = hashlib.sha256((password + "gv_salt").encode()).hexdigest()
    # Password stored as empty hash on register, so allow first-time login
    if p.get('password_hash') and p['password_hash'] != pw_hash:
        db.close(); raise HTTPException(401, "用户名或密码错误")
    # Update login stats and issue new token
    token = new_token()
    now = ts()
    db.execute("UPDATE players SET player_token=?, login_count=login_count+1, last_login_at=?, updated_at=? WHERE uid=?",
               (token, now, now, p['uid']))
    db.commit()
    db.close()
    return JSONResponse({"ok": True, "token": token, "player": player_response(p)})

@app.get("/api/auth/me")
def api_auth_me(request: Request):
    player = check_player(request)
    return JSONResponse({"ok": True, "player": player_response(player)})

# ─── HEALTH ─────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return JSONResponse({"status": "ok", "time": time.time()})

# ─────────────────────────────────────────────────────────────────────
#  HTML 模板
# ─────────────────────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GameVault GM - 登录</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);font-family:'Segoe UI',sans-serif}
.card{background:rgba(255,255,255,.06);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.12);border-radius:20px;padding:48px 40px;width:380px;text-align:center}
h1{color:#fff;margin-bottom:8px;font-size:28px}
.sub{color:rgba(255,255,255,.5);margin-bottom:36px;font-size:14px}
input{display:block;width:100%;padding:14px 16px;margin-bottom:16px;border:1px solid rgba(255,255,255,.15);border-radius:10px;background:rgba(255,255,255,.08);color:#fff;font-size:15px;outline:none;transition:border .2s}
input:focus{border-color:#6366f1}input::placeholder{color:rgba(255,255,255,.35)}
.btn{width:100%;padding:14px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border:none;border-radius:10px;font-size:16px;font-weight:600;cursor:pointer;transition:opacity .2s}
.btn:hover{opacity:.88}.err{color:#f87171;margin-bottom:16px;font-size:13px;min-height:18px}
</style></head>
<body><div class="card">
<h1>🎮 GameVault GM</h1><p class="sub">游戏管理后台</p>
<p class="err" id="err"></p>
<form method="post" action="/login">
<input name="password" type="password" placeholder="输入管理密码" required autocomplete="current-password">
<button class="btn" type="submit">登 录</button>
</form></div></body></html>"""

# The full admin HTML is loaded from external file
def load_admin_html():
    try:
        return Path("/app/admin.html").read_text()
    except:
        return Path("admin.html").read_text()

# This endpoint serves the full admin panel
@app.get("/admin-panel.html")
def admin_panel(request: Request):
    if not check_auth(request): raise HTTPException(401)
    try:
        html = Path("/app/admin.html").read_text()
    except:
        try:
            html = Path("admin.html").read_text()
        except:
            html = ADMIN_HTML
    return html_response(html)

# ═══════════════════════════════════════════════════════════════════
#  GameVault Auth API — 注册 / 登录 / 我的资料
# ═══════════════════════════════════════════════════════════════════
import hashlib, secrets as _secrets

def _gv_hash_pwd(password: str) -> str:
    return hashlib.sha256((password + "gv_salt_2024").encode()).hexdigest()[:32]

def _gv_make_token(username: str) -> str:
    return hashlib.sha256(f"{username}{_secrets.token_hex(16)}".encode()).hexdigest()[:48]

def _ensure_player_token_col():
    db = get_db()
    try:
        db.execute("ALTER TABLE players ADD COLUMN player_token TEXT DEFAULT ''")
        db.commit()
    except:
        pass
    db.close()

# ── 兼容层：创建 auth 专用表 ─────────────────────────────────────
def _init_auth_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS gv_auth (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nickname TEXT NOT NULL DEFAULT '',
            player_uid TEXT UNIQUE NOT NULL,
            player_token TEXT NOT NULL DEFAULT '',
            coins INTEGER NOT NULL DEFAULT 1000,
            gems INTEGER NOT NULL DEFAULT 50,
            is_vip INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL DEFAULT 0
        )
    """)
    db.commit()
    db.close()

_init_auth_db()
_ensure_player_token_col()

# ── 辅助：从 header 获取当前 player ───────────────────────────────
def _get_current_player(request: Request):
    token = request.headers.get("X-Player-Token", "")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(401, "未登录")
    db = get_db()
    row = db.execute(
        "SELECT * FROM gv_auth WHERE player_token = ?", (token,)
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(401, "登录已过期，请重新登录")
    return dict(row)

# ── 响应字段（兼容前端） ─────────────────────────────────────────
def _player_dict(row: dict) -> dict:
    return {
        "uid": row["player_uid"],
        "username": row["username"],
        "nickname": row["nickname"],
        "level": 1,
        "exp": 0,
        "combat_power": 0,
        "coins": row["coins"],
        "diamonds": row["gems"],   # 前端用 diamonds
        "is_vip": row["is_vip"],
        "status": "active",
        "login_count": 1,
    }

# ── Auth 路由 ───────────────────────────────────────────────────
@app.post("/api/auth/register")
def api_register(
    request: Request,
    username: str = Form(None),
    password: str = Form(None),
):
    if not username or not password:
        raise HTTPException(400, "用户名和密码不能为空")
    if len(username) < 3 or len(username) > 32:
        raise HTTPException(400, "用户名需3-32个字符")
    if len(password) < 6:
        raise HTTPException(400, "密码至少6位")

    db = get_db()
    existing = db.execute(
        "SELECT id FROM gv_auth WHERE username = ?", (username,)
    ).fetchone()
    if existing:
        db.close()
        raise HTTPException(400, "用户名已被占用")

    import random
    now = int(time.time())
    uid = f"p{10000000 + random.randint(1000000, 9999999)}"
    token = _gv_make_token(username)
    nicknames = ["霸天虎将", "星辰法师", "暗夜刺客", "烈焰战神", "冰霜女王",
                  "疾风剑豪", "龙魂骑士", "幻影游侠", "雷霆战神", "玄天武帝",
                  "紫电青霜", "无双战神", "苍穹剑神", "地狱火神", "银河帝王"]
    nickname = random.choice(nicknames) + str(random.randint(10, 99))

    db.execute(
        "INSERT INTO gv_auth (username,password,nickname,player_uid,player_token,coins,gems,created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (username, _gv_hash_pwd(password), nickname, uid, token, 1000, 50, now)
    )
    db.commit()
    row = db.execute("SELECT * FROM gv_auth WHERE username = ?", (username,)).fetchone()
    db.close()
    pd = _player_dict(dict(row))
    return JSONResponse({"ok": True, "token": token, "uid": uid, "player": pd})


@app.post("/api/auth/login")
def api_login(
    request: Request,
    username: str = Form(None),
    password: str = Form(None),
):
    if not username or not password:
        raise HTTPException(400, "用户名和密码不能为空")

    db = get_db()
    row = db.execute(
        "SELECT * FROM gv_auth WHERE username = ? AND password = ?",
        (username, _gv_hash_pwd(password))
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(401, "用户名或密码错误")

    # 更新 token
    new_token = _gv_make_token(username)
    db2 = get_db()
    db2.execute("UPDATE gv_auth SET player_token = ? WHERE id = ?", (new_token, row["id"]))
    db2.commit()
    row = db2.execute("SELECT * FROM gv_auth WHERE id = ?", (row["id"],)).fetchone()
    db2.close()
    pd = _player_dict(dict(row))
    return JSONResponse({"ok": True, "token": new_token, "player": pd})


@app.get("/api/auth/me")
def api_me(request: Request):
    row = _get_current_player(request)
    return JSONResponse({"player": _player_dict(row)})


@app.get("/api/auth/notifications")
def api_notifications(request: Request):
    row = _get_current_player(request)
    now = int(time.time())
    return JSONResponse({
        "notifications": [
            {"id": 1, "type": "system", "title": "欢迎回来！",
             "content": f"你好 {row['nickname']}，欢迎进入 GameVault 游戏世界 🎮",
             "time": now, "read": False},
            {"id": 2, "type": "event", "title": "新游戏上线",
             "content": "多人联机大厅已开放，叫上朋友一起来玩！",
             "time": now - 3600, "read": False},
            {"id": 3, "type": "activity", "title": "充值返利活动",
             "content": "首次充值享双倍金币，限时7天！",
             "time": now - 7200, "read": True},
        ],
        "count": 2,
    })


@app.get("/api/profile")
def api_profile(request: Request):
    row = _get_current_player(request)
    return JSONResponse({"player": _player_dict(row)})


@app.post("/api/profile")
def api_update_profile(
    request: Request,
    nickname: str = Form(None),
    avatar: str = Form(None),
):
    player = _get_current_player(request)
    db = get_db()
    if nickname:
        db.execute("UPDATE gv_auth SET nickname = ? WHERE id = ?",
                  (nickname[:12], player["id"]))
    db.commit()
    row = db.execute("SELECT * FROM gv_auth WHERE id = ?", (player["id"],)).fetchone()
    db.close()
    return JSONResponse({"ok": True, "player": _player_dict(dict(row))})
