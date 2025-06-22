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
    """將短網址展開到最終的長網址"""
    try:
        resp = requests.head(url, allow_redirects=True, timeout=5)
        return resp.url
    except:
        return url

def fetch_google_maps_reviews(url, scroll_times=10, scroll_pause=1.5, debug=True):
    """
    使用 Selenium 爬取 Google Maps 店家評論，並在 debug 模式下將完整頁面寫入 debug 文件
    :param url: Google Maps 店家完整或短網址
    :param scroll_times: 滾動次數
    :param scroll_pause: 每次滾動後等待秒數
    :param debug: 是否輸出 debug 文件
    :return: list of dict ({author, rating, time, text})
    """
    # 若為短網址，先展開
    url = expand_url(url)

    # 啟動瀏覽器（debug 時可關閉 headless 以便觀察）
    driver = init_driver(headless=False)
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    # 初始 DOM 存檔
    if debug:
        with open("debug_init.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("[Debug] 已輸出 debug_init.html（載入後、點擊前）")

    # 嘗試點擊商家詳情搜尋結果第一筆（若此為搜尋結果頁）
    try:
        first = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.section-result"))
        )
        first.click()
        time.sleep(3)
        print("[Debug] 點擊第一筆搜尋結果，進入詳細頁")
    except:
        print("[Debug] 假設已在商家詳細頁，無需點擊搜尋結果")

    # 再次等待詳細面板載入
    time.sleep(3)

    # 嘗試點擊「全部評論」按鈕
    try:
        btn = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//button[contains(., '全部評論') or contains(., '查看全部') or contains(., 'All reviews')]"
        )))
        btn.click()
        print("[Debug] 成功點擊全部評論按鈕")
    except Exception as e:
        print("[Warning] 未找到全部評論按鈕，將整頁滾動載入：", e)

    # 滾動載入更多評論
    body = driver.find_element(By.TAG_NAME, 'body')
    for _ in range(scroll_times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)

    # 最終 DOM 存檔
    html = driver.page_source
    if debug:
        with open("debug_final.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("[Debug] 已輸出 debug_final.html（滾動後）")

    driver.quit()

    # 解析評論
    soup = BeautifulSoup(html, 'html.parser')

    # 分別擷取作者、評分、時間、內文
    authors = [a.get_text(strip=True) for a in soup.select('div.d4r55')]
    ratings = []
    for span in soup.select('span.kvMYJc'):
        label = span.get('aria-label', '')
        try:
            ratings.append(int(label[0]))
        except:
            ratings.append(None)
    times = [t.get_text(strip=True) for t in soup.select('span.rsqaWe')]
    texts = [t.get_text(strip=True) for t in soup.select('span.wiI7pd')]

    # 對齊並組成結果
    count = min(len(authors), len(ratings), len(times), len(texts))
    results = []
    for i in range(count):
        results.append({
            'author': authors[i],
            'rating': ratings[i],
            'time': times[i],
            'text': texts[i]
        })

    print(f"[Debug] 總共擷取評論：{len(results)} 筆")
    return results

if __name__ == '__main__':
    test_url = 'https://www.google.com/maps/place/...'
    data = fetch_google_maps_reviews(test_url)
    for r in data:
        print(r)
