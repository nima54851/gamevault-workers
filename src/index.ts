import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { logger } from 'hono/logger'
import { getCookie, setCookie, deleteCookie } from 'hono/cookie'
import { html } from 'hono/html'
import type { D1Database } from '@cloudflare/workers-types'

// ──────────────────────────────────────────
//  TYPE ENV
// ──────────────────────────────────────────
interface Env {
  DB: D1Database
  ADMIN_PASSWORD: string
}

// ──────────────────────────────────────────
//  APP
// ──────────────────────────────────────────
const app = new Hono<{ Bindings: Env }>()

app.use('*', logger())
app.use('*', cors({ origin: '*', allowMethods: ['GET', 'POST', 'PUT', 'DELETE'] }))

// ──────────────────────────────────────────
//  AUTH HELPERS
// ──────────────────────────────────────────
const ADMIN_COOKIE = 'gv_admin_sid'
const ADMIN_HASH = (p: string) => {
  let h = 0
  for (let i = 0; i < p.length; i++) h = ((h << 5) - h + p.charCodeAt(i)) | 0
  return String(h)
}
const isAuthed = (c: any) => getCookie(c, ADMIN_COOKIE) === ADMIN_HASH(c.env.ADMIN_PASSWORD || 'admin123')
const requireAuth = async (c: any, next: any) => {
  if (!isAuthed(c)) return c.html(loginPage(''))
  await next()
}

// ──────────────────────────────────────────
//  PAGES
// ──────────────────────────────────────────
const loginPage = (err: string) => `<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GameVault 管理登录</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);font-family:'Segoe UI',sans-serif}
.card{background:rgba(255,255,255,.06);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.12);border-radius:20px;padding:48px 40px;width:380px;text-align:center}
h1{color:#fff;margin-bottom:8px;font-size:28px}.sub{color:rgba(255,255,255,.5);margin-bottom:36px;font-size:14px}
input{display:block;width:100%;padding:14px 16px;margin-bottom:16px;border:1px solid rgba(255,255,255,.15);border-radius:10px;background:rgba(255,255,255,.08);color:#fff;font-size:15px;outline:none;transition:border .2s}
input:focus{border-color:#6366f1}input::placeholder{color:rgba(255,255,255,.35)}
.btn{width:100%;padding:14px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border:none;border-radius:10px;font-size:16px;font-weight:600;cursor:pointer;transition:opacity .2s}
.btn:hover{opacity:.88}.err{color:#f87171;margin-bottom:16px;font-size:13px;min-height:18px}
</style></head>
<body><div class="card">
<h1>🎮 GameVault</h1><p class="sub">管理后台登录</p>
<p class="err">${err}</p>
<form method="post" action="/api/auth/login">
<input name="password" type="password" placeholder="输入管理密码" required autocomplete="current-password">
<button class="btn" type="submit">登 录</button>
</form></div></body></html>`

