"""鉴权 — 内存 session + Cookie"""
from __future__ import annotations
import hashlib
import secrets
import time
from fastapi import Request, HTTPException

SESSION_COOKIE = "manju_session"

# 内存 session 存储
_sessions: dict[str, dict] = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == password_hash


def create_session(user_id: int, username: str, role: str) -> str:
    from app.config import settings
    token = secrets.token_hex(32)
    _sessions[token] = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "expires": time.time() + settings.SESSION_EXPIRE_HOURS * 3600,
    }
    return token


def destroy_session(token: str):
    _sessions.pop(token, None)


def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token or token not in _sessions:
        return None
    session = _sessions[token]
    if time.time() > session["expires"]:
        del _sessions[token]
        return None
    return session


def require_auth(request: Request) -> dict:
    """依赖注入 — 未登录抛出 401"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, detail="请先登录")
    return user
