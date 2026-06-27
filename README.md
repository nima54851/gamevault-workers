# 🎮 GameVault Admin Backend

FastAPI 管理后端，部署在 Railway（国内可访问）。

**访问地址：** 部署后点 Railway → 右上角的 **Settings** → **Networking** → **Public Networking** → 打开

## 快速部署到 Railway

1. 打开 👉 https://railway.app
2. 用 GitHub 登录
3. 点 **New Project** → **Deploy from GitHub repo**
4. 选择 `nima54851/gamevault-workers`
5. Railway 自动检测 Python → 开始部署
6. 部署完成后点 **Settings** → **Environment** → 添加变量：
   - `ADMIN_PASSWORD` = `admin123`（改成你的密码）

## 本地运行

```bash
pip install -r requirements.txt
ADMIN_PASSWORD=admin123 uvicorn main:app --reload --port 8000
```

访问 http://localhost:8000/admin
