import os
import json
import time
import threading
import openai
import tiktoken
from flask import Flask, render_template, request
from modules.scraper_selenium import fetch_google_maps_reviews
from modules.analysis import keyword_stats
import re
from collections import Counter
from datetime import datetime
from markupsafe import escape, Markup
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError   # 注意這裡改成從 openai import OpenAI

load_dotenv()
app = Flask(__name__)

# 在程式一開始就建立好 OpenRouter client
router_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)



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

def extract_place_id(url):
    m = re.search(r"/place/([^/?]+)", url)
    return m.group(1) if m else None

@app.template_filter('nl2br')
def nl2br(s):
    # 先把文字 escape，再把換行換成 <br>
    escaped = escape(s)
    return Markup(escaped.replace('\n', '<br>\n'))

@app.route("/ask", methods=["POST"])
def ask():
    error = None
    try:
        reviews = json.loads(request.form["reviews_json"])
        question = request.form["user_question"].strip()
        if not question:
            raise ValueError("請輸入問題。")

        # 合併所有評論文字
        texts = [r.get("text","") for r in reviews]
        content = "\n\n".join(texts)

        messages = [
            {"role": "system", "content": "從現在開始，請全部使用繁體中文回答所有問題。"},
            {"role": "system", "content": "你是一個專業的店家評論分析助理。"},
            {"role": "user",   "content": f"以下是所有評論：\n\n{content}"},
            {"role": "user",   "content": question}
        ]

        # 多給一些 max_tokens，避免回答被截斷
        resp = router_client.chat.completions.create(
            model="deepseek/deepseek-r1-0528",
            messages=messages,
            temperature=0.7,
            max_tokens=2000,    # 原本 800 提升到 1500
            extra_headers={},
            extra_body={}
        )
        answer_raw = resp.choices[0].message.content.strip()

        # 把 AI 回傳中的 <br> 標籤換成換行
        answer = re.sub(r'<br\s*/?>', '\n', answer_raw)

        # 如果模型真的跑到 token 上限，finish_reason 會是 "length"
        if resp.choices[0].finish_reason == "length":
            answer += "\n\n（⚠️ 回答長度達模型上限，回答已中斷。）"

    except OpenAIError as e:
        error = f"AI 呼叫失敗：{e}"
        question = request.form.get("user_question","")
        answer = None
    except Exception as e:
        error = str(e)
        question = request.form.get("user_question","")
        answer = None

    return render_template(
        "answer.html",
        error=error,
        question=question,
        answer=answer,
        reviews_json=request.form["reviews_json"]
    )




if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
