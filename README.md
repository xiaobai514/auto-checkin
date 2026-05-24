# 🔄 每日自动签到

自动签到 justcn2.top 和 1ck.org，支持多账号，签到结果邮件通知。

## 运行方式

- **定时执行**：每天北京时间 00:30（GitHub Actions cron `30 16 * * *` UTC）
- **手动触发**：GitHub 仓库 → Actions → 每日自动签到 → Run workflow
- **完全独立**：跑在 GitHub 服务器上，本地断网不影响

## 技术栈

- Python 3.11 + Playwright（headless Chromium）
- ddddocr（验证码 OCR 识别）
- GitHub Actions（定时 + 运行环境）
- QQ 邮箱 SMTP_SSL（邮件通知）

## GitHub Secrets 配置

仓库 → Settings → Secrets and variables → Actions → New repository secret

### 网站1：justcn2.top（2个账号）

| Name           | Value          |
|----------------|----------------|
| SITE1_EMAIL_1  | 第1个账号邮箱   |
| SITE1_PASS_1   | 第1个账号密码   |
| SITE1_EMAIL_2  | 第2个账号邮箱   |
| SITE1_PASS_2   | 第2个账号密码   |

### 网站2：1ck.org（2个账号）

| Name           | Value          |
|----------------|----------------|
| SITE2_EMAIL_1  | 第1个账号邮箱   |
| SITE2_PASS_1   | 第1个账号密码   |
| SITE2_EMAIL_2  | 第2个账号邮箱   |
| SITE2_PASS_2   | 第2个账号密码   |

### 邮件通知

| Name          | Value              |
|---------------|--------------------|
| SMTP_SERVER   | smtp.qq.com        |
| SMTP_PORT     | 465                |
| SMTP_USER     | 2429699640@qq.com  |
| SMTP_PASS     | QQ邮箱授权码        |
| NOTIFY_EMAIL  | 2429699640@qq.com  |

## 添加更多账号

代码自动发现账号数量，只需新增 Secrets：

```
SITE1_EMAIL_3 / SITE1_PASS_3    # 网站1 第3个账号
SITE2_EMAIL_3 / SITE2_PASS_3    # 网站2 第3个账号
```

然后在 `.github/workflows/checkin.yml` 的 `env` 段加上对应行即可。

## 签到流程

### 网站1 justcn2.top
1. 访问登录页 → 填写邮箱密码 → 提交
2. 跳转用户中心 → 关闭弹窗/公告
3. 检查是否已签到 → 点击签到按钮
4. 确认签到结果

### 网站2 1ck.org
1. 访问 1ck.org → 自动跳转找可用节点
2. 进入登录页 → 填写邮箱密码 + 验证码（ddddocr 识别）
3. 验证码支持字母→数字映射（o→0, l→1, s→5 等）
4. 最多 20 次验证码重试
5. 登录后关闭弹窗 → 点击签到领奖
6. 多策略查找按钮：Playwright选择器 → JS DOM遍历坐标点击 → getByText

## 邮件通知格式

```
✅ 每日签到报告 (4个账号) - 全部成功

| 网站         | 账号   | 状态     | 详情         |
|-------------|--------|---------|-------------|
| justcn2.top | 账号1  | ✅ 成功  | 签到成功 +5积分 |
| justcn2.top | 账号2  | ✅ 成功  | 今日已签到     |
| 1ck.org     | 账号1  | ✅ 成功  | 签到成功 +500MB |
| 1ck.org     | 账号2  | ❌ 失败  | 登录失败       |
```

## 已知问题

- **GitHub Actions 定时延迟**：GitHub 负载高时 cron 可能延迟几小时执行，正常现象
- **验证码识别**：ddddocr 对某些验证码识别率不高，已做字母→数字映射优化
- **1ck.org 跳转**：每次访问可能跳到不同域名，代码自动适应
- **libasound2**：Ubuntu 24.04 已改名 libasound2t64，workflow 已处理

## 调试

失败时 Actions 会自动上传截图到 Artifacts（保留3天）：
- `site1_debug.png` / `site1_error.png` — 网站1签到页面状态
- `site2_debug.png` / `site2_error.png` — 网站2签到页面状态
- `site2_before_checkin.png` — 网站2签到前页面状态
- `site2_no_email.png` / `site2_no_password.png` — 登录表单异常

## 修改历史

| 日期       | 说明                                              |
|-----------|--------------------------------------------------|
| 2026-05-24 | 多账号支持 + 邮件表格汇总 + 签到按钮查找增强         |
| 2026-05-24 | 定时改为凌晨 0:30                                  |
| 2026-05-23 | 网站2验证码字母→数字映射 + 登录等待时间优化          |
| 2026-05-23 | 网站1已签到检测 + 网站2验证码20次重试               |
| 2026-05-21 | 初始版本：两站签到 + 邮件通知 + GitHub Actions      |
