import os
import json
import time
import openai
from openai import OpenAIError
from flask import Flask, render_template, request
from modules.scraper_selenium import fetch_google_maps_reviews
from modules.analysis import keyword_stats
import re
from collections import Counter
from datetime import datetime, date

app = Flask(__name__)

# 初始化 OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_place_id(url):
    """
    從 Google Maps URL 中抽取 place_id
    支援格式如：https://www.google.com/maps/place/<place_id>/...
    """
    m = re.search(r"/place/([^/?]+)", url)
    return m.group(1) if m else None

def safe_create(**kwargs):
    """
    使用 exponential backoff 重試機制呼叫 OpenAI chat completions，
    遇到 429（RateLimitError）才重試，其它錯誤則直接冒泡。
    """
    max_retries = 3
    for i in range(max_retries):
        try:
            return openai.chat.completions.create(**kwargs)
        except OpenAIError as e:
            msg = str(e)
            # 只對 429 做重試
            if "429" not in msg:
                raise
            wait = 2 ** i  # 1s, 2s, 4s
            print(f"⚠️ RateLimitError, retry #{i+1} after {wait}s…")
            time.sleep(wait)
    # 最後一次不捕，讓最終錯誤被外層處理
    return openai.chat.completions.create(**kwargs)

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

        place_id = extract_place_id(place_url)
        if not place_id:
            error = "無法從網址抽出 place_id，請確認格式"
        else:
            try:
                start_year = int(start_year)
                end_year   = int(end_year)

                # 1. 爬取評論，並過濾年份
                reviews = fetch_google_maps_reviews(
                    place_url,
                    scroll_times=15,
                    scroll_pause=1.5,
                    start_year=start_year,
                    end_year=end_year,
                    debug=True
                )

                # 2. 提取文字，做關鍵字統計
                texts = [r['text'] for r in reviews]
                stats_df = keyword_stats(texts, top_n=20)
                stats = stats_df.to_dict(orient="records")

                # —— 星等分佈統計 ——
                ratings = [r['rating'] for r in reviews if r.get('rating') is not None]
                cnt = Counter(ratings)
                rating_counts = {star: cnt.get(star, 0) for star in [5,4,3,2,1]}

                return render_template(
                    "results.html",
                    reviews=reviews,
                    stats=stats,
                    rating_counts=rating_counts,
                    start_year=start_year,
                    end_year=end_year
                )
            except ValueError as ve:
                error = str(ve)
            except Exception as e:
                error = "爬蟲發生錯誤：" + str(e)

    return render_template("index.html", years=years, error=error)

@app.route("/ask", methods=["POST"])
def ask():
    # （可選）印出 key 與使用量，方便 debug
    print(">>> OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))
    print(">>> openai.api_key      :", openai.api_key)
    today = date.today().isoformat()
    try:
        usage = openai.usage.records.list(start_date=today, end_date=today)
        print("📊 今日使用紀錄：", usage.data)
    except Exception as e:
        print("❌ 查 usage 失敗：", e)

    # 從隱藏欄位取出 reviews JSON
    reviews = json.loads(request.form['reviews_json'])
    user_question = request.form['user_question'].strip()

    # 準備 prompt
    review_texts = [f"{r['author']} ({r['rating']}★)：『{r['text']}』" for r in reviews]
    context = "\n".join(review_texts)
    prompt = (
        "以下是 Google Maps 店家的多筆消費者評論：\n"
        f"{context}\n\n"
        f"請根據上述評論，回答使用者的問題：{user_question}"
    )

    # 呼叫 OpenAI（透過 safe_create 自動重試）
    try:
        resp = safe_create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一個擅長分析消費者評論的助手。"},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.5,
            max_tokens=500,
        )
        answer = resp.choices[0].message.content
        return render_template("answer.html", question=user_question, answer=answer)

    except OpenAIError as e:
        msg = str(e)
        if "429" in msg or "insufficient_quota" in msg:
            error = "系統忙碌或呼叫頻率過高，請稍後再試。"
        else:
            error = f"OpenAI 錯誤：{msg}"
        return render_template("answer.html", question=user_question, answer=None, error=error)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
