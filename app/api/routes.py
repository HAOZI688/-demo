"""API 路由 — 精简版（第一轮 9 个端点）
端点列表：
- POST /api/login
- GET  /api/login/status
- POST /api/logout
- GET  /api/projects
- POST /api/projects
- GET  /api/scripts
- POST /api/scripts
- GET  /api/scripts/{id}
- POST /api/scripts/{id}/analyze  ⚠️ USE_LLM 安全 fallback mock

第二轮再加：
- /api/scripts/{id}/rewrite
- /api/scripts/{id}/covers/*
- /api/scripts/{id}/export
- /api/analysis-records, /api/exports
- /api/studio/content/*
- /api/tasks/{id}
"""
from __future__ import annotations
import json
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.database import SessionLocal, User, Project, Script, ScriptVersion, AnalysisReport
from app.auth import (
    hash_password, verify_password,
    create_session, destroy_session,
    SESSION_COOKIE,
)
from app.config import settings
from app.preset import load_preset

router = APIRouter()


# ============================================================
# 鉴权
# ============================================================

@router.post("/api/login")
async def login(req: dict, response: Response):
    username = (req.get("username") or "").strip()
    password = req.get("password") or ""
    if not username or not password:
        raise HTTPException(400, detail="请输入用户名和密码")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username, User.is_active == 1).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(401, detail="用户名或密码错误")
        user.last_login = datetime.utcnow()
        db.commit()
        token = create_session(user.id, user.username, user.role)
        response.set_cookie(
            SESSION_COOKIE, token,
            httponly=True, max_age=settings.SESSION_EXPIRE_HOURS * 3600, samesite="lax",
        )
        return {"ok": True, "user": {"id": user.id, "username": user.username, "role": user.role}}
    finally:
        db.close()


@router.get("/api/login/status")
async def login_status(request: Request):
    from app.auth import get_current_user
    user = get_current_user(request)
    if not user:
        return {"logged_in": False}
    return {"logged_in": True, "role": user.get("role", "user"), "username": user.get("username")}


@router.post("/api/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        destroy_session(token)
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


# ============================================================
# 项目
# ============================================================

@router.get("/api/projects")
async def list_projects():
    db = SessionLocal()
    try:
        projects = (
            db.query(Project)
            .filter(Project.is_deleted == 0)
            .order_by(Project.id.desc())
            .all()
        )
        result = []
        for p in projects:
            scripts = (
                db.query(Script)
                .filter(Script.project_id == p.id, Script.is_deleted == 0)
                .all()
            )
            result.append({
                "id": p.id,
                "name": p.name,
                "genre": p.genre,
                "description": p.description,
                "status": p.status,
                "script_count": len(scripts),
                "scripts": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "status": s.status,
                        "current_version": s.current_version,
                    }
                    for s in scripts
                ],
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })
        return result
    finally:
        db.close()


