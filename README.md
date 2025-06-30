# Google Maps 評論分析系統

此專案為結合網路爬蟲、資料分析、AI 應用的 Flask 網頁應用，實際展示 Google Maps 評論爬取、評論星等、關鍵字統計與 AI 智能輔助分析。

## 技術架構

- **後端框架**：Flask + Jinja2
- **爬蟲工具**：Selenium + BeautifulSoup
- **資料分析**：jieba 斷詞 + pandas 統計
- **前端呈現**：Bootstrap 5 + Chart.js 圖表
- **AI串接與分析**：結合 AI 模型（OpenRouter 大語言模型）輔助分析評論內容

---

## 主要功能

- 自動化爬取 Google Maps 店家評論
- 過濾指定年份評論區間
- 評論星數 + 關鍵字統計與視覺化圖表
- AI 自然語言互動，提供評論總結、趨勢判斷等輔助分析

---

## 專案結構

```
├─ app.py                  # Flask 主程式
├─ modules/
│  ├─ scraper_selenium.py  # 評論爬蟲模組
│  └─ analysis.py          # 中文關鍵字統計模組
├─ templates/              # 前端模板
│  ├─ index.html           # 首頁輸入表單
│  ├─ results.html         # 分析結果與圖表
│  └─ answer.html          # AI 回答頁面
├─ .env                    # 環境變數 (API 金鑰)
└─ requirements.txt        # 套件需求列表
```

---

## 環境安裝

1. 安裝套件：
   
   pip install -r requirements.txt
   
2. 建立 `.env` 檔案，填入 OpenRouter 金鑰：
   
   OPENROUTER_API_KEY=你的API金鑰
   
3. 確認已安裝 Google Chrome，`webdriver_manager` 會自動處理 chromedriver。

   在linux安裝google瀏覽器

   wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
   sudo apt install -y ./google-chrome-stable_current_amd64.deb
   google-chrome --version
 


---

## 使用說明

1. 啟動服務：
   
   python app.py
   
2. 瀏覽器開啟 [http://localhost:5000]
3. 輸入 Google Maps 店家網址與選擇年份區間（相差一年）
4. 查看評論列表、星等分佈、關鍵字統計
5. 可進一步向 AI 提問，獲取智能評論分析

---


## 未來規劃

- 優化 JSON 資料傳遞，改用 session 快取
- 加入停用詞清單，提升關鍵字品質
- 情感分析、評論分群功能擴充
- 改用 Docker 容器化部署

---





