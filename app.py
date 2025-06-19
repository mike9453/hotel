from flask import Flask, render_template, request
from modules.scraper_selenium import fetch_google_maps_reviews
from modules.analysis import keyword_stats
import re
from collections import Counter
from datetime import datetime

app = Flask(__name__)

def extract_place_id(url):
    """
    從 Google Maps URL 中抽取 place_id
    支援格式如：https://www.google.com/maps/place/<place_id>/...
    """
    m = re.search(r"/place/([^/?]+)", url)
    return m.group(1) if m else None

@app.route("/", methods=["GET", "POST"])
def index():
    # 產生可選年份：從今年往前推 20 年
    current_year = datetime.now().year
    years = list(range(current_year, current_year - 21, -1))

    error = None
    if request.method == "POST":
        place_url  = request.form.get("place_url", "").strip()
        start_year = request.form.get("start_year")
        end_year   = request.form.get("end_year")

        # 確認 place_id
        place_id = extract_place_id(place_url)
        if not place_id:
            error = "無法從網址抽出 place_id，請確認格式"
        else:
            # 嘗試轉成整數並呼叫爬蟲
            try:
                start_year = int(start_year)
                end_year   = int(end_year)

                # 1. 爬取評論，並過濾年份
                reviews = fetch_google_maps_reviews(
                    place_url,
                    start_year=start_year,
                    end_year=end_year,
                    scroll_times=15,
                    scroll_pause=1.5
                )

                # 2. 提取文字，做關鍵字統計
                texts = [r["text"] for r in reviews]
                stats_df = keyword_stats(texts, top_n=20)
                stats = stats_df.to_dict(orient="records")

                # —— 星等分佈統計 —— 
                ratings = [r["rating"] for r in reviews if r.get("rating") is not None]
                cnt = Counter(ratings)
                rating_counts = {star: cnt.get(star, 0) for star in [5,4,3,2,1]}

                # 3. 顯示結果頁
                return render_template(
                    "results.html",
                    reviews=reviews,
                    stats=stats,
                    rating_counts=rating_counts,
                    start_year=start_year,
                    end_year=end_year
                )
            except ValueError as ve:
                # 包含年份區間檢查失敗或轉型錯誤
                error = str(ve)
            except Exception as e:
                error = "爬蟲發生錯誤：" + str(e)

    # GET 或有錯誤時，顯示查詢頁
    return render_template("index.html", years=years, error=error)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
