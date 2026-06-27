"""
GameVault 管理后端 - FastAPI
访问：http://localhost:8000/admin
"""
import os
import sqlite3
import hashlib
import time
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ─── CONFIG ────────────────────────────────────────────────────────────
PORT = int(os.getenv("PORT", "8000"))
DB_PATH = os.getenv("DB_PATH", "./gamevault.db")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
COOKIE_SECRET = os.getenv("COOKIE_SECRET", "gv-secret-2024")

# ─── DATABASE ──────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT DEFAULT '',
            coins INTEGER DEFAULT 0,
            is_vip INTEGER DEFAULT 0,
            created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT,
            item TEXT,
            amount INTEGER DEFAULT 0,
            type TEXT,
            ts INTEGER
        );
        CREATE TABLE IF NOT EXISTS games (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT DEFAULT '',
            file_path TEXT DEFAULT '',
            is_vip INTEGER DEFAULT 0,
            category TEXT DEFAULT '',
            plays INTEGER DEFAULT 0,
            created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            uid TEXT,
            username TEXT DEFAULT '',
            score INTEGER DEFAULT 0,
            ts INTEGER
        );
    """)
    db.commit()

    # Seed test data if empty
    cur = db.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        now = int(time.time())
        db.executemany(
            "INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)",
            [
                ("u001","test_user","",100,0,now),
                ("u002","vip_player","",500,1,now),
                ("u003","game_master","",0,1,now),
            ]
        )
        db.executemany(
            "INSERT OR IGNORE INTO transactions (uid,item,amount,type,ts) VALUES (?,?,?,?,?)",
            [
                ("u001","金币充值",100,"deposit",now),
                ("u002","VIP月卡",0,"purchase",now),
                ("u001","游戏奖励",50,"reward",now),
            ]
        )
        db.executemany(
            "INSERT OR IGNORE INTO games VALUES (?,?,?,?,?,?,?,?)",
            [
                ("snake","贪吃蛇","经典贪吃蛇","games/snake.html",0,"休闲",128,now),
                ("flappy","Flappy鸟","飞行闯关","games/flappy.html",1,"飞行",64,now),
                ("2048","2048","益智合并","games/2048.html",0,"益智",256,now),
                ("tetris","俄罗斯方块","经典方块","games/tetris.html",0,"经典",88,now),
            ]
        )
        db.commit()
    db.close()

# ─── AUTH ──────────────────────────────────────────────────────────────
def make_token(pwd: str) -> str:
    return str(abs(hash(pwd + COOKIE_SECRET)) % 10**12)

def check_auth(request: Request) -> bool:
    return request.cookies.get("gv_sid") == make_token(ADMIN_PASSWORD)

# ─── APP ────────────────────────────────────────────────────────────────
app = FastAPI(title="GameVault Admin API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── LOGIN PAGE HTML ───────────────────────────────────────────────────
LOGIN_HTML = """<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GameVault 管理登录</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);font-family:'Segoe UI',sans-serif}
.card{background:rgba(255,255,255,.06);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.12);border-radius:20px;padding:48px 40px;width:380px;text-align:center}
h1{color:#fff;margin-bottom:8px;font-size:28px}.sub{color:rgba(255,255,255,.5);margin-bottom:36px;font-size:14px}
input{display:block;width:100%;padding:14px 16px;margin-bottom:16px;border:1px solid rgba(255,255,255,.15);border-radius:10px;background:rgba(255,255,255,.08);color:#fff;font-size:15px;outline:none;box-sizing:border-box}
input:focus{border-color:#6366f1}input::placeholder{color:rgba(255,255,255,.35)}
.btn{width:100%;padding:14px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border:none;border-radius:10px;font-size:16px;font-weight:600;cursor:pointer}
.btn:hover{opacity:.88}.err{color:#f87171;margin-bottom:16px;font-size:13px;min-height:18px}
</style></head>
<body><div class="card">
<h1>🎮 GameVault</h1><p class="sub">管理后台登录</p>
<p class="err" id="err"></p>
<form method="post" action="/login">
<input name="password" type="password" placeholder="输入管理密码" required autocomplete="current-password">
<button class="btn" type="submit">登 录</button>
</form>
</div></body></html>"""

DASH_HTML = """<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GameVault 管理后台</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:#0f0f1a;color:#e2e8f0;min-height:100vh}
.top{background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:18px 32px;display:flex;align-items:center;justify-content:space-between}
.top h1{font-size:20px;color:#fff}.badge{background:rgba(255,255,255,.2);color:#fff;padding:4px 14px;border-radius:20px;font-size:13px;cursor:pointer;border:none}
.main{padding:24px 32px;max-width:1200px;margin:0 auto}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:28px}
.card{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:22px}
.card .lbl{color:rgba(255,255,255,.4);font-size:12px;margin-bottom:6px;text-transform:uppercase}
.card .val{font-size:34px;font-weight:700}
.card.users .val{color:#34d399}.card.vip .val{color:#fbbf24}
.card.games .val{color:#60a5fa}.card.tx .val{color:#f472b6}
.section{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:22px;margin-bottom:18px}
.section h2{color:#fff;font-size:15px;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid rgba(255,255,255,.06)}
table{width:100%%;border-collapse:collapse;font-size:14px}
th{text-align:left;color:rgba(255,255,255,.4);font-weight:500;padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.06)}
td{padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.04)}
tr:hover td{background:rgba(255,255,255,.03)}
.vip-badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600}
.vip-badge.yes{background:rgba(251,191,36,.2);color:#fbbf24}
.vip-badge.no{background:rgba(255,255,255,.07);color:rgba(255,255,255,.35)}
.btn-d{background:#ef4444;color:#fff;border:none;padding:5px 12px;border-radius:8px;cursor:pointer;font-size:13px}
.btn-d:hover{background:#dc2626}.btn-g{background:#22c55e;color:#fff;border:none;padding:5px 12px;border-radius:8px;cursor:pointer;font-size:13px}
.coin{color:#fbbf24;font-weight:600}
input.s{padding:8px 14px;border:1px solid rgba(255,255,255,.12);border-radius:8px;background:rgba(255,255,255,.06);color:#fff;font-size:14px;width:220px}
input.s::placeholder{color:rgba(255,255,255,.3)}.loading{color:rgba(255,255,255,.4);padding:20px}
.msg{position:fixed;top:20px;right:20px;padding:12px 20px;border-radius:10px;font-size:14px;z-index:1000;animation:fade .3s}
.msg.ok{background:#065f46;color:#6ee7b7}.msg.err{background:#7f1d1d;color:#fca5a5}
@keyframes fade{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}
a.refresh{color:#60a5fa;text-decoration:none;font-size:13px;margin-left:12px}
</style></head>
<body>
<div class="top">
  <h1>🎮 GameVault 管理后台</h1>
  <div style="display:flex;gap:10px">
    <span class="badge">● 在线</span>
    <form method="post" action="/logout" style="display:inline"><button class="badge" type="submit">退出</button></form>
  </div>
</div>
<div class="main">
  <div class="grid">
    <div class="card users"><div class="lbl">用户总数</div><div class="val" id="s-users">-</div></div>
    <div class="card vip"><div class="lbl">VIP用户</div><div class="val" id="s-vips">-</div></div>
    <div class="card games"><div class="lbl">收录游戏</div><div class="val" id="s-games">-</div></div>
    <div class="card tx"><div class="lbl">交易记录</div><div class="val" id="s-txs">-</div></div>
  </div>
  <div class="section">
    <h2>👥 用户管理<a href="javascript:loadUsers()" class="refresh">↻</a>
      <input class="s" placeholder="搜索用户名..." id="q" oninput="loadUsers()" style="float:right"></h2>
    <div id="user-tbl"><div class="loading">加载中...</div></div>
  </div>
  <div class="section">
    <h2>📊 交易记录<a href="javascript:loadTxs()" class="refresh">↻</a></h2>
    <div id="tx-tbl"><div class="loading">加载中...</div></div>
  </div>
</div>
<script>
async function api(url, opts={}) {
  const r = await fetch(url, {...opts, credentials:'same-origin'});
  if(r.status===401) { location.href='/admin'; return null; }
  if(!r.ok && r.status!==200) throw new Error(r.status);
  return r;
}
function msg(t,type='ok'){
  const el=document.createElement('div'); el.className='msg '+type; el.textContent=t;
  document.body.appendChild(el); setTimeout(()=>el.remove(),3000);
}
async function loadStats(){
  const r=await api('/api/stats'); if(!r)return;
  const d=await r.json();
  document.getElementById('s-users').textContent=d.users;
  document.getElementById('s-vips').textContent=d.vips;
  document.getElementById('s-games').textContent=d.games;
  document.getElementById('s-txs').textContent=d.txs;
}
async function loadUsers(){
  const q=encodeURIComponent(document.getElementById('q').value||'');
  const el=document.getElementById('user-tbl');
  el.innerHTML='<div class="loading">加载中...</div>';
  const r=await api('/api/users?q='+q); if(!r)return;
  el.innerHTML=await r.text();
}
async function loadTxs(){
  const el=document.getElementById('tx-tbl');
  el.innerHTML='<div class="loading">加载中...</div>';
  const r=await api('/api/transactions'); if(!r)return;
  el.innerHTML=await r.text();
}
async function toggleVip(uid){
  try{
    await api('/api/users/vip?uid='+uid,{method:'POST'});
    msg('操作成功'); loadUsers(); loadStats();
  }catch(e){ msg('操作失败','err'); }
}
async function deleteUser(uid){
  if(!confirm('确定删除该用户?'))return;
  try{
    await api('/api/users/delete?uid='+uid,{method:'POST'});
    msg('已删除'); loadUsers(); loadStats();
  }catch(e){ msg('删除失败','err'); }
}
loadStats(); loadUsers(); loadTxs();
</script>
</body></html>"""

def render_users(rows):
    if not rows:
        return '<p style="color:rgba(255,255,255,.3);padding:16px">暂无用户</p>'
    html = '<table><thead><tr><th>用户名</th><th>金币</th><th>VIP</th><th>注册时间</th><th>操作</th></tr></thead><tbody>'
    for r in rows:
        ts = time.strftime('%Y-%m-%d', time.localtime(r['created_at'])) if r['created_at'] else '—'
        badge = '<span class="vip-badge yes">✓ VIP</span>' if r['is_vip'] else '<span class="vip-badge no">普通</span>'
        new_vip = 0 if r['is_vip'] else 1
        label = '取消VIP' if r['is_vip'] else '开通VIP'
        html += f"""<tr>
          <td>{r['username']}</td>
          <td><span class="coin">{r['coins'] or 0}</span></td>
          <td>{badge}</td>
          <td>{ts}</td>
          <td>
            <button class="btn-g" onclick="toggleVip('{r['uid']}')">{label}</button>
            <button class="btn-d" onclick="deleteUser('{r['uid']}')">删除</button>
          </td>
        </tr>"""
    html += '</tbody></table>'
    return html

def render_txs(rows):
    if not rows:
        return '<p style="color:rgba(255,255,255,.3);padding:16px">暂无交易记录</p>'
    html = '<table><thead><tr><th>用户</th><th>类型</th><th>商品</th><th>金额</th><th>时间</th></tr></thead><tbody>'
    for r in rows:
        ts = time.strftime('%m-%d %H:%M', time.localtime(r['ts'])) if r['ts'] else '—'
        amt = f'<span class="coin">+{r["amount"]}</span>' if r['amount'] else '—'
        html += f"""<tr>
          <td>{r.get('username', r.get('uid','—')) or '—'}</td>
          <td>{r['type'] or '—'}</td>
          <td>{r['item'] or '—'}</td>
          <td>{amt}</td>
          <td>{ts}</td>
        </tr>"""
    html += '</tbody></table>'
    return html

# ─── ROUTES ────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/admin")

@app.get("/admin", include_in_schema=False)
def admin_page(request: Request):
    if not check_auth(request):
        return HTMLResponse(LOGIN_HTML)
    return HTMLResponse(DASH_HTML)

@app.get("/login", include_in_schema=False)
def login_get(request: Request):
    if check_auth(request):
        return RedirectResponse(url="/admin")
    return HTMLResponse(LOGIN_HTML)

@app.post("/login", include_in_schema=False)
def login_post(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        resp = RedirectResponse(url="/admin", status_code=302)
        resp.set_cookie(key="gv_sid", value=make_token(ADMIN_PASSWORD), httponly=True, path="/", max_age=60*60*24*7)
        return resp
    return HTMLResponse(LOGIN_HTML.replace('id="err"></p>', 'id="err">密码错误</p>'), status_code=401)

@app.post("/logout", include_in_schema=False)
def logout(request: Request):
    resp = RedirectResponse(url="/admin", status_code=302)
    resp.delete_cookie("gv_sid", path="/")
    return resp

# ─── API ────────────────────────────────────────────────────────────────
@app.get("/api/stats")
def stats(request: Request):
    if not check_auth(request):
        raise HTTPException(401)
    db = get_db()
    try:
        users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        vips  = db.execute("SELECT COUNT(*) FROM users WHERE is_vip=1").fetchone()[0]
        games = db.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        txs   = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        return JSONResponse({"users":users,"vips":vips,"games":games,"txs":txs})
    finally:
        db.close()

@app.get("/api/users")
def users(request: Request, q: str = ""):
    if not check_auth(request):
        raise HTTPException(401)
    db = get_db()
    try:
        if q:
            rows = db.execute("SELECT uid,username,coins,is_vip,created_at FROM users WHERE username LIKE ? ORDER BY created_at DESC LIMIT 50", (f"%{q}%",)).fetchall()
        else:
            rows = db.execute("SELECT uid,username,coins,is_vip,created_at FROM users ORDER BY created_at DESC LIMIT 50").fetchall()
        return HTMLResponse(render_users(rows))
    finally:
        db.close()

@app.post("/api/users/vip")
def toggle_vip(request: Request, uid: str = ""):
    if not check_auth(request):
        raise HTTPException(401)
    if not uid:
        raise HTTPException(400, "uid required")
    db = get_db()
    try:
        user = db.execute("SELECT is_vip FROM users WHERE uid=?", (uid,)).fetchone()
        if not user:
            raise HTTPException(404, "user not found")
        new_vip = 0 if user[0] else 1
        db.execute("UPDATE users SET is_vip=? WHERE uid=?", (new_vip, uid))
        db.commit()
        return JSONResponse({"ok":True,"is_vip":new_vip})
    finally:
        db.close()

@app.post("/api/users/delete")
def delete_user(request: Request, uid: str = ""):
    if not check_auth(request):
        raise HTTPException(401)
    if not uid:
        raise HTTPException(400, "uid required")
    db = get_db()
    try:
        db.execute("DELETE FROM users WHERE uid=?", (uid,))
        db.commit()
        return JSONResponse({"ok":True})
    finally:
        db.close()

@app.get("/api/transactions")
def transactions(request: Request):
    if not check_auth(request):
        raise HTTPException(401)
    db = get_db()
    try:
        rows = db.execute(
            "SELECT t.*, u.username FROM transactions t LEFT JOIN users u ON t.uid=u.uid ORDER BY t.ts DESC LIMIT 50"
        ).fetchall()
        return HTMLResponse(render_txs(rows))
    finally:
        db.close()

@app.get("/health")
def health():
    return JSONResponse({"status":"ok","time":time.time()})

# ─── GUNICORN ENTRY (for Railway) ─────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
