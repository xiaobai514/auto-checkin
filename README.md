# 每日自动签到机器人

自动完成以下两个网站的每日签到：
- **justcn2.top** — 登录 → 用户中心 → 签到
- **1ck.org** — 登录（含验证码自动识别）→ 首页签到

---

## 📁 文件结构

```
├── checkin.py                        # 主签到脚本
├── requirements.txt                  # Python 依赖
├── .gitignore                        # 防止泄露本地凭据
└── .github/
    └── workflows/
        └── checkin.yml               # GitHub Actions 定时任务
```

---

## 🚀 部署步骤

### 第一步：创建 GitHub 私有仓库

1. 登录 [github.com](https://github.com)
2. 右上角 **+** → **New repository**
3. 填写仓库名，例如 `auto-checkin`
4. 选择 **Private**（私有，重要！）
5. 点击 **Create repository**

---

### 第二步：上传代码到仓库

在 WSL 终端执行：

```bash
# 进入脚本目录（根据你的实际路径调整）
cd /path/to/checkin

# 初始化 git
git init
git add .
git commit -m "初始化签到脚本"

# 关联远程仓库（替换 YOUR_USERNAME 为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/auto-checkin.git
git branch -M main
git push -u origin main
```

---

### 第三步：配置 GitHub Secrets（存储密码）

1. 打开你的仓库页面
2. 点击顶部 **Settings** → 左侧 **Secrets and variables** → **Actions**
3. 点击 **New repository secret**，依次添加以下 4 个：

| Secret 名称 | 值 |
|-------------|-----|
| `SITE1_EMAIL` | q748949062@gmail.com |
| `SITE1_PASS`  | 你的 justcn2.top 密码 |
| `SITE2_EMAIL` | q748949062@gmail.com |
| `SITE2_PASS`  | 你的 1ck.org 密码 |

> ⚠️ 密码在 Secrets 里是加密的，GitHub 员工也看不到，日志里也不会显示。

---

### 第四步：手动触发测试

1. 仓库页面 → 点击 **Actions** 选项卡
2. 左侧选择 **每日自动签到**
3. 右侧点击 **Run workflow** → **Run workflow**
4. 等待约 2-3 分钟，查看运行结果

**绿色 ✅ = 成功，红色 ❌ = 失败（点进去看日志）**

---

### 运行时间

默认每天 **北京时间 08:00** 自动运行。

如需修改时间，编辑 `.github/workflows/checkin.yml` 中的 cron 表达式：
```yaml
- cron: "0 0 * * *"   # UTC 00:00 = 北京时间 08:00
```

常用时间参考：
- 北京 07:00 → `0 23 * * *`（前一天UTC）
- 北京 09:00 → `0 1 * * *`
- 北京 12:00 → `0 4 * * *`

---

## 🔧 本地调试（WSL）

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 设置临时环境变量
export SITE1_EMAIL="你的邮箱"
export SITE1_PASS="你的密码"
export SITE2_EMAIL="你的邮箱"
export SITE2_PASS="你的密码"

# 运行
python checkin.py
```

---

## 📸 失败排查

签到失败时，Actions 会自动保存截图。

1. 点击失败的 workflow run
2. 右下角 **Artifacts** → 下载 `debug-screenshots`
3. 查看截图了解失败原因

---

## ⚠️ 注意事项

- 仓库必须设为 **Private（私有）**
- 不要在代码里硬编码密码，只用 Secrets
- GitHub Actions 免费版每月有 2000 分钟，每次运行约 3 分钟，每天一次完全够用
