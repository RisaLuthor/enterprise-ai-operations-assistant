from __future__ import annotations

from src.db.database import get_connection


def record_usage_event(user_id: int, endpoint: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO usage_events (user_id, endpoint, request_count)
            VALUES (?, ?, 1)
            """,
            (user_id, endpoint),
        )
        conn.commit()
    finally:
        conn.close()


def get_monthly_usage_count(user_id: int) -> int:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(request_count), 0) AS total
            FROM usage_events
            WHERE user_id = ?
              AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
            """,
            (user_id,),
        ).fetchone()
        return int(row["total"]) if row else 0
    finally:
        conn.close()