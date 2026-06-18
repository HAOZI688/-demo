# 前端接手说明 — 爆款猎人 Demo

> 面向**前端开发同事**，说明当前 demo 的实现范围、数据策略、启动方式和修改入口。
> 仓库：`https://github.com/HAOZI688/-demo.git`
> 启动后访问 `http://localhost:8765`

---

## 快速启动

```bash
git clone https://github.com/HAOZI688/-demo.git
cd -demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/dev.sh
# → http://localhost:8765/login
```

## 测试账号

| 用户名 | 密码 | 角色 |
|---|---|---|
| `admin` | `admin123` | 管理员（导航完整） |
| `user` | `user123` | 普通用户（仅创作中心） |

---

## 页面清单

| 路由 | 模板 | 状态 |
|---|---|---|
| `/login` | `login.html`（139 行纯静态） | ✅ |
| `/workspace` | `workspace/studio.html`（5000+ 行 SPA） | ✅ 核心页面 |

左侧导航 11 项中实际展示 6 项，管理员后台 5 项已隐藏：

| 导航项 | 渲染函数 | 数据来源 | 状态 |
|---|---|---|---|
| 📝 工作台 | `showWorkspace()` | 静态 | ✅ |
| 📁 项目 | `renderProjectsPage()` | `GET /api/projects` | ✅ |
| 📋 记录 | `loadAnalysisRecords()` | `GET /api/analysis-records` | ✅ |
| 📤 导出 | `loadExportRecords()` | `GET /api/exports` | ✅ |
| 📚 素材 | `renderMaterialsPage()` | 本地 SCRIPTS | ✅ |
| 🔥 爆款库 | `renderViralLibraryPage()` | `GET /api/market-data` + 本地 | ✅ |
| 🕷️ 采集 / 🎯 规则 / 💬 Prompt / 🔄 流程 / 👥 用户 | （管理员，已隐藏） | — | ❌ 未接入 |

---

## 5 阶段工作流

| 阶段 | 触发 | API | 数据来源 | 状态 |
|---|---|---|---|---|
| ① 原文 | 导入剧本 | `POST /api/scripts` | SQLite | ✅ |
| ② 分析 | 「分析」按钮 | `POST /api/scripts/{id}/analyze` | `preset/analyze_response.json` | ✅ |
| ③ 改写 V2 | 分析 Modal「进入改写」 | `POST /api/scripts/{id}/rewrite` | `preset/rewrite_response.json` | ✅ |
| ④ 封面 | 改写 Modal「生成封面」 | `POST /api/scripts/{id}/covers/generate` | 内联 mock（placehold.co） | ✅ |
| ⑤ 导出 | 时间轴「结果导出」 | `POST /api/scripts/{id}/export` | `preset/export_response.json` | ✅ |

---

## Mock 边界

### 真实写入 SQLite（不丢失）

- 用户（seed 创建）
- 项目（UI 新建）
- 剧本 + 剧本版本（UI 导入）
- 分析报告（点击分析后写入）

### 预置 JSON（修改即生效，`data/preset/`）

| 文件 | 影响的内容 |
|---|---|
| `analyze_response.json` | 分析结果（6 维评分 / 问题 / 建议 / 证据） |
| `rewrite_response.json` | 改写 V2 方案（章节 / 修改列表） |
| `rewrite_status.json` | 改写进度状态（前端轮询） |
| `export_response.json` | 导出文件清单 |
| `projects_list.json` | 项目页预置数据 |
| `history_list.json` | 记录页预置数据 |
| `exports_list.json` | 导出页预置数据 |
| `viral_library_list.json` | 爆款库预置数据 |

### 预置 JSON 更新方式

```bash
vim data/preset/analyze_response.json   # 改字段
git commit -m "feat: update analyze mock"
git push
```

---

## 建议修改入口

### 前端（主要集中在 studio.html 的 5000+ 行内联 JS）

| 函数名 | 行号 | 作用 |
|---|---|---|
| `navTo(page)` | 4332 | SPA 路由器，控制导航切换 |
| `showHomeView()` | 5078 | 欢迎页显示 |
| `showWorkspace()` | 5092 | 工作台显示 |
| `openNewProjectModal()` | 2917 | 新建项目弹层 |
| `runAnalyze(scriptId)` | 2026 | 分析流程 |
| `runRewrite(scriptId)` | 2112 | 改写 V2 流程 |
| `runGenerateCovers(scriptId)` | 2455 | 封面生成流程 |
| `runExport(scriptId)` | 2402 | 导出流程 |

### 后端

| 文件 | 说明 |
|---|---|
| `app/api/routes.py`（~500 行） | 全部 21 个 API 端点 |
| `app/database.py`（~200 行） | SQLAlchemy 模型（5 张表） |
| `app/main.py`（~135 行） | FastAPI 入口 + 鉴权中间件 |

---

## 本地验证

```bash
python -c "import app.main"                    # import 校验
python scripts/extract_studio_js.py | node --check  # JS 语法校验
python scripts/check_html_balance.py            # HTML 平衡校验
pytest tests/ -v                                # 期望 9 passed
bash scripts/dev.sh                             # 启动
```

---

## 已知限制

- **LLM**：`USE_LLM=1` 暂未实现，设了也安全 fallback 到 mock
- **管理员后台**：6 个页面已隐藏
- **封面图片**：使用 `placehold.co` 占位图
- **改写保存**：`/api/scripts/{id}/rewrite-blocks/save` 和 `/rewrite/save-edits` 暂未实现（不影响主链路闭环）
- **项目搜索**：`filterProjectCards()` 前端搜索功能只做客户端过滤
