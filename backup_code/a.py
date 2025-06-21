import os
import json
import time
import threading
import openai
import tiktoken
from openai import OpenAIError
from flask import Flask, render_template, request
from modules.scraper_selenium import fetch_google_maps_reviews
from modules.analysis import keyword_stats
import re
from collections import Counter
from datetime import datetime
from markupsafe import escape, Markup
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI


app = Flask(__name__)

@app.template_filter('nl2br')
def nl2br(s):
    # 先把文字 escape，再把換行換成 <br>
    escaped = escape(s)
    return Markup(escaped.replace('\n', '<br>\n'))

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="<OPENROUTER_API_KEY>",
)

openai.api_key   = os.getenv("OPENROUTER_API_KEY")
openai.api_base  = "https://openrouter.ai/api/v1" 

# 全域鎖與時間戳，用來做 client 端限速
lock = threading.Lock()
_last_chat_time = 0.0
# gpt-3.5-turbo 是 3 RPM → 每分鐘 3 次呼叫 → MIN_CHAT_INTERVAL = 60 / 3 = 20 秒
MIN_CHAT_INTERVAL = 20.0  

# 初始化 tiktoken
ENC = tiktoken.get_encoding("cl100k_base")
MAX_TOKENS_PER_CHUNK = 1000  # 每個 chunk 最多大約 1000 tokens

def throttle_chat():
    """確保每次呼叫 ChatCompletion.create 間隔 >= MIN_CHAT_INTERVAL"""
    global _last_chat_time
    with lock:
        now = time.time()
        elapsed = now - _last_chat_time
        if elapsed < MIN_CHAT_INTERVAL:
            time.sleep(MIN_CHAT_INTERVAL - elapsed)
        _last_chat_time = time.time()

def safe_create(**kwargs):
    """
    在呼叫 chat.completions.create 前做限速，
    遇到 429 時指數 backoff 共重試 5 次。
    """
    max_retries = 5
    for i in range(max_retries):
        throttle_chat()
        try:
            return openai.chat.completions.create(**kwargs)
        except OpenAIError as e:
            msg = str(e)
            if "429" not in msg:
                raise
            wait = 2 ** i
            if hasattr(e, "http_headers"):
                ra = e.http_headers.get("retry-after")
                if ra and ra.isdigit():
                    wait = int(ra)
            print(f"⚠️ RateLimitError, retry #{i+1} in {wait}s …")
            time.sleep(wait)
    throttle_chat()
    return openai.chat.completions.create(**kwargs)

def extract_place_id(url):
    m = re.search(r"/place/([^/?]+)", url)
    return m.group(1) if m else None

def chunk_by_tokens(texts):
    """
    根據 tiktoken 把多個文本切成多個 token 數量 <= MAX_TOKENS_PER_CHUNK 的 chunk
    """
    chunks = []
    current, count = [], 0
    for txt in texts:
        tlen = len(ENC.encode(txt))
        if count + tlen > MAX_TOKENS_PER_CHUNK:
            chunks.append(current)
            current, count = [], 0
        current.append(txt)
        count += tlen
    if current:
        chunks.append(current)
    return chunks

@app.route("/", methods=["GET", "POST"])
def index():
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

                reviews = fetch_google_maps_reviews(
                    place_url,
                    scroll_times=15,
                    scroll_pause=1.5,
                    start_year=start_year,
                    end_year=end_year,
                    debug=True
                )

                texts = [r['text'] for r in reviews]
                stats_df = keyword_stats(texts, top_n=20)
                stats = stats_df.to_dict(orient="records")

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
    reviews = json.loads(request.form['reviews_json'])
    user_question = request.form['user_question'].strip()

    # 將所有 review 文本切成 token-based chunks
    texts = [r["text"] for r in reviews]
    chunks = chunk_by_tokens(texts)

    # 對每個 chunk 做單獨摘要
    summaries = []
    for chunk in chunks:
        chunk_prompt = (
            "請將以下消費者評論濃縮成不超過200字的摘要：\n\n"
            + "\n".join(chunk)
        )
        resp = safe_create(
            model="deepseek/deepseek-r1-0528:free",
            messages=[{"role":"user","content":chunk_prompt}],
            max_tokens=200,
            temperature=0.3
        )
        if isinstance(resp, str):
            summaries.append(resp)
        else:
            summaries.append(resp.choices[0].message.content)

    # 合併所有 chunk 摘要，再做最終摘要
    combined_prompt = (
        "以下是多段消費者評論摘要，請綜合並濃縮成一個不超過300字的最終摘要：\n\n"
        + "\n".join(summaries)
    )
    final_resp = safe_create(
        model="deepseek/deepseek-r1-0528:free",
        messages=[{"role":"user","content":combined_prompt}],
        max_tokens=300,
        temperature=0.3
    )
    if isinstance(final_resp, str):
        final_summary = final_resp
    else:
        final_summary = final_resp.choices[0].message.content

    # 最後以 final_summary + user_question 取得回答
    answer_prompt = (
        f"以下是整理後的評論摘要：\n{final_summary}\n\n"
        f"請根據上述摘要回答使用者問題：{user_question}"
    )
    answer_resp = safe_create(
        model="deepseek/deepseek-r1-0528:free",
        messages=[
            {"role":"system","content":"你是一個擅長分析消費者評論的助手。"},
            {"role":"user","content":answer_prompt}
        ],
        max_tokens=500,
        temperature=0.5
    )
    if isinstance(answer_resp, str):
        answer = answer_resp
    else:
        answer = answer_resp.choices[0].message.content

    return render_template("answer.html", question=user_question, answer=answer)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