const dashPage = (stats: any) => `<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GameVault 管理后台</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#0f0f1a;color:#e2e8f0;min-height:100vh}
.top{background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:20px 32px;display:flex;align-items:center;justify-content:space-between}
.top h1{font-size:22px;color:#fff}
.top .right{display:flex;gap:12px;align-items:center}
.badge{background:rgba(255,255,255,.2);color:#fff;padding:4px 14px;border-radius:20px;font-size:13px}
.main{padding:24px 32px;max-width:1200px;margin:0 auto}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:28px}
.card{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:24px}
.card .label{color:rgba(255,255,255,.45);font-size:13px;margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px}
.card .val{font-size:36px;font-weight:700;color:#fff}
.card .sub{color:rgba(255,255,255,.35);font-size:12px;margin-top:4px}
.card.users .val{color:#34d399}.card.vip .val{color:#fbbf24}
.card.games .val{color:#60a5fa}.card.tx .val{color:#f472b6}
.section{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:24px;margin-bottom:20px}
.section h2{color:#fff;font-size:16px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,.07)}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;color:rgba(255,255,255,.4);font-weight:500;padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.06)}
td{padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.04)}
tr:hover td{background:rgba(255,255,255,.03)}
.vip-badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600}
.vip-badge.yes{background:rgba(251,191,36,.2);color:#fbbf24}
.vip-badge.no{background:rgba(255,255,255,.07);color:rgba(255,255,255,.35)}
button.danger{background:#ef4444;color:#fff;border:none;padding:6px 14px;border-radius:8px;cursor:pointer;font-size:13px}
button.danger:hover{background:#dc2626}
input.search{padding:8px 14px;border:1px solid rgba(255,255,255,.12);border-radius:8px;background:rgba(255,255,255,.06);color:#fff;font-size:14px;width:260px}
input.search::placeholder{color:rgba(255,255,255,.3)}
.coin{color:#fbbf24;font-weight:600}
</style></head>
<body>
<div class="top">
  <h1>🎮 GameVault 管理后台</h1>
  <div class="right">
    <span class="badge">在线</span>
    <form method="post" action="/api/auth/logout" style="display:inline">
      <button class="badge" style="border:none;cursor:pointer;font-size:13px">退出</button>
    </form>
  </div>
</div>
<div class="main">
  <div class="grid">
    <div class="card users"><div class="label">用户总数</div><div class="val">${stats.users}</div></div>
    <div class="card vip"><div class="label">VIP用户</div><div class="val">${stats.vips}</div></div>
    <div class="card games"><div class="label">收录游戏</div><div class="val">${stats.games}</div></div>
    <div class="card tx"><div class="label">交易记录</div><div class="val">${stats.txs}</div></div>
  </div>
  <div class="section">
    <h2>👥 用户管理</h2>
    <input class="search" placeholder="搜索用户名..." hx-get="/api/users" hx-trigger="keyup delay:300ms" hx-target="#user-table" name="q" value="">
    <div id="user-table"></div>
  </div>
  <div class="section">
    <h2>📊 最新交易</h2>
    <div id="tx-table"></div>
  </div>
</div>
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
</body></html>`

// ──────────────────────────────────────────
//  AUTH ROUTES
// ──────────────────────────────────────────
app.get('/login', (c) => c.html(loginPage('')))

app.post('/api/auth/login', async (c) => {
  const body = await c.req.parseBody()
  const password = String(body['password'] || '')
  const secret = c.env.ADMIN_PASSWORD || 'admin123'
  if (password === secret) {
    setCookie(c, ADMIN_COOKIE, ADMIN_HASH(secret), { httpOnly: true, path: '/', maxAge: 60 * 60 * 24 * 7, sameSite: 'Lax' })
    return c.redirect('/admin')
  }
  return c.html(loginPage('密码错误'))
})

app.post('/api/auth/logout', (c) => {
  deleteCookie(c, ADMIN_COOKIE, { path: '/' })
  return c.redirect('/login')
})

// ──────────────────────────────────────────
//  ADMIN DASHBOARD
// ──────────────────────────────────────────
app.get('/admin', requireAuth, async (c) => {
  const users = await c.env.DB.prepare('SELECT COUNT(*) as n FROM users').first<{n:number}>()
  const vips  = await c.env.DB.prepare('SELECT COUNT(*) as n FROM users WHERE is_vip=1').first<{n:number}>()
  const games = await c.env.DB.prepare('SELECT COUNT(*) as n FROM games').first<{n:number}>()
  const txs   = await c.env.DB.prepare('SELECT COUNT(*) as n FROM transactions').first<{n:number}>()
  return c.html(dashPage({ users: users?.n||0, vips: vips?.n||0, games: games?.n||0, txs: txs?.n||0 }))
})

// ──────────────────────────────────────────
//  API ROUTES
// ──────────────────────────────────────────
app.get('/api/stats', requireAuth, async (c) => {
  const users = await c.env.DB.prepare('SELECT COUNT(*) as n FROM users').first<{n:number}>()
  const vips  = await c.env.DB.prepare('SELECT COUNT(*) as n FROM users WHERE is_vip=1').first<{n:number}>()
  const games = await c.env.DB.prepare('SELECT COUNT(*) as n FROM games').first<{n:number}>()
  const txs   = await c.env.DB.prepare('SELECT COUNT(*) as n FROM transactions').first<{n:number}>()
  return c.json({ users: users?.n||0, vips: vips?.n||0, games: games?.n||0, txs: txs?.n||0 })
})

