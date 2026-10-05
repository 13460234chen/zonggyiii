# 🚦 智慧通勤風險通知系統

一套以 **GitHub Actions + Python + Open-Meteo + WAQI + Telegram Bot** 建立的自動通勤風險通知系統。

每天平日早上自動執行：

1. 取得指定地點當日最高溫。
2. 取得當日最高降雨機率。
3. 取得指定座標附近的即時 AQI。
4. 依多重門檻計算「低／中／高風險」。
5. 產生完整通勤建議。
6. 透過 Telegram Bot 發送通知。

## 1. 專案結構

```text
smart_commute_risk/
├── .github/
│   └── workflows/
│       └── commute.yml
├── tests/
│   └── test_risk.py
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

## 2. 風險規則

預設門檻：

| 條件 | 門檻 | 基本分數 |
|---|---:|---:|
| 最高溫 | ≥ 35°C | +2 |
| 最高降雨機率 | ≥ 60% | +2 |
| AQI | ≥ 100 | +2 |
| 高溫 + 高降雨機率 | 同時成立 | +1 |
| 高降雨機率 + AQI 偏高 | 同時成立 | +1 |

風險等級：

- `0–2`：🟢 低風險
- `3–5`：🟠 中風險
- `6+`：🔴 高風險

門檻可在 GitHub Repository Variables 修改，不必改 Python。

## 3. API

### 天氣：Open-Meteo

使用 `/v1/forecast` 的 daily：

- `temperature_2m_max`
- `precipitation_probability_max`

Open-Meteo 的 daily API 直接提供每日最高溫與最高降水機率。

### AQI：WAQI

使用地理座標查詢：

```text
https://api.waqi.info/feed/geo:{lat};{lon}/?token=TOKEN
```

需要 WAQI token。

### Telegram

使用 Bot API 的 `sendMessage` 發送文字通知。

## 4. GitHub 設定

進入：

`Repository → Settings → Secrets and variables → Actions`

### Variables

新增：

```text
LOCATION_NAME
LOCATION_LAT
LOCATION_LON
TIMEZONE
HEAT_THRESHOLD
RAIN_THRESHOLD
AQI_THRESHOLD
```

例如：

```text
LOCATION_NAME = 桃園市
LOCATION_LAT = 24.9937
LOCATION_LON = 121.3010
TIMEZONE = Asia/Taipei
HEAT_THRESHOLD = 35
RAIN_THRESHOLD = 60
AQI_THRESHOLD = 100
```

### Secrets

新增：

```text
WAQI_TOKEN
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

不要把這些 token 直接寫入程式或 commit 到 Git。

## 5. 建立 Telegram Bot

在 Telegram 搜尋 `@BotFather`：

1. 執行 `/newbot`
2. 取得 Bot Token。
3. 把 Bot 加入要接收通知的聊天室，或先對 Bot 傳訊息。
4. 取得對應的 `chat_id`。
5. 將 Token 與 chat ID 放進 GitHub Secrets。

## 6. 取得 WAQI Token

向 World Air Quality Index Project 申請 API token，放入：

```text
WAQI_TOKEN
```

## 7. 本機測試

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

載入 `.env` 後執行：

```bash
python main.py
```

也可以先跑單元測試：

```bash
python -m pytest
```

## 8. 手動測試 GitHub Actions

Workflow 包含：

```yaml
workflow_dispatch:
```

所以部署後可以從：

`Actions → Smart Commute Risk Notification → Run workflow`

手動執行，不必等排程。

## 9. 預設通知時間

目前設定：

```yaml
cron: "30 6 * * 1-5"
timezone: "Asia/Taipei"
```

也就是週一至週五台灣時間 06:30。

如果希望 07:00 通知，改成：

```yaml
cron: "0 7 * * 1-5"
```

GitHub Actions 官方文件支援在 schedule 中指定 IANA timezone。

## 10. 安全與可靠性

- Token 全部使用 GitHub Secrets。
- 一般設定使用 GitHub Variables。
- API request 設定 timeout。
- API 非成功狀態會讓 workflow 失敗，方便追蹤。
- Telegram 訊息保留資料來源時間，避免把過期 AQI 誤當即時資訊。
- GitHub Actions 使用 concurrency，避免同一時間重複執行。

> 本系統是風險提示工具，不取代氣象署、環境部、道路交通或其他官方即時警報。
