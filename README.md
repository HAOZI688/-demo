# 爆款猎人 Demo（manju-demo）

> 漫剧 AI 分析平台的最小可运行展示仓。
> 本仓采用单一发布主线：**功能分支开发 → Pull Request 合并 → `main` 自动部署 UAT**。
> 默认运行在 mock 模式，**不依赖任何外部 LLM 凭据**。

---

## 快速启动

```bash
# 1. 克隆
git clone https://github.com/your-org/manju-demo.git
cd manju-demo

# 2. 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 装依赖
pip install -r requirements.txt

# 4. （可选）复制环境变量模板
cp .env.example .env

# 5. 启动
bash scripts/dev.sh
# 或直接：
# uvicorn app.main:app --reload --port 8765
```

打开浏览器：`http://localhost:8765/login`

## 演示账号

| 账号 | 密码 | 角色 |
|---|---|---|
| `admin` | `admin123` | 管理员 |
| `user` | `user123` | 普通用户 |

## 验证清单

启动后逐项检查：

- [ ] `/login` 返回 200
- [ ] admin/admin123 登录成功，跳转 `/workspace`
- [ ] 看到欢迎页：「爆款猎人」+ AI 输入框 + 4 卡片
- [ ] 点「新建项目」可创建
- [ ] 顶栏「📤 导入剧本」可创建剧本
- [ ] 剧本卡点「分析」→ 弹出分析详情（6 维评分）
- [ ] `/api/health` 返回 200
- [ ] `/api/version` 返回 200
- [ ] 退出登录 → 跳回 `/login`

## 模式说明

| 模式 | 触发 | 行为 |
|---|---|---|
| **mock（默认）** | `USE_LLM=0` 或环境变量未设 | 分析/改写全部返回预置 JSON，零外部请求 |
| **LLM** | `USE_LLM=1` + 配置 `TOKEN_*` | **当前第一轮**：USE_LLM=1 将安全 fallback 到 mock，不会报错；第二轮再实现真实 LLM 路径 |

## 目录结构

```
manju-demo/
├── app/
│   ├── main.py              # FastAPI 入口 + 中间件 + /api/health + /api/version
│   ├── config.py            # 配置
│   ├── database.py          # SQLAlchemy 5 张表 + 种子
│   ├── auth.py              # 鉴权
│   ├── preset.py            # 预置 JSON 加载
│   ├── api/routes.py        # 10 个端点
│   ├── web/
│   │   ├── templates/       # 登录页 + 工作台 SPA
│   │   └── static/          # CSS / JS
├── data/preset/             # mock 响应
├── scripts/dev.sh           # 启动脚本
├── tests/test_smoke.py      # 冒烟测试
├── .github/workflows/ci.yml # CI
└── requirements*.txt
```

## CI

GitHub Actions CI 跑：
- Python lint（flake8）
- 格式检查（black）
- `python -c "import app.main"`
- HTML 平衡检查
- studio.html 内联 JS 语法检查
- pytest 冒烟测试
- 启动后 `/login` 和 `/api/health` HTTP 200

## 发布流程

1. 从 `main` 拉功能分支：`git checkout -b feat/xxx`
2. 改完后：`git commit -m "feat: ..."` + `git push`
3. GitHub 上开 PR
4. CI 通过 → review → merge 到 `main`
5. `main` 收到新提交后自动触发 UAT 部署（第二轮再加）

## 第二轮待补

- 完整 `deploy-uat.yml` / `rollback.yml` / `systemd` / `Dockerfile`
- `.vscode/` 配置
- `docs/` 文档
- Dependabot / Issue 模板 / PR 模板 / CODEOWNERS
- 5 个内嵌数据页（projects / history / exports / materials / viral-library）
- 改写 V2 / 封面 / 导出 / 端到端工作流
- DimensionScore / CoverAsset / BenchmarkSample 3 张表
- USE_LLM=1 真实 LLM 路径

## License

Apache-2.0
