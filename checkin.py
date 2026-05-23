"""
每日自动签到脚本
支持网站：
  1. justcn2.top  - 登录后签到（需关闭弹窗公告）
  2. 1ck.org       - 自动跳转找可用节点后登录签到（含验证码）
  3. 邮件通知      - 签到完成后发送结果邮件
"""

import os
import sys
import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from playwright.async_api import async_playwright

# ── 日志配置 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── 从环境变量读取凭据 ────────────────────────────────────
SITE1_URL   = "https://justcn2.top/auth/login"
SITE1_EMAIL = os.environ["SITE1_EMAIL"]
SITE1_PASS  = os.environ["SITE1_PASS"]

SITE2_URL   = "https://1ck.org/login"
SITE2_EMAIL = os.environ["SITE2_EMAIL"]
SITE2_PASS  = os.environ["SITE2_PASS"]

# ── 邮件配置 ──────────────────────────────────────────────
SMTP_SERVER  = os.environ.get("SMTP_SERVER", "smtp.qq.com")
SMTP_PORT    = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER    = os.environ.get("SMTP_USER", "")
SMTP_PASS    = os.environ.get("SMTP_PASS", "")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "")


# ── OCR 初始化 ────────────────────────────────────────────
def get_ocr():
    import ddddocr
    ocr = ddddocr.DdddOcr(show_ad=False)
    log.info("ddddocr 加载成功")
    return ocr


# ── 邮件发送 ──────────────────────────────────────────────
def send_email(subject, body):
    if not all([SMTP_USER, SMTP_PASS, NOTIFY_EMAIL]):
        log.warning("邮件配置不完整，跳过通知")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = NOTIFY_EMAIL
        msg["Subject"] = subject
        html = f"""<html><body style="font-family:Arial,sans-serif;padding:20px">
        <h2>🔔 每日签到报告</h2>
        <p>时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p><hr>{body}<hr>
        <p style="color:#999;font-size:12px">此邮件由 GitHub Actions 自动发送</p>
        </body></html>"""
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        log.info(f"邮件已发送至 {NOTIFY_EMAIL}")
        return True
    except Exception as e:
        log.error(f"邮件发送失败: {e}")
        return False


