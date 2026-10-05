import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import Weather, AirQuality, evaluate_risk


def test_low_risk():
    weather = Weather("2026-10-05", 28.0, 20)
    air = AirQuality(50, "Test", "2026-10-05 06:00")
    risk = evaluate_risk(weather, air, 35, 60, 100)
    assert risk.level == "低風險"


def test_high_heat_rain_aqi():
    weather = Weather("2026-10-05", 36.0, 80)
    air = AirQuality(160, "Test", "2026-10-05 06:00")
    risk = evaluate_risk(weather, air, 35, 60, 100)
    assert risk.level == "高風險"
    assert len(risk.reasons) >= 3


def test_medium_rain():
    weather = Weather("2026-10-05", 35.0, 70)
    air = AirQuality(50, "Test", "2026-10-05 06:00")
    risk = evaluate_risk(weather, air, 35, 60, 100)
    assert risk.level == "中風險"
