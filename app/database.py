"""数据库模型 — 精简版（第一轮 5 张表）
原仓库 32 张表 → 第一轮只保留主链路必需的 5 张：
- User（鉴权）
- Project（项目）
- Script（剧本）
- ScriptVersion（剧本版本）
- AnalysisReport（分析报告）
其余 3 张（DimensionScore / CoverAsset / BenchmarkSample）第二轮再加。
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), default="user")  # admin / user
    is_active = Column(Integer, default=1)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    genre = Column(String(100), default="")
    description = Column(Text, default="")
    status = Column(String(20), default="active")
    is_deleted = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Script(Base):
    __tablename__ = "scripts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    genre = Column(String(100), default="")
    word_count = Column(Integer, default=0)
    status = Column(String(20), default="draft")  # draft / analyzing / analyzed / failed
    current_version = Column(String(20), default="V1")
    tags_json = Column(Text, default="[]")
    is_deleted = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScriptVersion(Base):
    __tablename__ = "script_versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    script_id = Column(Integer, index=True, nullable=False)
    version = Column(String(20), nullable=False)  # V1, V2...
    content = Column(Text, default="")
    change_summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    script_id = Column(Integer, index=True, nullable=True)
    script_title = Column(String(200), default="")
    script_content = Column(Text, default="")

    # 6 维评分
    overall_score = Column(Float, default=0)
    rhythm_score = Column(Float, default=0)        # Hook 吸引力
    audience_score = Column(Float, default=0)      # 情绪操控
    production_score = Column(Float, default=0)    # 爽点与反转
    character_score = Column(Float, default=0)     # 角色商业价值
    social_score = Column(Float, default=0)        # 付费卡点
    spread_score = Column(Float, default=70)       # 平台传播

    prediction_tier = Column(String(10), default="B")
    genre = Column(String(100), default="")
    viral_probability = Column(Float, default=0)
    report_content = Column(Text, default="")
    features_json = Column(Text, default="{}")
    rule_evidence_json = Column(Text, default="{}")
    summary_json = Column(Text, default="{}")
    duration = Column(Float, default=0)

    # 版本溯源
    rule_version = Column(String(50), default="v1.0.0")
    prompt_version = Column(String(50), default="v1.0.0")
    model_version = Column(String(100), default="mock-v0.1.0")
    reference_cases = Column(Text, default="[]")

    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """创建所有表（仅当数据库不存在时）"""
    Base.metadata.create_all(bind=engine)


def _seed_defaults():
    """种子数据：2 个用户（admin / user）。项目/剧本第一轮不预置，由 UI 创建。"""
    from app.auth import hash_password

    db = SessionLocal()
    try:
        if not db.query(User).first():
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
                is_active=1,
            )
            db.add(admin)
            print("[Seed] Created admin (admin / admin123)")

        if not db.query(User).filter(User.username == "user").first():
            demo = User(
                username="user",
                password_hash=hash_password("user123"),
                role="user",
                is_active=1,
            )
            db.add(demo)
            print("[Seed] Created user (user / user123)")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Seed] Error: {e}")
    finally:
        db.close()