# ════════════════════════════════════════════════════════
#  网站 1：justcn2.top
# ════════════════════════════════════════════════════════
async def checkin_site1(page):
    log.info("=== [网站1] justcn2.top 开始签到 ===")
    result = {"success": False, "message": ""}
    try:
        # 1. 登录
        await page.goto(SITE1_URL, wait_until="networkidle", timeout=30000)
        await page.fill('input[type="email"], input[name="email"]', SITE1_EMAIL)
        await page.fill('input[type="password"], input[name="passwd"]', SITE1_PASS)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.wait_for_timeout(2000)
        log.info("[网站1] 登录成功")

        # 2. 跳转到用户中心
        await page.goto("https://justcn2.top/user", wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(3000)

        # 3. 关闭可能的弹窗/公告遮挡
        close_selectors = [
            "button.close", ".close-btn", "[aria-label='Close']",
            "button:has-text('关闭')", "button:has-text('我知道了')",
            "button:has-text('确定')", "button:has-text('取消')",
            ".modal .close", ".swal2-close", ".swal2-confirm",
            "[data-dismiss='modal']", ".ant-modal-close",
        ]
        for sel in close_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    log.info(f"[网站1] 关闭弹窗: {sel}")
                    await page.wait_for_timeout(500)
            except Exception:
                continue

        # 4. 点击页面安全区域关闭可能的下拉/提示（避开顶部导航栏）
        await page.mouse.click(400, 600)
        await page.wait_for_timeout(500)

        # 5. 检查是否已签到（用 locator 而不是 inner_text，避免 Material Icons 干扰）
        checkin_done_selectors = [
            "text=今日已签到", "text=已签到", "text=已领取",
            "text=签到成功", ":text('已签到')",
        ]
        for sel in checkin_done_selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=1000):
                    log.info("[网站1] 今日已签到")
                    result["success"] = True
                    result["message"] = "今日已签到"
                    return result
            except:
                continue

        # 6. 寻找并点击签到按钮（多位置尝试）
        checkin_selectors = [
            "text=点我签到", "text=摇动手机签到", "text=签到",
            "text=每日签到", "text=点击签到", "text=签到领",
            "button:has-text('签到')", "a:has-text('签到')",
            ".checkin", "#checkin", "[onclick*='checkin']",
        ]
        clicked = False
        
        # 尝试1: 当前视图
        for sel in checkin_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    clicked = True
                    log.info(f"[网站1] 点击签到: {sel}")
                    break
            except Exception:
                continue
        
        # 尝试2: 滚动到顶部
        if not clicked:
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)
            for sel in checkin_selectors:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                        clicked = True
                        log.info(f"[网站1] 顶部点击签到: {sel}")
                        break
                except Exception:
                    continue
        
        # 尝试3: 滚动到底部
        if not clicked:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            for sel in checkin_selectors:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                        clicked = True
                        log.info(f"[网站1] 底部点击签到: {sel}")
                        break
                except Exception:
                    continue
        
        # 尝试4: 逐步滚动页面查找
        if not clicked:
            for scroll_y in [300, 600, 900, 1200, 1500]:
                await page.evaluate(f"window.scrollTo(0, {scroll_y})")
                await page.wait_for_timeout(500)
                for sel in checkin_selectors:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=500):
                            await btn.click()
                            clicked = True
                            log.info(f"[网站1] 滚动{scroll_y}px后点击签到: {sel}")
                            break
                    except Exception:
                        continue
                if clicked:
                    break

        if not clicked:
            log.warning("[网站1] 仍未找到签到按钮")
            await page.screenshot(path="/tmp/site1_debug.png")
            result["message"] = "未找到签到按钮"
            return result

        # 6. 获取签到结果
        await page.wait_for_timeout(3000)
        dialog_text = ""
        for sel in [".modal", ".alert", ".swal2-popup", "[role='dialog']", ".toast", ".message"]:
            try:
                dialog_text = await page.locator(sel).first.inner_text(timeout=3000)
                if dialog_text:
                    break
            except Exception:
                continue

        if dialog_text:
            log.info(f"[网站1] 签到结果: {dialog_text.strip()}")
            result["success"] = True
            result["message"] = dialog_text.strip()
        else:
            body = await page.inner_text("body")
            for keyword in ["签到成功", "已签到", "获得", "流量", "奖励", "积分"]:
                if keyword in body:
                    result["success"] = True
                    result["message"] = f"签到成功 (检测到'{keyword}')"
                    log.info(f"[网站1] {result['message']}")
                    break
            if not result["success"]:
                result["success"] = True
                result["message"] = "签到操作已完成"
                log.info("[网站1] 签到操作已完成")

        return result

    except Exception as e:
        log.error(f"[网站1] 失败: {e}")
        await page.screenshot(path="/tmp/site1_error.png")
        result["message"] = str(e)
        return result


async def first_visible(page, selectors, timeout=1000):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=timeout):
                return sel, loc
        except Exception:
            continue
    return None, None


async def site2_has_login_form(page):
    password_selectors = [
        'input[type="password"]',
        'input[name="passwd"]',
        'input[name="password"]',
    ]
    _, password = await first_visible(page, password_selectors, timeout=800)
    return password is not None


async def site2_is_logged_in(page):
    if "login" not in page.url.lower():
        return True

    logged_in_selectors = [
        "text=退出", "text=登出", "text=注销", "text=用户中心",
        "text=签到领奖", "text=今日已签到", "text=已签到",
        "text=账户余额", "text=流量趋势", "text=我的订阅",
        "a:has-text('Logout')", "button:has-text('Logout')",
    ]
    _, logged_in_marker = await first_visible(page, logged_in_selectors, timeout=800)
    return logged_in_marker is not None


