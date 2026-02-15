from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests


@dataclass
class XUIClient:
    uuid: str
    email: str
    expiry_date: datetime


class ThreeXUI:
    def __init__(self, base_url: str, username: str, password: str, inbound_id: int):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.inbound_id = inbound_id
        self.session = requests.Session()

    def login(self) -> None:
        resp = self.session.post(
            f"{self.base_url}/login",
            data={"username": self.username, "password": self.password},
            timeout=20,
        )
        resp.raise_for_status()

    def create_client(self, tg_user_id: int, days: int) -> XUIClient:
        self.login()
        client_uuid = str(uuid.uuid4())
        email = f"tg{tg_user_id}_{client_uuid[:8]}"
        expiry_date = datetime.utcnow() + timedelta(days=days)
        expiry_ms = int(expiry_date.timestamp() * 1000)

        settings = {
            "clients": [
                {
                    "id": client_uuid,
                    "email": email,
                    "enable": True,
                    "tgId": str(tg_user_id),
                    "expiryTime": expiry_ms,
                    "totalGB": 0,
                    "flow": "",
                }
            ]
        }

        payload = {
            "id": self.inbound_id,
            "settings": json.dumps(settings, ensure_ascii=False),
        }

        resp = self.session.post(
            f"{self.base_url}/panel/api/inbounds/addClient",
            data=payload,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success", False):
            raise RuntimeError(f"3x-ui вернул ошибку: {data}")

        return XUIClient(uuid=client_uuid, email=email, expiry_date=expiry_date)