// Users list
app.get('/api/users', requireAuth, async (c) => {
  const q = c.req.query('q') || ''
  let stmt
  if (q) {
    stmt = c.env.DB.prepare('SELECT uid,username,coins,is_vip,created_at FROM users WHERE username LIKE ? ORDER BY created_at DESC LIMIT 50')
      .bind(`%${q}%`)
  } else {
    stmt = c.env.DB.prepare('SELECT uid,username,coins,is_vip,created_at FROM users ORDER BY created_at DESC LIMIT 50')
  }
  const { results } = await stmt.all()
  const rows = results as any[] || []
  if (rows.length === 0) return c.html('<p style="color:rgba(255,255,255,.3);padding:20px">暂无用户</p>')
  const html = `<table><thead><tr><th>用户</th><th>金币</th><th>VIP</th><th>注册时间</th><th>操作</th></tr></thead><tbody>
    ${rows.map(r => `<tr>
      <td>${r.username}</td>
      <td><span class="coin">${r.coins || 0}</span></td>
      <td><span class="vip-badge ${r.is_vip?'yes':'no'}">${r.is_vip?'✓ VIP':'普通'}</span></td>
      <td>${r.created_at ? new Date(r.created_at*1000).toLocaleDateString('zh-CN'):'—'}</td>
      <td>
        <button class="danger" hx-post="/api/users/vip" hx-vals='{"uid":"${r.uid}"}' hx-confirm="确定切换 ${r.username} 的VIP状态?">切换VIP</button>
      </td>
    </tr>`).join('')}
  </tbody></table>`
  return c.html(html)
})

// Toggle VIP
app.post('/api/users/vip', requireAuth, async (c) => {
  const body = await c.req.parseBody()
  const uid = String(body['uid'] || '')
  if (!uid) return c.json({ error: 'uid required' }, 400)
  const user = await c.env.DB.prepare('SELECT is_vip FROM users WHERE uid=?').bind(uid).first()
  if (!user) return c.json({ error: 'user not found' }, 404)
  const newVip = user.is_vip ? 0 : 1
  await c.env.DB.prepare('UPDATE users SET is_vip=? WHERE uid=?').bind(newVip, uid).run()
  return c.json({ ok: true, is_vip: newVip })
})

// Transactions
app.get('/api/transactions', requireAuth, async (c) => {
  const { results } = await c.env.DB.prepare(
    'SELECT t.*,u.username FROM transactions t LEFT JOIN users u ON t.uid=u.uid ORDER BY t.ts DESC LIMIT 30'
  ).all()
  const rows = results as any[] || []
  if (rows.length === 0) return c.html('<p style="color:rgba(255,255,255,.3);padding:20px">暂无交易记录</p>')
  const html = `<table><thead><tr><th>用户</th><th>类型</th><th>商品</th><th>金额</th><th>时间</th></tr></thead><tbody>
    ${rows.map(r => `<tr>
      <td>${r.username || r.uid || '—'}</td>
      <td>${r.type || '—'}</td>
      <td>${r.item || '—'}</td>
      <td>${r.amount ? `<span class="coin">+${r.amount}</span>` : '—'}</td>
      <td>${r.ts ? new Date(r.ts*1000).toLocaleString('zh-CN'):'—'}</td>
    </tr>`).join('')}
  </tbody></table>`
  return c.html(html)
})

// ──────────────────────────────────────────
//  HEALTH
// ──────────────────────────────────────────
app.get('/health', (c) => c.json({ status: 'ok', time: Date.now() }))

// ──────────────────────────────────────────
//  CORS preflight
// ──────────────────────────────────────────
app.options('*', (c) => c.newResponse(null, 204))

export default app
