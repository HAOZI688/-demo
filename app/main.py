"""FastAPI 入口 — 精简版（第一轮）"""
from __future__ import annotations
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import init_db, _seed_defaults, SessionLocal
from app.config import settings
from app.api.routes import router

WEB_DIR = Path(__file__).parent / "web"
STATIC_DIR = WEB_DIR / "static"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _seed_defaults()
    print(f"[App] 启动完成 (USE_LLM={settings.USE_LLM})")
    yield


app = FastAPI(title="爆款猎人 — Demo", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 鉴权中间件 =====
PUBLIC_PATHS = ["/login", "/static", "/favicon.ico", "/api/login", "/api/login/status", "/api/health", "/api/version"]


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    # 公开路径放行
    if any(path.startswith(p) for p in PUBLIC_PATHS):
        return await call_next(request)
    # API 401
    if path.startswith("/api/"):
        from app.auth import get_current_user
        if not get_current_user(request):
            return JSONResponse(status_code=401, content={"detail": "请先登录"})
    # 页面重定向
    else:
        from app.auth import get_current_user
        if not get_current_user(request):
            return RedirectResponse(url="/login", status_code=302)
    return await call_next(request)


# ===== 页面路由 =====

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """login.html is static HTML + inline JS, no Jinja2 context"""
    p = WEB_DIR / "templates" / "login.html"
    return HTMLResponse(p.read_text(encoding="utf-8"))


@app.get("/", response_class=HTMLResponse)
async def root_redirect():
    """根路径：已登录跳 /workspace，未登录跳 /login（由中间件处理）"""
    return RedirectResponse(url="/workspace", status_code=302)


@app.get("/workspace", response_class=HTMLResponse)
async def workspace_page():
    """workspace/studio.html is static HTML + inline JS, no Jinja2 context"""
    p = WEB_DIR / "templates" / "workspace" / "studio.html"
    return HTMLResponse(p.read_text(encoding="utf-8"))


# ===== 监控/版本端点 =====

@app.get("/api/health")
async def health(db: Session = Depends(get_db)):
    """健康检查：本地启动验证 + CI 冒烟测试 + UAT 部署后健康检查。
    必须稳定、轻量、无副作用，使用 SQLAlchemy 2.x 兼容写法。
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "db": "ok",
            "version": settings.APP_VERSION,
            "is_llm": settings.USE_LLM,
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "db": "error", "detail": str(e)},
        )


@app.get("/api/version")
async def version():
    """版本信息。第一轮用占位，第二轮 CI 注入真实 commit/build_time。"""
    return {
        "version": settings.APP_VERSION,
        "commit": os.environ.get("GIT_COMMIT", settings.PLACEHOLDER_COMMIT),
        "build_time": os.environ.get("BUILD_TIME", settings.PLACEHOLDER_BUILD_TIME),
        "is_llm_enabled": settings.USE_LLM,
    }


# ===== 静态文件 =====
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ===== 业务 API =====
app.include_router(router)
