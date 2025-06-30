# CLAUDE.md - Google Maps 評論分析系統

## 專案概述
這是一個基於 Flask 的 Google Maps 評論分析系統，整合網路爬蟲、資料分析和 AI 輔助分析功能。系統可以自動爬取指定店家的 Google Maps 評論，進行關鍵字統計和星等分析，並提供 AI 智能問答功能。

## 技術架構
- **後端框架**: Flask + Jinja2
- **爬蟲工具**: Selenium + BeautifulSoup
- **資料分析**: jieba 斷詞 + pandas 統計
- **前端**: Bootstrap 5 + Chart.js 圖表
- **AI 服務**: OpenRouter API (DeepSeek-R1 模型)
- **容器化**: Docker 支援

## 專案結構
```
├── app.py                    # 主要 Flask 應用程式
├── modules/
│   ├── __init__.py          # Python 模組初始化
│   ├── scraper_selenium.py  # Google Maps 評論爬蟲
│   └── analysis.py          # 中文關鍵字分析模組
├── templates/               # Jinja2 模板
│   ├── index.html          # 首頁表單
│   ├── results.html        # 分析結果頁面
│   └── answer.html         # AI 問答頁面
├── backup_code/            # 備份程式碼
├── requirements.txt        # Python 套件需求
├── Dockerfile             # Docker 容器配置
└── .env                   # 環境變數 (需自行建立)
```

## 環境設定
### 必要套件
主要依賴套件包括：
- Flask 3.1.1 (web 框架)
- Selenium 4.33.0 (網頁自動化)
- BeautifulSoup4 4.13.4 (HTML 解析)
- jieba 0.42.1 (中文分詞)
- pandas 2.3.0 (資料分析)
- openai 1.88.0 (OpenRouter API 整合)
- python-dotenv 1.1.0 (環境變數管理)

### 環境變數
需要建立 `.env` 檔案並設定：
```
OPENROUTER_API_KEY=your_openrouter_api_key
```

## 主要功能模組

### 1. app.py - Flask 主應用
- 路由處理: `/` (首頁), `/ask` (AI 問答)
- Google Maps 網址解析 (`extract_place_id`)
- OpenRouter AI 整合
- 模板過濾器 (`nl2br` 用於換行處理)

### 2. modules/scraper_selenium.py - 評論爬蟲
主要函數：
- `fetch_google_maps_reviews()`: 主要爬蟲函數
- `init_driver()`: 初始化 Chrome WebDriver
- `parse_time_txt()`: 解析時間文字為日期
- `expand_url()`: 處理短網址展開

爬蟲特色：
- 自動處理 Google Maps 評論頁面導航
- 支援年份區間過濾 (必須相差一年)
- 智能滾動加載更多評論
- 重複內容去除

### 3. modules/analysis.py - 關鍵字分析
- `keyword_stats()`: 使用 jieba 進行中文分詞和統計
- 輸出 pandas DataFrame 格式結果

## 使用流程
1. 啟動服務: `python app.py` (預設 port 5000)
2. 輸入 Google Maps 店家 URL
3. 選擇年份區間 (相差一年)
4. 檢視評論統計和圖表
5. 使用 AI 問答功能進行深度分析

## 開發建議
### 測試
- 無特定測試框架，建議手動測試主要流程
- 檢查爬蟲功能：確認能正確抓取評論
- 檢查 AI 功能：確認 OpenRouter API 連線正常

### 部署
- 支援 Docker 容器化部署
- 生產環境建議使用 gunicorn (已列在 requirements.txt)
- 確保 Chrome 和 chromedriver 可用於 Selenium

### 程式碼風格
- 使用繁體中文註解和錯誤訊息
- Flask 路由使用 POST/GET 混合處理
- 錯誤處理：捕獲 Selenium 和 OpenAI API 例外
- 模板使用 Jinja2 語法，支援自定義過濾器

### 潛在改善點
- 加入停用詞清單提升關鍵字品質
- 優化 JSON 資料傳遞，改用 session 快取
- 增加情感分析功能
- 加強錯誤處理和使用者體驗

## 安全注意事項
- API 金鑰透過環境變數管理
- 用戶輸入經過適當的 escape 處理
- 爬蟲遵循合理的延遲時間避免過度請求