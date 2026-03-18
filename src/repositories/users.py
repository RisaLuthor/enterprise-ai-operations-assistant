from __future__ import annotations

from typing import Optional

from src.db.database import get_connection


def get_user_by_email(email: str) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, email, square_customer_id, square_subscription_id, plan, is_active, created_at
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, email, square_customer_id, square_subscription_id, plan, is_active, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_square_customer_id(square_customer_id: str) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, email, square_customer_id, square_subscription_id, plan, is_active, created_at
            FROM users
            WHERE square_customer_id = ?
            """,
            (square_customer_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_user(email: str, plan: str, square_customer_id: str | None = None) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO users (email, square_customer_id, square_subscription_id, plan, is_active)
            VALUES (?, ?, NULL, ?, 1)
            """,
            (email, square_customer_id, plan),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def update_user_plan(user_id: int, plan: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET plan = ? WHERE id = ?",
            (plan, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_user_square_subscription(user_id: int, square_subscription_id: str | None) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET square_subscription_id = ? WHERE id = ?",
            (square_subscription_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_user_active(user_id: int, is_active: bool) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, user_id),
        )
        conn.commit()
    finally:
        conn.close()