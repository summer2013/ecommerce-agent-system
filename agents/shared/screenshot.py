from datetime import datetime
from pathlib import Path

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def take_screenshot(url: str, store_code: str) -> str:
    """
    用 Playwright 打开 URL 并截图
    返回截图文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{store_code}_{timestamp}.png"
    filepath = SCREENSHOT_DIR / filename

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            page.screenshot(path=str(filepath), full_page=False)
            browser.close()
        print(f"  📸 截图保存：{filepath}")
        return str(filepath)
    except Exception as e:
        print(f"  ⚠ 截图失败：{e}")
        return ""


def take_mock_screenshot(store_code: str, store_name: str) -> str:
    """
    Mock 截图：没有真实网站时，截取百度地图搜索结果作为示意
    返回截图文件路径
    """
    # 选用更稳定的公开页面做示意，避免部分网络环境对地图站点的访问限制
    url = f"https://www.bing.com/search?q={store_name}"
    return take_screenshot(url, store_code)


if __name__ == "__main__":
    print("测试截图功能...")
    path = take_mock_screenshot("STORE001", "上海旗舰店")
    if path:
        print(f"✅ 截图成功：{path}")
    else:
        print("❌ 截图失败")
