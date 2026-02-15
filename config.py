from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Plan:
    code: str
    title: str
    price_rub: int
    duration: timedelta


PLANS = {
    "m1": Plan(code="m1", title="1 месяц", price_rub=300, duration=timedelta(days=30)),
    "m3": Plan(code="m3", title="3 месяца", price_rub=800, duration=timedelta(days=90)),
    "m12": Plan(code="m12", title="12 месяцев", price_rub=2800, duration=timedelta(days=365)),
}


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
PAYMENT_PHONE = os.getenv("PAYMENT_PHONE", "")

THREEXUI_BASE_URL = os.getenv("THREEXUI_BASE_URL", "").rstrip("/")
THREEXUI_USERNAME = os.getenv("THREEXUI_USERNAME", "")
THREEXUI_PASSWORD = os.getenv("THREEXUI_PASSWORD", "")
THREEXUI_INBOUND_ID = int(os.getenv("THREEXUI_INBOUND_ID", "1"))

DB_PATH = os.getenv("DB_PATH", "botvpn.sqlite3")
XRAY_ACCESS_TEMPLATE = os.getenv(
    "XRAY_ACCESS_TEMPLATE",
    "✅ Подписка активирована!\nUUID: {uuid}\nЛогин: {email}\nДействует до: {expiry_date}",
)


def validate_settings() -> None:
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not ADMIN_IDS:
        missing.append("ADMIN_IDS")
    if not PAYMENT_PHONE:
        missing.append("PAYMENT_PHONE")
    if not THREEXUI_BASE_URL:
        missing.append("THREEXUI_BASE_URL")
    if not THREEXUI_USERNAME:
        missing.append("THREEXUI_USERNAME")
    if not THREEXUI_PASSWORD:
        missing.append("THREEXUI_PASSWORD")

    if missing:
        raise RuntimeError(f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}")
