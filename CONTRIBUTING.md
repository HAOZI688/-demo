# 贡献指南 — manju-demo

> 感谢你参与 manju-demo（爆款猎人演示仓）的开发。
> 本仓采用**功能分支 + Pull Request 流程**，禁止直接推送到 `main`。

---

## 开发流程

1. **从 `main` 拉取最新代码**
   ```bash
   git checkout main
   git pull
   ```

2. **创建功能分支**
   ```bash
   git checkout -b feat/my-feature
   # 或 fix/my-bugfix、docs/my-doc、refactor/my-change
   ```

3. **本地开发**
   ```bash
   source .venv/bin/activate
   bash scripts/dev.sh  # 启动服务，http://localhost:8765
   ```

4. **提交前检查**
   ```bash
   python scripts/check_html_balance.py    # HTML 平衡
   python scripts/extract_studio_js.py | node --check  # JS 语法
   flake8 app/ --max-line-length=120       # Python lint
   pytest tests/ -v                        # 测试全绿
   ```

5. **提交**
   ```bash
   git add .
   git commit -m "feat: 我的新功能"  # 见下方 commit 规范
   git push origin feat/my-feature
   ```

6. **创建 Pull Request**
   - 在 GitHub 上开 PR 到 `main`
   - CI 自动跑：lint → test → HTML 平衡 → JS 语法
   - CI 通过后请一位 reviewer
   - merge 后自动部署 UAT

---

## Commit 规范（Conventional Commits）

```
<type>: <简短描述>

[可选的详细描述]
```

### Type 类型

| type | 语义 | 示例 |
|---|---|---|
| `feat` | 新功能 | `feat: 添加剧本搜索功能` |
| `fix` | 修复 | `fix: 修正 JS 语法错误导致白屏` |
| `docs` | 文档 | `docs: 更新前端接手说明` |
| `style` | 样式 | `style: 调整 Modal 圆角` |
| `refactor` | 重构 | `refactor: 提取 renderCols 为独立函数` |
| `test` | 测试 | `test: 补充 analyse 端点测试` |
| `chore` | 工程化 | `chore: 添加 deploy-uat.yml` |

### 示例

```
feat: 添加剧本搜索功能
- 在 renderProjectsPage 中添加搜索输入框
- 实现 filterProjectCards 客户端过滤
```

```
chore: 配置 GitHub Actions 自动部署
```

---

## 分支命名

| 前缀 | 语义 |
|---|---|
| `feat/` | 新功能 |
| `fix/` | 修复 |
| `docs/` | 文档 |
| `refactor/` | 重构 |
| `chore/` | 工程化 |

---

## 环境要求

- Python 3.11+
- Node.js（用于 studio.html 内联 JS 语法检查）
- FastAPI + uvicorn（pip 安装）

---

## 目录结构快速参考

```
manju-demo/
├── app/
│   ├── main.py         # FastAPI 入口 + 中间件
│   ├── api/routes.py   # 全部 21 个 API 端点
│   ├── database.py     # SQLAlchemy 模型（5 张表）
│   ├── auth.py         # 鉴权
│   └── preset.py       # 预置 JSON 加载
├── data/preset/        # mock 数据 JSON
├── scripts/            # 开发和部署脚本
├── tests/              # pytest
└── .github/workflows/  # CI + 部署
```
