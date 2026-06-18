# 第三轮工程化实施清单

> 只做 branch protection + GitHub Actions 部署 + systemd + 贡献指南，**不改业务主链路**。

---

## 实施内容

| 编号 | 文件 | 说明 | 优先级 |
|---|---|---|---|
| 3-1 | GitHub 仓库设置 | Branch protection rules（main 分支） | 高 |
| 3-2 | `.github/workflows/deploy-uat.yml` | 自动部署到 UAT | 高 |
| 3-3 | `.github/workflows/rollback.yml` | 手动回滚 workflow | 中 |
| 3-4 | `systemd/manju-demo.service` | uvicorn 的 systemd unit | 高 |
| 3-5 | `scripts/deploy-uat.sh` | UAT 部署脚本（Actions 调用） | 高 |
| 3-6 | `CONTRIBUTING.md` | PR 流程 + commit 规范 | 中 |
| — | **`docs/phase-3-checklist.md`** | **本文档** | — |

---

## 详细要求

### 3-1 Branch Protection（GitHub 仓库设置）

在 GitHub → Settings → Branches → Add rule：

| 规则 | 值 |
|---|---|
| Branch name pattern | `main` |
| Require pull request reviews before merging | ✅（1 个） |
| Require status checks to pass | ✅ `CI / test` |
| Require branches to be up to date | ✅ |
| Do not allow bypassing the above settings | ✅ |
| Allow force pushes | ❌ |
| Allow deletions | ❌ |

### 3-2 deploy-uat.yml

- 触发：push 到 `main`（CI 通过后）+ `workflow_dispatch`
- 配置参数：`use_llm`（boolean，默认 false）
- SSH 到 UAT 服务器后执行：
  1. `cd /srv/manju-demo`
  2. 备份当前 `data/manju.db`
  3. `git fetch && git reset --hard origin/main`
  4. `source .venv/bin/activate && pip install -r requirements.txt`
  5. **重建** `.env.runtime`（不追加，见 PRD §8.5.1）
  6. `sudo systemctl restart manju-demo`
  7. `sleep 3 && curl -f http://localhost:8765/api/health`
- 凭据：GitHub Secrets `UAT_HOST` / `UAT_USER` / `UAT_SSH_KEY`

### 3-3 rollback.yml

- 触发：`workflow_dispatch`
- 参数：`commit_sha`（必需）
- SSH 后：`git reset --hard <sha>` → pip install → restart → health check

### 3-4 systemd/manju-demo.service

- `EnvironmentFile=-/srv/manju-demo/.env.runtime`（`-` 前缀允许缺失）
- `Restart=always` / `RestartSec=5`
- `User=manju` / `WorkingDirectory=/srv/manju-demo`

### 3-5 scripts/deploy-uat.sh

- 由 deploy-uat.yml 在 SSH 远程执行
- 等价于 deploy-uat.yml 的 `script:` 内容（可被 Actions 直接调用）

### 3-6 CONTRIBUTING.md

- PR 流程
- commit 规范（conventional commits）
- 开发环境要求

---

## 不在此轮的范围

- ❌ `Dockerfile` / `docker-compose.yml`
- ❌ `.vscode/` 配置
- ❌ `docs/` 全家桶（仅 2 份新文档）
- ❌ Dependabot / Issue 模板 / PR 模板 / CODEOWNERS
- ❌ 任何业务 API、前端页面、预置数据修改
- ❌ `README.md` 更新
- ❌ UAT 服务器实际配置（需仓维护者手动完成）

---

## 新增文件清单

```
manju-demo/
├── .github/workflows/
│   ├── deploy-uat.yml       # 新增
│   └── rollback.yml         # 新增
├── systemd/
│   └── manju-demo.service   # 新增
├── scripts/
│   └── deploy-uat.sh        # 新增
├── CONTRIBUTING.md          # 新增
└── docs/
    ├── frontend-handover.md # 已创建
    └── phase-3-checklist.md # 本文档
```