async def site2_find_captcha_input(page):
    captcha_selectors_input = [
        'input[name="captcha"]',
        'input[placeholder*="验证码"]',
        'input[id*="captcha"]',
        'input[name="code"]',
        'input[placeholder*="code"]',
        'input[type="text"]:not([name*="email"]):not([name*="mail"]):not([placeholder*="邮箱"]):not([placeholder*="email"]):not([id*="email"]):not([id*="mail"])',
    ]

    for sel in captcha_selectors_input:
        try:
            candidates = page.locator(sel)
            count = await candidates.count()
            for idx in range(count):
                inp = candidates.nth(idx)
                if not await inp.is_visible(timeout=500):
                    continue

                name = (await inp.get_attribute("name") or "").lower()
                field_id = (await inp.get_attribute("id") or "").lower()
                placeholder = (await inp.get_attribute("placeholder") or "").lower()
                value = await inp.input_value(timeout=500)
                email_like = (
                    "email" in name or "mail" in name or
                    "email" in field_id or "mail" in field_id or
                    "email" in placeholder or "邮箱" in placeholder or
                    value == SITE2_EMAIL
                )
                if email_like:
                    continue
                return sel, inp
        except Exception:
            continue

    return None, None


# ════════════════════════════════════════════════════════
#  网站 2：1ck.org（自动跳转找节点 + 验证码）
# ════════════════════════════════════════════════════════
async def checkin_site2(page, ocr):
    log.info("=== [网站2] 1ck.org 开始签到 ===")
    result = {"success": False, "message": ""}
    try:
        # 1. 访问并等待跳转稳定
        await page.goto(SITE2_URL, timeout=60000)
        await page.wait_for_load_state("networkidle", timeout=30000)
        
        # 等待跳转稳定（连续3次URL不变才算稳定）
        stable_count = 0
        last_url = ""
        for i in range(20):
            current = page.url
            if current == last_url:
                stable_count += 1
                if stable_count >= 3:
                    log.info(f"[网站2] 跳转稳定: {current}")
                    break
            else:
                stable_count = 0
                last_url = current
                log.info(f"[网站2] 跳转中: {current}")
            await page.wait_for_timeout(2000)

        # 2. 等待页面完全加载
        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.wait_for_timeout(2000)
        
        # 获取跳转后的域名
        base_url = page.url.split('/login')[0] if '/login' in page.url else page.url.rsplit('/', 1)[0]
        log.info(f"[网站2] 最终URL: {page.url}")

        # 3. 进入登录界面
        import random
        login_url = f"{base_url}/login"
        log.info(f"[网站2] 访问登录页: {login_url}")
        await page.goto(login_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # 4. 尝试登录（最多5次验证码重试）
        login_success = False
        for attempt in range(20):
            log.info(f"[网站2] 登录尝试 {attempt+1}/20")

            # 找邮箱输入框（多种选择器）
            email_filled = False
            email_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[name*="mail"]',
                'input[id*="email"]',
                'input[id*="mail"]',
                'input[placeholder*="邮箱"]',
                'input[placeholder*="email"]',
                'input[type="text"]:not([name*="captcha"]):not([name="code"]):not([id*="captcha"]):not([placeholder*="验证码"]):not([placeholder*="code"])',
            ]
            for sel in email_selectors:
                try:
                    inp = page.locator(sel).first
                    if await inp.is_visible(timeout=2000):
                        await inp.fill(SITE2_EMAIL)
                        email_filled = True
                        log.info(f"[网站2] 填写邮箱: {sel}")
                        break
                except Exception:
                    continue

            if not email_filled:
                log.warning("[网站2] 未找到邮箱输入框")
                await page.screenshot(path="/tmp/site2_no_email.png")
                break

            # 找密码输入框
            password_filled = False
            for sel in ['input[type="password"]', 'input[name="passwd"]', 'input[name="password"]']:
                try:
                    inp = page.locator(sel).first
                    if await inp.is_visible(timeout=2000):
                        await inp.fill(SITE2_PASS)
                        password_filled = True
                        log.info(f"[网站2] 填写密码: {sel}")
                        break
                except Exception:
                    continue

            if not password_filled:
                log.warning("[网站2] 未找到密码输入框")
                await page.screenshot(path="/tmp/site2_no_password.png")
                break

            # 处理验证码
            captcha_selectors_img = [
                # base64 验证码图片（最优先，避免匹配到其他base64图片如logo）
                'img.my-auto[src^="data:"]',
                'img[src*="captcha"]', 'img[id*="captcha"]',
                '.captcha img', 'img[alt*="验证码"]',
                'img[src*="code"]', 'img[alt*="captcha"]',
                'img.captcha', '#captcha-img',
            ]
            
            captcha_input = None
            captcha_img = None
            
            # 找验证码输入框，排除已经填写了邮箱的输入框
            captcha_input_sel, captcha_input = await site2_find_captcha_input(page)
            if captcha_input:
                log.info(f"[网站2] 找到验证码输入框: {captcha_input_sel}")
            
            # 找验证码图片
            for sel in captcha_selectors_img:
                try:
                    img = page.locator(sel).first
                    if await img.is_visible(timeout=1000):
                        captcha_img = img
                        log.info(f"[网站2] 找到验证码图片: {sel}")
                        break
                except:
                    continue
            
            if captcha_img and captcha_input:
                try:
                    # 优先从 base64 src 解码图片（比截图更准确）
                    src = await captcha_img.get_attribute("src")
                    if src and src.startswith("data:") and "," in src:
                        import base64 as b64
                        b64_data = src.split(",", 1)[1]
                        img_bytes = b64.b64decode(b64_data)
                        log.info(f"[网站2] 从base64解码验证码图片 ({len(img_bytes)} bytes)")
                    else:
                        img_bytes = await captcha_img.screenshot()
                    
                    code = ocr.classification(img_bytes)
                    # 字母→数字映射（ddddocr有时把数字识别成字母）
                    char_map = {'o': '0', 'O': '0', 'l': '1', 'I': '1', 'i': '1', 
                                'z': '2', 'Z': '2', 's': '5', 'S': '5', 'b': '6',
                                'g': '9', 'q': '9', 'G': '9', 'c': '0', 'C': '0',
                                'd': '0', 'D': '0', 'e': '8', 'B': '8'}
                    code = ''.join(char_map.get(c, c) for c in code)
                    # 过滤非数字字符
                    code = ''.join(c for c in code if c.isdigit())
                    # 只取前4位
                    if len(code) > 4:
                        code = code[:4]
                    log.info(f"[网站2] OCR识别验证码: {code}")
                    if len(code) < 4:
                        log.warning(f"[网站2] 验证码位数不足: {code}")
                        continue
                    await captcha_input.fill(str(code))
                except Exception as e:
                    log.warning(f"[网站2] 验证码处理失败: {e}")
            else:
                log.warning(f"[网站2] 未找到验证码元素 (input={captcha_input is not None}, img={captcha_img is not None})")

            # 提交登录
            submitted = False
            for sel in ['button[type="submit"]', 'button:has-text("登录")', 'button:has-text("Login")', 'input[type="submit"]']:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        submitted = True
                        log.info(f"[网站2] 点击登录: {sel}")
                        break
                except Exception:
                    continue

            if not submitted:
                log.warning("[网站2] 未找到登录提交按钮")
                await page.screenshot(path="/tmp/site2_no_submit.png")
                break

            await page.wait_for_load_state("networkidle", timeout=15000)
            await page.wait_for_timeout(5000)  # 登录成功需要3秒以上才能检测到

            # 检查登录结果
            current_url = page.url
            if await site2_is_logged_in(page):
                login_success = True
                log.info(f"[网站2] 登录成功! URL: {current_url}")
                break
            else:
                log.warning(f"[网站2] 登录失败，可能验证码错误")
                # 重新导航到登录页（刷新验证码）
                await page.goto(login_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)

        if not login_success:
            result["message"] = "登录失败"
            return result

        # 6. 签到 - 右上部"签到领奖"
        await page.wait_for_timeout(8000)  # 等待页面完全加载（登录后需要较长时间）
        await page.wait_for_load_state("networkidle", timeout=15000)
        
        # 滚动到顶部，确保签到按钮可见
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        
        # 先检查是否已签到
        checkin_done_selectors = [
            "text=今日已签到", "text=已签到", "text=已领取",
        ]
        for sel in checkin_done_selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=1000):
                    log.info("[网站2] 今日已签到")
                    result["success"] = True
                    result["message"] = "今日已签到"
                    return result
            except:
                continue
        
        checkin_selectors = [
            "text=签到领奖", "text=签到", "text=每日签到",
            "button:has-text('签到')", "a:has-text('签到')",
            "[onclick*='checkin']", ".checkin-btn", "#checkin",
        ]
        clicked = False
        for sel in checkin_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=3000):
                    await btn.click()
                    clicked = True
                    log.info(f"[网站2] 点击签到: {sel}")
                    break
            except Exception:
                continue

        if not clicked:
            log.warning("[网站2] 未找到签到按钮")
            await page.screenshot(path="/tmp/site2_debug.png")
            result["message"] = "未找到签到按钮"
            return result

        await page.wait_for_timeout(3000)
        
        # 获取签到结果
        for sel in [".modal", ".alert", ".swal2-popup", "[role='dialog']", ".toast"]:
            try:
                text = await page.locator(sel).first.inner_text(timeout=3000)
                if text:
                    result["message"] = text.strip()
                    break
            except Exception:
                continue
        
        if not result["message"]:
            result["message"] = "签到完成"
        
        result["success"] = True
        log.info(f"[网站2] 签到结果: {result['message']}")
        return result

    except Exception as e:
        log.error(f"[网站2] 失败: {e}")
        await page.screenshot(path="/tmp/site2_error.png")
        result["message"] = str(e)
        return result


