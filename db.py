from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Order:
    id: int
    user_id: int
    username: str
    plan_code: str
    amount_rub: int
    phone: str
    status: str
    receipt_file_id: Optional[str]
    receipt_note: Optional[str]
    created_at: str


class Database:
    def __init__(self, path: str):
        self.path = path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    plan_code TEXT NOT NULL,
                    amount_rub INTEGER NOT NULL,
                    phone TEXT NOT NULL,
                    status TEXT NOT NULL,
                    receipt_file_id TEXT,
                    receipt_note TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    order_id INTEGER NOT NULL,
                    plan_code TEXT NOT NULL,
                    uuid TEXT NOT NULL,
                    email TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(order_id) REFERENCES orders(id)
                )
                """
            )

    def create_order(self, user_id: int, username: str, plan_code: str, amount_rub: int, phone: str) -> int:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO orders (user_id, username, plan_code, amount_rub, phone, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'pending_receipt', ?, ?)
                """,
                (user_id, username, plan_code, amount_rub, phone, now, now),
            )
            return int(cur.lastrowid)

    def set_receipt(self, order_id: int, file_id: Optional[str], note: Optional[str]) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE orders
                SET receipt_file_id = ?, receipt_note = ?, status = 'pending_admin', updated_at = ?
                WHERE id = ?
                """,
                (file_id, note, now, order_id),
            )

    def set_order_status(self, order_id: int, status: str) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, order_id),
            )

    def get_order(self, order_id: int) -> Optional[Order]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not row:
                return None
            return Order(**dict(row))

    def add_subscription(self, user_id: int, order_id: int, plan_code: str, uuid: str, email: str, expires_at: str) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO subscriptions (user_id, order_id, plan_code, uuid, email, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, order_id, plan_code, uuid, email, expires_at, now),
            )
