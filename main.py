import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WAQI_URL = "https://api.waqi.info/feed/geo:{lat};{lon}/"
TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"


@dataclass
class Weather:
    date: str
    max_temp: float
    max_rain_probability: int


@dataclass
class AirQuality:
    aqi: int
    station: str
    observed_at: str


@dataclass
class Risk:
    level: str
    emoji: str
    reasons: List[str]
    advice: List[str]


def env_float(name: str) -> float:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"Missing environment variable: {name}")
    return float(value)


def env_int(name: str, default: Optional[int] = None) -> int:
    value = os.getenv(name)
    if value is None:
        if default is None:
            raise ValueError(f"Missing environment variable: {name}")
        return default
    return int(value)


def fetch_weather(lat: float, lon: float, timezone: str) -> Weather:
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": timezone,
        "forecast_days": 1,
        "daily": "temperature_2m_max,precipitation_probability_max",
    }
    response = requests.get(OPEN_METEO_URL, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()["daily"]

    return Weather(
        date=data["time"][0],
        max_temp=float(data["temperature_2m_max"][0]),
        max_rain_probability=int(data["precipitation_probability_max"][0]),
    )


def fetch_aqi(lat: float, lon: float, token: str) -> AirQuality:
    url = WAQI_URL.format(lat=lat, lon=lon)
    response = requests.get(url, params={"token": token}, timeout=20)
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") != "ok":
        raise RuntimeError(f"WAQI API error: {payload}")

    data = payload["data"]
    aqi = data.get("aqi")
    if aqi is None or not isinstance(aqi, (int, float)):
        raise RuntimeError("WAQI returned an unavailable AQI value.")

    station = data.get("city", {}).get("name", "Unknown station")
    observed_at = data.get("time", {}).get("s", "Unknown time")
    return AirQuality(int(aqi), station, observed_at)


def evaluate_risk(
    weather: Weather,
    air: AirQuality,
    heat_threshold: float,
    rain_threshold: int,
    aqi_threshold: int,
) -> Risk:
    reasons: List[str] = []
    advice: List[str] = []
    score = 0

    if weather.max_temp >= heat_threshold:
        score += 2
        reasons.append(f"最高溫 {weather.max_temp:.1f}°C ≥ {heat_threshold:.0f}°C")
        advice.append("高溫時段減少長時間曝曬，攜帶飲水並優先選擇有遮蔭路線。")

    if weather.max_rain_probability >= rain_threshold:
        score += 2
        reasons.append(
            f"最高降雨機率 {weather.max_rain_probability}% ≥ {rain_threshold}%"
        )
        advice.append("建議攜帶雨具；騎車或步行者應預留較長通勤時間。")

    if air.aqi >= aqi_threshold:
        score += 2
        reasons.append(f"AQI {air.aqi} ≥ {aqi_threshold}")
        advice.append("空氣品質偏差，敏感族群減少戶外活動；必要時佩戴合適口罩。")

    # Cross-condition escalation.
    if (
        weather.max_temp >= heat_threshold
        and weather.max_rain_probability >= rain_threshold
    ):
        score += 1
        reasons.append("高溫與高降雨機率同時出現")
        advice.append("注意午後天氣快速變化，建議準備室內備援交通方案。")

    if weather.max_rain_probability >= rain_threshold and air.aqi >= aqi_threshold:
        score += 1
        reasons.append("高降雨機率與較差空氣品質同時出現")
        advice.append("若可調整行程，優先選擇大眾運輸並縮短戶外停留。")

    if score >= 6:
        level, emoji = "高風險", "🔴"
        advice.insert(0, "建議優先改搭大眾運輸，必要時考慮延後或調整通勤時間。")
    elif score >= 3:
        level, emoji = "中風險", "🟠"
        advice.insert(0, "通勤前請做好防曬、雨具或空氣品質防護準備。")
    else:
        level, emoji = "低風險", "🟢"
        advice.insert(0, "目前沒有觸發主要風險門檻，正常通勤即可。")

    if not reasons:
        reasons.append("未達任何主要風險門檻")

    # Remove duplicate advice while preserving order.
    advice = list(dict.fromkeys(advice))
    return Risk(level, emoji, reasons, advice)


def build_message(
    location: str,
    weather: Weather,
    air: AirQuality,
    risk: Risk,
    timezone: str,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reasons = "\n".join(f"• {item}" for item in risk.reasons)
    advice = "\n".join(f"• {item}" for item in risk.advice)

    return (
        f"🚦 智慧通勤風險通知\n"
        f"━━━━━━━━━━━━━━\n"
        f"📍 地點：{location}\n"
        f"📅 預報日期：{weather.date}\n"
        f"🕒 通知時間：{now} ({timezone})\n\n"
        f"🌡️ 最高溫：{weather.max_temp:.1f}°C\n"
        f"🌧️ 最高降雨機率：{weather.max_rain_probability}%\n"
        f"🌫️ AQI：{air.aqi}（{air.station}）\n"
        f"🕐 AQI 更新：{air.observed_at}\n\n"
        f"{risk.emoji} 風險等級：{risk.level}\n\n"
        f"⚠️ 觸發條件\n{reasons}\n\n"
        f"🚌 通勤建議\n{advice}\n\n"
        f"ℹ️ 本通知為自動化風險提示，請以實際路況與官方警報為準。"
    )


def send_telegram(token: str, chat_id: str, message: str) -> None:
    url = TELEGRAM_URL.format(token=token)
    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")


def main() -> int:
    try:
        lat = env_float("LOCATION_LAT")
        lon = env_float("LOCATION_LON")
        location = os.getenv("LOCATION_NAME", "指定地點")
        timezone = os.getenv("TIMEZONE", "Asia/Taipei")

        heat_threshold = env_float("HEAT_THRESHOLD")
        rain_threshold = env_int("RAIN_THRESHOLD")
        aqi_threshold = env_int("AQI_THRESHOLD")

        waqi_token = os.environ["WAQI_TOKEN"]
        telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]
        telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]

        weather = fetch_weather(lat, lon, timezone)
        air = fetch_aqi(lat, lon, waqi_token)
        risk = evaluate_risk(
            weather,
            air,
            heat_threshold,
            rain_threshold,
            aqi_threshold,
        )
        message = build_message(location, weather, air, risk, timezone)

        print(message)
        send_telegram(telegram_token, telegram_chat_id, message)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
