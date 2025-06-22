# 1. 選一個輕量但支援 apt 的 Python 版本
FROM python:3.10-slim

# 2. 安裝系統依賴：chromium + chromedriver
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      chromium chromium-driver \
 && rm -rf /var/lib/apt/lists/*

# 3. 設定工作目錄
WORKDIR /app

# 4. 複製所有程式碼到 /app
COPY . /app

# 5. 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 6. 設環境變數，讓 selenium 找到 chromium
ENV CHROME_BIN=/usr/bin/chromium
# 若需要其他 .env 變數，也可以在這裡列
# ENV OPENROUTER_API_KEY=你的金鑰

# 7. 暴露 port
EXPOSE 5000

# 8. 預設啟動命令
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