@router.post("/api/projects")
async def create_project(req: dict):
    name = (req.get("name") or "").strip()
    if not name:
        raise HTTPException(400, detail="项目名称不能为空")

    db = SessionLocal()
    try:
        p = Project(
            name=name,
            genre=req.get("genre", ""),
            description=req.get("description", ""),
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return {"ok": True, "id": p.id, "name": p.name}
    finally:
        db.close()


# ============================================================
# 剧本
# ============================================================

@router.get("/api/scripts")
async def list_scripts(project_id: int | None = None):
    db = SessionLocal()
    try:
        query = db.query(Script).filter(Script.is_deleted == 0)
        if project_id:
            query = query.filter(Script.project_id == project_id)
        scripts = query.order_by(Script.id.desc()).all()

        result = []
        for s in scripts:
            report = (
                db.query(AnalysisReport)
                .filter(AnalysisReport.script_id == s.id)
                .order_by(AnalysisReport.id.desc())
                .first()
            )
            result.append({
                "id": s.id,
                "project_id": s.project_id,
                "title": s.title,
                "genre": s.genre,
                "word_count": s.word_count,
                "status": s.status,
                "current_version": s.current_version,
                "tags": json.loads(s.tags_json or "[]"),
                "score": report.overall_score if report else 0,
                "tier": report.prediction_tier if report else "--",
                "probability": report.viral_probability if report else 0,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            })
        return result
    finally:
        db.close()


@router.post("/api/scripts")
async def create_script(req: dict):
    project_id = req.get("project_id")
    title = (req.get("title") or "").strip()
    content = req.get("content") or ""
    if not project_id or not title or not content:
        raise HTTPException(400, detail="缺少项目ID、标题或内容")
    if len(content) < settings.MIN_SCRIPT_CHARS:
        raise HTTPException(400, detail=f"剧本内容至少 {settings.MIN_SCRIPT_CHARS} 字")

    db = SessionLocal()
    try:
        # 校验项目
        proj = db.query(Project).filter(Project.id == project_id, Project.is_deleted == 0).first()
        if not proj:
            raise HTTPException(404, detail="项目不存在")

        s = Script(
            project_id=project_id,
            title=title,
            genre=req.get("genre", ""),
            word_count=len(content),
            status="draft",
            current_version="V1",
            tags_json=json.dumps(req.get("tags", []), ensure_ascii=False),
        )
        db.add(s)
        db.flush()

        sv = ScriptVersion(
            script_id=s.id,
            version="V1",
            content=content,
            change_summary="初始导入",
        )
        db.add(sv)
        db.commit()
        db.refresh(s)
        return {"ok": True, "id": s.id, "title": s.title, "version_id": sv.id}
    finally:
        db.close()


@router.get("/api/scripts/{script_id}")
async def get_script(script_id: int):
    db = SessionLocal()
    try:
        s = db.query(Script).filter(Script.id == script_id, Script.is_deleted == 0).first()
        if not s:
            raise HTTPException(404, detail="剧本不存在")

        versions = (
            db.query(ScriptVersion)
            .filter(ScriptVersion.script_id == script_id)
            .order_by(ScriptVersion.id)
            .all()
        )
        current_version = versions[-1] if versions else None
        report = (
            db.query(AnalysisReport)
            .filter(AnalysisReport.script_id == script_id)
            .order_by(AnalysisReport.id.desc())
            .first()
        )
        return {
            "id": s.id,
            "project_id": s.project_id,
            "title": s.title,
            "genre": s.genre,
            "word_count": s.word_count,
            "status": s.status,
            "current_version": s.current_version,
            "tags": json.loads(s.tags_json or "[]"),
            "versions": [
                {
                    "id": v.id,
                    "version": v.version,
                    "content": (v.content or "")[:500],
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
                for v in versions
            ],
            "current_content": current_version.content if current_version else "",
            "report": {
                "id": report.id,
                "overall_score": report.overall_score,
                "tier": report.prediction_tier,
                "probability": report.viral_probability,
                "has_markdown": bool(report.report_content),
                "dimensions": {
                    "rhythm": report.rhythm_score,
                    "audience": report.audience_score,
                    "production": report.production_score,
                    "character": report.character_score,
                    "social": report.social_score,
                    "spread": report.spread_score,
                },
            } if report else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
    finally:
        db.close()


# ============================================================
# 分析（核心端点）— mock / LLM 双模式
# ============================================================

@router.post("/api/scripts/{script_id}/analyze")
async def analyze_script(script_id: int, req: dict = None):
    """
    第一轮：USE_LLM=0 → 返回 mock JSON
           USE_LLM=1 → 安全 fallback mock（即使 TOKEN 缺失也不报错，第二轮再实现真实 LLM 路径）
    """
    started = time.time()
    req = req or {}

    db = SessionLocal()
    try:
        s = db.query(Script).filter(Script.id == script_id, Script.is_deleted == 0).first()
        if not s:
            raise HTTPException(404, detail="剧本不存在")
        sv = (
            db.query(ScriptVersion)
            .filter(ScriptVersion.script_id == script_id)
            .order_by(ScriptVersion.id.desc())
            .first()
        )
        if not sv:
            raise HTTPException(404, detail="剧本版本不存在")
        title = s.title
        content = sv.content
        genre = s.genre
        s.status = "analyzing"
        db.commit()
    finally:
        db.close()

    # === 分析主体：USE_LLM=1 暂未实现，安全 fallback mock ===
    # 第一轮：根据 PRD 要求，USE_LLM=1 也必须返回 mock，不让服务报错
    try:
        if settings.USE_LLM:
            # 预留：第二轮实现真实 LLM 调用
            # try:
            #     result = await _real_llm_analyze(title, content, genre, script_id)
            # except Exception:
            #     # 真实 LLM 失败时 fallback mock，保证 demo 不阻塞
            #     result = load_preset("analyze_response")
            result = load_preset("analyze_response")
        else:
            result = load_preset("analyze_response")
    except Exception as e:
        # 任何异常 → 兜底 mock
        print(f"[analyze] fallback to mock due to: {e}")
        result = load_preset("analyze_response")

    # 写 AnalysisReport
    dims = result.get("dimensions", {})
    summary = result.get("summary", {})
    markdown_report = result.get("markdown_report", "")
    db = SessionLocal()
    try:
        s = db.query(Script).filter(Script.id == script_id).first()
        s.status = "analyzed"
        report = AnalysisReport(
            script_id=script_id,
            script_title=title,
            script_content=content[:5000],
            overall_score=result.get("overall_score", 0),
            rhythm_score=dims.get("rhythm", {}).get("score", 0),
            audience_score=dims.get("audience", {}).get("score", 0),
            production_score=dims.get("production", {}).get("score", 0),
            character_score=dims.get("character", {}).get("score", 0),
            social_score=dims.get("social", {}).get("score", 0),
            spread_score=dims.get("spread", {}).get("score", 70),
            prediction_tier=result.get("tier", "B"),
            viral_probability=result.get("viral_probability", 0),
            genre=genre,
            duration=time.time() - started,
            model_version=f"mock-v{settings.APP_VERSION}" + ("-fallback" if settings.USE_LLM else ""),
            report_content=markdown_report,
            summary_json=json.dumps(summary, ensure_ascii=False),
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        report_id = report.id
    finally:
        db.close()

    latency = time.time() - started
    return {
        "ok": True,
        "report_id": report_id,
        "overall_score": result.get("overall_score", 0),
        "tier": result.get("tier", "B"),
        "viral_probability": result.get("viral_probability", 0),
        "dimensions": {
            k: {"score": v.get("score", 0), "max": v.get("max_score", 20)}
            for k, v in dims.items()
        },
        "latency": latency,
    }


# ============================================================
# 改写 / 重评 / 导出 / 封面（第二轮：mock 模式）
# ============================================================


@router.get("/api/scripts/{script_id}/rewrite-status")
async def rewrite_status(script_id: int):
    """返回改写进度状态—指望 basic analyze 后有 mock rewrite_status.json"""
    result = load_preset("rewrite_status")
    if result:
        if script_id:
            result["script_id"] = script_id
        return result
    return {"has_rewrite": False, "script_id": script_id, "status": "no_rewrite",
            "changes": [], "accepted": 0, "total": 0}


@router.post("/api/scripts/{script_id}/rewrite")
async def rewrite_script(script_id: int, req: dict = None):
    """分析 → 改写：返回 mock V2 结构"""
    req = req or {}
    result = load_preset("rewrite_response")
    if not result:
        result = {
            "status": "completed", "script_id": script_id, "rewrite_version": "V2",
            "new_version": "V2", "rewrite_version_id": 100 + script_id,
            "latest_version_id": 100 + script_id, "version_id": 100 + script_id,
            "chapters": [{"title": "第 1 章", "content": "改写后内容"}],
            "changes": [{"id": 1, "type": "add", "location": "第 1 章",
                        "content": "加入开场悬念", "status": "accepted"}],
            "score_lift": 8,
        }
    result["script_id"] = script_id
    result["ok"] = True
    result["new_version"] = result.get("new_version", "V2")
    result["rewrite_version_id"] = result.get("rewrite_version_id", 100 + script_id)
    return result


@router.post("/api/scripts/{script_id}/reanalyze")
async def reanalyze_script(script_id: int, req: dict = None):
    """改写后重评：返回分析 mock（同 analyze 端点）"""
    req = req or {}
    result = load_preset("analyze_response")
    if not result:
        result = {"overall_score": 85, "tier": "S", "viral_probability": 82,
                  "dimensions": {}}
    result["ok"] = True
    result["report_id"] = 100 + script_id
    result["new_score"] = result.get("overall_score", 85)
    result["new_tier"] = result.get("tier", "S")
    result["score_delta"] = result.get("overall_score", 85) - 78
    return result


@router.post("/api/scripts/{script_id}/export")
async def export_script(script_id: int, req: dict = None):
    """结果导出：返回 mock 文件清单"""
    req = req or {}
    result = load_preset("export_response")
    if not result:
        result = {"formats": {"json": "export.json", "md": "export.md", "zip": "export.zip",
                              "docx": "export.docx", "pdf": "export.pdf"},
                  "total_size": 1084416, "export_id": 100 + script_id}
    result["ok"] = True
    result["export_id"] = result.get("export_id", 100 + script_id)
    result["formats"] = result.get("formats", {"json": "export.json", "md": "export.md"})
    return result


@router.post("/api/scripts/{script_id}/covers/generate")
async def generate_covers(script_id: int, req: dict = None):
    """生成 3 张 Mock 封面（prlacedocio placeholder）"""
    result = {
        "ok": True,
        "covers": [
            {"id": script_id * 10 + 1, "script_id": script_id,
             "image_url": f"https://placehold.co/600x800/1a1a2e/e94560?text=Cover+{script_id}+1",
             "prompt": "漫剧封面 - 都市风格", "style": "都市写实",
             "source_type": "mock_generated", "is_selected": False},
            {"id": script_id * 10 + 2, "script_id": script_id,
             "image_url": f"https://placehold.co/600x800/2d1b69/a855f7?text=Cover+{script_id}+2",
             "prompt": "漫剧封面 - 水墨国风", "style": "水墨国风",
             "source_type": "mock_generated", "is_selected": False},
            {"id": script_id * 10 + 3, "script_id": script_id,
             "image_url": f"https://placehold.co/600x800/0f3460/22d3ee?text=Cover+{script_id}+3",
             "prompt": "漫剧封面 - 赛博朋克", "style": "赛博朋克",
             "source_type": "mock_generated", "is_selected": False},
        ],
        "source_type": "mock_generated",
        "warning": "Mock 生图，非真实 AI 生成",
    }
    return result


@router.post("/api/scripts/{script_id}/covers/{cover_id}/select")
async def select_cover(script_id: int, cover_id: int):
    """选择封面（no-op）"""
    return {"ok": True, "cover_id": cover_id, "is_selected": True}


# ============================================================
# 数据页支撑（Part 3：最小可展示）
# ============================================================


@router.get("/api/analysis-records")
async def analysis_records(page: int = 1, page_size: int = 50):
    """分析记录列表 — 从 preset/history_list.json 加载 + 补充当前 SCRIPTS 中的真实分析"""
    from app.database import SessionLocal, AnalysisReport as Report
    result = load_preset("history_list") or {"items": []}
    items = result.get("items", [])
    # 合并真实数据库中的分析记录
    db = SessionLocal()
    try:
        reports = db.query(Report).order_by(Report.id.desc()).limit(page_size).all()
        for r in reports:
            if not any(item.get("id") == r.id for item in items):
                items.append({
                    "id": r.id,
                    "script_id": r.script_id,
                    "script_title": r.script_title,
                    "overall_score": r.overall_score,
                    "prediction_tier": r.prediction_tier,
                    "score_delta": None,
                    "rule_version": r.rule_version,
                    "model_version": r.model_version,
                    "duration": r.duration,
                    "viral_probability": r.viral_probability,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "parent_report_id": r.parent_report_id if hasattr(r, "parent_report_id") else None,
                })
    finally:
        db.close()
    return {"items": items, "total": len(items), "page": page, "page_size": page_size}


@router.get("/api/analysis-records/{record_id}")
async def analysis_record_detail(record_id: int):
    """单条分析记录详情"""
    from app.database import SessionLocal, AnalysisReport as Report
    db = SessionLocal()
    try:
        r = db.query(Report).filter(Report.id == record_id).first()
        if not r:
            return load_preset("history_list", {}).get("items", [{}])[0] if load_preset("history_list") else {"ok": False}
        return {
            "id": r.id,
            "script_id": r.script_id,
            "script_title": r.script_title,
            "script_snapshot": (r.script_content or "")[:500],
            "script_version": "V1",
            "project_id": None,
            "overall_score": r.overall_score,
            "prediction_tier": r.prediction_tier,
            "viral_probability": r.viral_probability,
            "rhythm_score": r.rhythm_score,
            "audience_score": r.audience_score,
            "production_score": r.production_score,
            "character_score": r.character_score,
            "social_score": r.social_score,
            "spread_score": r.spread_score,
            "rule_version": r.rule_version,
            "model_version": r.model_version,
            "duration": r.duration,
            "score_delta": None,
            "parent_report_id": None,
            "dimension_deltas": {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "markdown_report": r.report_content or "",
            "summary": json.loads(r.summary_json or "{}"),
            "has_markdown": bool(r.report_content),
        }
    finally:
        db.close()


@router.get("/api/exports")
async def exports_list(page: int = 1, page_size: int = 50):
    """导出记录列表 — 从 preset/exports_list.json 读取"""
    result = load_preset("exports_list") or {"items": []}
    items = result.get("items", [])
    return {"items": items, "total": len(items), "page": page, "page_size": page_size}


@router.get("/api/exports/{export_id}")
async def export_detail(export_id: int):
    """单条导出记录详情"""
    result = load_preset("exports_list") or {"items": []}
    for item in result.get("items", []):
        if item.get("id") == export_id:
            return item
    return {"ok": False, "detail": "记录不存在"}


@router.get("/api/market-data")
async def market_data():
    """爆款库（最低 mock）：viral-library 页面依赖 /api/market-data 做渲染"""
    return {"items": []}


# ============================================================
#  studio/content 数据页 — 仅 fallback，实际页面由其 inline JS 函数渲染
# ============================================================


@router.get("/api/studio/content/{page}")
async def studio_content(page: str):
    """返回内嵌 SPA 数据页的最小 HTML 片段。
    实际大多数页面由 studio.html 的 inline JS 函数直接渲染（renderProjectsPage / loadAnalysisRecords 等），
    此端点为备用 fallback。如果某页没有专门的 inline 函数，则由这里返回最小占位。
    """
    presets = {
        "projects": """
<div class="page-content" style="padding:20px;max-width:1200px;margin:0 auto">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
    <div><h2 style="font-size:18px;font-weight:700">📁 项目中心</h2><p style="font-size:11px;color:#6b7280">管理创作项目</p></div>
    <div style="display:flex;gap:8px">
      <button class="b bp" onclick="openNewProjectModal()">+ 新建项目</button>
    </div>
  </div>
  <div id="projects-body"><p style="color:#9ca3af;text-align:center;padding:40px">点击「+ 新建项目」开始</p></div>
</div>""",
        "history": "<div class='page-content'><h2>分析记录</h2><p style='padding:30px;text-align:center;color:#9ca3af'>暂无分析记录</p></div>",
        "exports": "<div class='page-content'><h2>导出记录</h2><p style='padding:30px;text-align:center;color:#9ca3af'>暂无导出记录</p></div>",
        "materials": "<div class='page-content'><h2>📚 素材库</h2><p style='padding:30px;text-align:center;color:#9ca3af'>暂无素材。完成剧本分析并导出后自动入库。</p></div>",
        "viral-library": "<div class='page-content'><h2>🔥 爆款库</h2><p style='padding:30px;text-align:center;color:#9ca3af'>暂无数据</p></div>",
        "scoring-rules": "<div class='page-content'><h2>🎯 评分规则</h2><p style='padding:30px;text-align:center;color:#9ca3af'>Demo 中只读展示</p></div>",
        "prompts": "<div class='page-content'><h2>💬 Prompt 管理</h2><p style='padding:30px;text-align:center;color:#9ca3af'>Demo 中只读展示</p></div>",
        "agent-flow": "<div class='page-content'><h2>🔄 Agent 流程</h2><p style='padding:30px;text-align:center;color:#9ca3af'>Demo 中只读展示</p></div>",
        "users": "<div class='page-content'><h2>👥 用户管理</h2><p style='padding:30px;text-align:center;color:#9ca3af'>Demo 中只读展示</p></div>",
        "settings": "<div class='page-content'><h2>⚙️ 设置</h2><p style='padding:30px;text-align:center;color:#9ca3af'>Demo 中只读展示</p></div>",
        "crawler": "<div class='page-content'><h2>🕷️ 数据采集</h2><p style='padding:30px;text-align:center;color:#9ca3af'>Demo 未接入</p></div>",
    }
    return {"html": presets.get(page, "<div class='page-content'><h2>🚧 页面开发中</h2></div>")}
