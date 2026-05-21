"""
每日自动签到脚本
支持网站：
  1. justcn2.top  - 登录后进入"我的→用户中心"签到
  2. 1ck.org       - 登录后首页签到（含图片验证码识别）
"""

import os
import sys
import time
import base64
import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

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

# ── OCR 初始化（ddddocr） ────────────────────────────────
def get_ocr():
    try:
        import ddddocr
        ocr = ddddocr.DdddOcr(show_ad=False)
        log.info("ddddocr 加载成功")
        return ocr
    except ImportError:
        log.error("ddddocr 未安装，请检查 requirements.txt")
        raise


# ════════════════════════════════════════════════════════
#  网站 1：justcn2.top
# ════════════════════════════════════════════════════════
async def checkin_site1(page):
    log.info("=== [网站1] justcn2.top 开始签到 ===")
    try:
        # 1. 登录
        await page.goto(SITE1_URL, wait_until="networkidle", timeout=30000)
        await page.fill('input[type="email"], input[name="email"]', SITE1_EMAIL)
        await page.fill('input[type="password"], input[name="passwd"]', SITE1_PASS)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle", timeout=15000)
        log.info("[网站1] 登录成功")

        # 2. 跳转到用户中心
        await page.goto("https://justcn2.top/user", wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        # 3. 寻找并点击签到按钮（尝试多种选择器）
        checkin_selectors = [
            "text=签到",
            "text=每日签到",
            "a[href*='checkin']",
            "button:has-text('签到')",
            ".checkin",
            "#checkin",
        ]
        clicked = False
        for sel in checkin_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=3000):
                    await btn.click()
                    clicked = True
                    log.info(f"[网站1] 点击签到按钮：{sel}")
                    break
            except Exception:
                continue

        if not clicked:
            log.warning("[网站1] 未找到签到按钮，尝试截图排查")
            await page.screenshot(path="/tmp/site1_debug.png")
            return False

        # 4. 等待签到弹窗/结果
        await page.wait_for_timeout(3000)
        # 捕获弹窗文字
        dialog_text = ""
        try:
            dialog_text = await page.locator(".modal, .alert, .swal2-popup, [role='dialog']").first.inner_text(timeout=5000)
        except Exception:
            pass

        if dialog_text:
            log.info(f"[网站1] 签到结果：{dialog_text.strip()}")
        else:
            # 备用：抓页面通知
            body = await page.inner_text("body")
            if "签到" in body or "流量" in body or "成功" in body:
                log.info("[网站1] 签到成功（页面含成功标志）")
            else:
                log.warning("[网站1] 签到结果不明确，请查看截图")
                await page.screenshot(path="/tmp/site1_result.png")

        return True

    except Exception as e:
        log.error(f"[网站1] 签到失败：{e}")
        try:
            await page.screenshot(path="/tmp/site1_error.png")
        except Exception:
            pass
        return False


# ════════════════════════════════════════════════════════
#  网站 2：1ck.org（含节点测速跳转 + 图片验证码）
# ════════════════════════════════════════════════════════
async def checkin_site2(page, ocr):
    log.info("=== [网站2] 1ck.org 开始签到 ===")
    try:
        # 1. 访问登录页（可能触发节点测速跳转）
        await page.goto(SITE2_URL, timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)

        # 处理节点测速跳转：等待最终落到登录页
        for attempt in range(5):
            current = page.url
            log.info(f"[网站2] 当前URL：{current}")
            if "login" in current or "1ck.org" in current:
                break
            log.info(f"[网站2] 等待跳转... ({attempt+1}/5)")
            await page.wait_for_timeout(3000)
            await page.wait_for_load_state("networkidle", timeout=10000)

        # 2. 处理图片验证码（最多重试5次）
        login_success = False
        for attempt in range(5):
            log.info(f"[网站2] 登录尝试 {attempt+1}/5")

            # 填写邮箱和密码
            await page.fill('input[type="email"], input[name="email"]', SITE2_EMAIL)
            await page.fill('input[type="password"], input[name="passwd"], input[name="password"]', SITE2_PASS)

            # 识别验证码
            captcha_input = page.locator('input[name="captcha"], input[placeholder*="验证码"], input[id*="captcha"]').first
            captcha_img   = page.locator('img[src*="captcha"], img[id*="captcha"], .captcha img').first

            if await captcha_img.is_visible(timeout=3000):
                # 截取验证码图片
                img_bytes = await captcha_img.screenshot()
                code = ocr.classification(img_bytes)
                log.info(f"[网站2] OCR 识别验证码：{code}")
                await captcha_input.fill(str(code))
            else:
                log.warning("[网站2] 未找到验证码图片，跳过验证码填写")

            # 提交
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle", timeout=15000)

            # 检查是否登录成功
            if "login" not in page.url:
                login_success = True
                log.info("[网站2] 登录成功")
                break
            else:
                log.warning(f"[网站2] 验证码错误，刷新重试...")
                # 刷新验证码
                try:
                    await captcha_img.click()
                    await page.wait_for_timeout(1000)
                except Exception:
                    await page.reload()
                    await page.wait_for_load_state("networkidle", timeout=10000)

        if not login_success:
            log.error("[网站2] 多次验证码识别失败，放弃")
            await page.screenshot(path="/tmp/site2_login_fail.png")
            return False

        # 3. 签到
        await page.wait_for_timeout(2000)
        checkin_selectors = [
            "text=签到",
            "text=每日签到",
            "button:has-text('签到')",
            "a:has-text('签到')",
            "[onclick*='checkin']",
            ".checkin-btn",
        ]
        clicked = False
        for sel in checkin_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=3000):
                    await btn.click()
                    clicked = True
                    log.info(f"[网站2] 点击签到按钮：{sel}")
                    break
            except Exception:
                continue

        if not clicked:
            log.warning("[网站2] 未找到签到按钮，截图排查")
            await page.screenshot(path="/tmp/site2_debug.png")
            return False

        await page.wait_for_timeout(3000)
        log.info("[网站2] 签到操作完成")
        await page.screenshot(path="/tmp/site2_result.png")
        return True

    except Exception as e:
        log.error(f"[网站2] 签到失败：{e}")
        try:
            await page.screenshot(path="/tmp/site2_error.png")
        except Exception:
            pass
        return False


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

        # ── 网站1 ──
        ctx1 = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
        )
        page1 = await ctx1.new_page()
        results["site1"] = await checkin_site1(page1)
        await ctx1.close()

        # ── 网站2 ──
        ctx2 = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
        )
        page2 = await ctx2.new_page()
        results["site2"] = await checkin_site2(page2, ocr)
        await ctx2.close()

        await browser.close()

    # ── 汇总 ──
    log.info("══════════════════════════════")
    log.info(f"网站1 justcn2.top : {'✅ 成功' if results['site1'] else '❌ 失败'}")
    log.info(f"网站2 1ck.org      : {'✅ 成功' if results['site2'] else '❌ 失败'}")
    log.info("══════════════════════════════")

    if not all(results.values()):
        sys.exit(1)  # 让 GitHub Actions 标记为失败


if __name__ == "__main__":
    asyncio.run(main())
