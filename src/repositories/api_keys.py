from __future__ import annotations

from typing import Optional

from src.db.database import get_connection


def create_api_key(user_id: int, api_key: str) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO api_keys (user_id, api_key, is_active)
            VALUES (?, ?, 1)
            """,
            (user_id, api_key),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_api_key_record(api_key: str) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                ak.id,
                ak.user_id,
                ak.api_key,
                ak.is_active,
                u.email,
                u.plan,
                u.is_active AS user_is_active
            FROM api_keys ak
            JOIN users u ON u.id = ak.user_id
            WHERE ak.api_key = ?
            """,
            (api_key,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_api_key_for_user(user_id: int) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, user_id, api_key, is_active, created_at
            FROM api_keys
            WHERE user_id = ? AND is_active = 1
            ORDER BY id ASC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()