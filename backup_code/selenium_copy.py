# modules/scraper_selenium.py

import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def init_driver(headless=False):
    opts = Options()
    if headless:
        opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts
    )
    driver.set_window_size(1920, 1080)
    return driver

def expand_url(url):
    """將短網址展開到最終長網址"""
    try:
        resp = requests.head(url, allow_redirects=True, timeout=5)
        return resp.url
    except:
        return url

def fetch_google_maps_reviews(url, scroll_times=20, scroll_pause=1.5, debug=True):
    """
    用 Selenium 全量爬取 Google Maps 店家評論：
      1) 動態找評論容器並滾動到底
      2) 萃取 author/rating/time/text
      3) 回傳 list of dict
    """
    url = expand_url(url)
    driver = init_driver(headless=False)
    wait = WebDriverWait(driver, 20)
    html = None

    try:
        driver.get(url)
        # (1) 如果是搜尋結果頁，點第一筆
        try:
            first = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.section-result")))
            first.click()
            time.sleep(2)
        except:
            pass

        # (2) 點「評論」Tab
        try:
            tab = wait.until(EC.element_to_be_clickable((By.XPATH,
                "//button[@role='tab' and contains(., '評論')]"
            )))
            tab.click()
            time.sleep(2)
        except:
            pass

        # (3) 等待至少一則評論卡片
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-review-id]")))

        # (4) 動態找 scrollable container
        scrollable = driver.execute_script("""
            const card = document.querySelector('[data-review-id]');
            function getScrollParent(node) {
                if (!node) return document.scrollingElement || document.documentElement;
                const style = window.getComputedStyle(node);
                if (['auto','scroll'].includes(style.overflowY)) return node;
                return getScrollParent(node.parentElement);
            }
            return getScrollParent(card);
        """)

        # (5) 滾動到底
        prev = 0
        for _ in range(scroll_times):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable)
            time.sleep(scroll_pause)
            curr = len(scrollable.find_elements(By.CSS_SELECTOR, "[data-review-id]"))
            if curr == prev:
                break
            prev = curr

        # (6) 點一次「顯示更多評論」(若有)
        try:
            more = scrollable.find_element(By.XPATH,
                ".//button[contains(., '顯示更多評論') or contains(., 'Load more reviews')]"
            )
            more.click()
            time.sleep(2)
        except:
            pass

        # (7) 取得 page_source
        try:
            html = driver.page_source
        except Exception as e:
            print("[Warning] 取得 page_source 失敗，重試：", e)
            time.sleep(2)
            html = driver.page_source

        if debug:
            with open("debug_final.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("[Debug] 已輸出 debug_final.html")

    finally:
        driver.quit()

    # 如果 html 拿不到，就回空 list
    if not html:
        return []

    # (8) 解析評論
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    seen = set()

    for card in soup.select("[data-review-id]"):
        # 作者
        author_el = card.select_one("div.d4r55")
        author = author_el.get_text(strip=True) if author_el else ""

        # 星等（Multi-fallback）
        rating = None
        # a) aria-label
        star_el = card.select_one("[aria-label*='顆星'], [aria-label*='star']")
        if star_el and star_el.has_attr("aria-label"):
            try:
                rating = int(star_el["aria-label"][0])
            except:
                pass
        # b) 用★ icon 計數
        if rating is None:
            icons = card.select("span.hCCjke.google-symbols.NhBTye.elGi1d")
            if icons:
                rating = len(icons)

        # 時間
        time_el = card.select_one("span.rsqaWe, div[class*='review-date']")
        time_txt = time_el.get_text(strip=True) if time_el else ""

        # 內文
        text_el = (
            card.select_one("span.wiI7pd")
            or card.select_one("span[jsname='bN97Pc']")
            or card.select_one("div.MyEned")
        )
        text = text_el.get_text(strip=True) if text_el else ""

        # 過濾空白 & 重複
        if not text or text in seen:
            continue
        seen.add(text)

        results.append({
            "author": author,
            "rating": rating,
            "time": time_txt,
            "text": text
        })

    print(f"[Debug] 抓到 {len(results)} 筆評論")
    return results


if __name__ == "__main__":
    url = "https://www.google.com/maps/place/YourPlaceID"
    for r in fetch_google_maps_reviews(url):
        print(r)