# ════════════════════════════════════════════════════════
#  主入口
# ════════════════════════════════════════════════════════
async def main():
    log.info(f"签到任务开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    ocr = get_ocr()
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"

        ctx1 = await browser.new_context(user_agent=ua)
        page1 = await ctx1.new_page()
        results["site1"] = await checkin_site1(page1)
        await ctx1.close()

        ctx2 = await browser.new_context(user_agent=ua)
        page2 = await ctx2.new_page()
        results["site2"] = await checkin_site2(page2, ocr)
        await ctx2.close()

        await browser.close()

    # 汇总
    s1 = results["site1"]
    s2 = results["site2"]
    log.info("══════════════════════════════")
    log.info(f"网站1 justcn2.top : {'✅' if s1['success'] else '❌'} {s1['message']}")
    log.info(f"网站2 1ck.org     : {'✅' if s2['success'] else '❌'} {s2['message']}")
    log.info("══════════════════════════════")

    # 发送邮件
    all_ok = s1["success"] and s2["success"]
    emoji = "✅" if all_ok else "⚠️"
    subject = f"{emoji} 每日签到报告 - {'全部成功' if all_ok else '部分失败'}"
    email_body = f"""
    <table style="border-collapse:collapse;width:100%">
    <tr style="background:{'#d4edda' if s1['success'] else '#f8d7da'}">
        <td style="padding:10px;border:1px solid #ddd"><b>网站1 justcn2.top</b></td>
        <td style="padding:10px;border:1px solid #ddd">{'✅ 成功' if s1['success'] else '❌ 失败'}</td>
        <td style="padding:10px;border:1px solid #ddd">{s1['message']}</td>
    </tr>
    <tr style="background:{'#d4edda' if s2['success'] else '#f8d7da'}">
        <td style="padding:10px;border:1px solid #ddd"><b>网站2 1ck.org</b></td>
        <td style="padding:10px;border:1px solid #ddd">{'✅ 成功' if s2['success'] else '❌ 失败'}</td>
        <td style="padding:10px;border:1px solid #ddd">{s2['message']}</td>
    </tr>
    </table>"""
    send_email(subject, email_body)

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
