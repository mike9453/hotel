# modules/scraper_selenium.py

import time, re, requests, datetime
from dateutil.relativedelta import relativedelta
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
    try:
        resp = requests.head(url, allow_redirects=True, timeout=5)
        return resp.url
    except:
        return url

def parse_time_txt(time_txt: str) -> datetime.date:
    """把 'X 年前'/'X 個月前'/'X 週前'/'X 天前' 轉成實際日期"""
    now = datetime.datetime.now()
    m = re.match(r"(\d+)\s*年前", time_txt)
    if m:
        return (now - relativedelta(years=int(m.group(1)))).date()
    m = re.match(r"(\d+)\s*(?:個)?月前", time_txt)
    if m:
        return (now - relativedelta(months=int(m.group(1)))).date()
    m = re.match(r"(\d+)\s*(?:週|周)前", time_txt)
    if m:
        return (now - datetime.timedelta(weeks=int(m.group(1)))).date()
    m = re.match(r"(\d+)\s*天前", time_txt)
    if m:
        return (now - datetime.timedelta(days=int(m.group(1)))).date()
    m = re.search(r"(\d{4})", time_txt)
    if m:
        return datetime.date(int(m.group(1)), 1, 1)
    return now.date()

def fetch_google_maps_reviews(
    url: str,
    scroll_times: int = 20,
    scroll_pause: float = 1.5,
    start_year: int = None,
    end_year:   int = None,
    debug: bool = True
):
    """
    爬取 Google Maps 評論，最多捲動 scroll_times 次，也會點「更多評論」直到看不到新評論。
    若提供 start_year 與 end_year，則僅保留 start_year <= 年份 < end_year 的評論，
    且必須 end_year - start_year == 1。
    """
    # 年份區間檢查
    if start_year is not None and end_year is not None:
        if end_year - start_year != 1:
            raise ValueError("請選擇相差一年的區間 (end_year − start_year 必須等於 1)！")

    url = expand_url(url)
    driver = init_driver(headless=False)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get(url)
        # (1) 點第一筆搜尋結果
        try:
            first = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "div.section-result, div[data-result-index]")
            ))
            first.click()
            time.sleep(2)
        except:
            pass

        # (2) 點「評論」Tab
        try:
            tab = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//button[@role='tab' and (contains(., '評論') or contains(., 'Reviews'))]"
            )))
            tab.click()
            time.sleep(2)
        except:
            pass

        # (3) 等待至少一則評論
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-review-id]")))

        # (4) 找可捲動容器
        scrollable = driver.execute_script("""
            const c = document.querySelector('[data-review-id]');
            function getScrollParent(n){
              if(!n) return document.scrollingElement||document.documentElement;
              const s = getComputedStyle(n).overflowY;
              return ['auto','scroll'].includes(s)?n:getScrollParent(n.parentElement);
            }
            return getScrollParent(c);
        """)

        # (5) 滾動 + 點更多評論，最多執行 scroll_times 次
        prev_count = 0
        for _ in range(scroll_times):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable)
            time.sleep(scroll_pause)
            # 嘗試點「Load more」
            try:
                more = scrollable.find_element(By.XPATH,
                    ".//button[contains(., 'Load more') or contains(., '顯示更多評論')]"
                )
                more.click()
                time.sleep(scroll_pause)
            except:
                pass

            cards = scrollable.find_elements(By.CSS_SELECTOR, "[data-review-id]")
            curr_count = len(cards)
            if curr_count == prev_count:
                break
            prev_count = curr_count

        html = driver.page_source
        if debug:
            with open("debug_final.html", "w", encoding="utf-8") as f:
                f.write(html)
    finally:
        driver.quit()

    # (6) 解析 & 過濾
    soup = BeautifulSoup(html, "html.parser")
    results, seen = [], set()
    for card in soup.select("[data-review-id]"):
        # 作者
        author_el = card.select_one("div.d4r55")
        author = author_el.get_text(strip=True) if author_el else ""

        # 評分
        rating = None
        star_el = card.select_one("[aria-label*='顆星'],[aria-label*='star']")
        if star_el and star_el.has_attr("aria-label"):
            m = re.search(r"(\d)", star_el["aria-label"])
            rating = int(m.group(1)) if m else None
        if rating is None:
            icons = card.select("span.hCCjke.google-symbols.NhBTye.elGi1d")
            rating = len(icons)

        # 時間文字 & 解析日期
        time_txt = card.select_one("span.rsqaWe, div[class*='review-date']")
        time_txt = time_txt.get_text(strip=True) if time_txt else ""
        date = parse_time_txt(time_txt)

        # 年份過濾
        if start_year is not None and end_year is not None:
            if not (start_year <= date.year < end_year):
                continue

        # 內文
        text_el = (
            card.select_one("span.wiI7pd")
            or card.select_one("span[jsname='bN97Pc']")
            or card.select_one("div.MyEned")
        )
        text = text_el.get_text(strip=True) if text_el else ""
        if not text or text in seen:
            continue
        seen.add(text)

        results.append({
            "author": author,
            "rating": rating,
            "time_txt": time_txt,
            "date": date.isoformat(),
            "text": text
        })

    print(f"[Debug] 抓到 {len(results)} 筆符合條件的評論")
    return results

if __name__ == "__main__":
    reviews = fetch_google_maps_reviews(
        "https://www.google.com/maps/place/YourPlaceID",
        scroll_times=30,
        scroll_pause=1.2,
        start_year=2022,
        end_year=2023,
        debug=True
    )
    for r in reviews:
        print(r)
