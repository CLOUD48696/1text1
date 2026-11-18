# AI Panel Studio

AI 圆桌讨论本地 Web App 面试项目。输入话题、确认 AI 生成的主持人与专家阵容，观看由当前讨论内容驱动的圆桌讨论，并实时查看共识与分歧。

## 当前状态

2026-11-17：已实现可运行 MVP，包含嘉宾生成与确认、自主意图调度、主持人、实时状态与发言、共识/分歧证据、自然语言总结、多讨论隔离、SSE 补发与刷新恢复。默认 **Demo 演示模式**，明确使用预设内容；live 模式只接 DeepSeek，不会在失败时偷偷降级成演示内容。

真实 DeepSeek 请求尚未验收：需在本地 `.env` 填入 API Key 后运行。后端模型适配器已经通过模拟 HTTP 响应测试，不能据此宣称真实服务已通过。

仓库：[CLOUD48696/1text1](https://github.com/CLOUD48696/1text1)，分支 `main`。

## 开发入口

- [项目协作约定](AGENTS.md)
- [产品方案与验收标准](docs/product.md)
- [技术方案、数据模型与 API 契约](docs/architecture.md)
- [24 小时实施计划](docs/implementation-plan.md)
- [当前进度与续接说明](docs/handoff.md)
- [真实 Prompt 与过程记录](docs/prompt-log.md)

## 实际技术栈

- 前端：React 19、TypeScript、Vite 7、Lucide、Zustand、原生 CSS。页面拆为 Home / Roster / Studio / Avatar 组件；没有引入原规划中的 Tailwind/shadcn，减少小型 MVP 的组件与样式工具依赖。
- 后端：FastAPI、Pydantic、SQLAlchemy、SQLite；普通 HTTP API + 持久化 SSE 事件；独立 DeepSeek 适配层与轻量讨论状态机。
- 测试：pytest（核心/集成/供应商适配）、Playwright（桌面与手机视口，真实后端 + DemoLLM）。
- 依赖锁定：`backend/requirements.lock.txt`、`frontend/package-lock.json`。已验证 Windows、Python 3.14.7、Node.js 22.19.0、npm 10.9.3。

## 快速启动（Windows PowerShell）

在项目根目录执行：

Windows 上重装依赖前先关闭正在运行的 Vite 开发服务，避免 esbuild.exe 被占用。

```powershell
./scripts/setup.ps1
# 如果 Python 不在 PATH：./scripts/setup.ps1 -Python 'D:/miniconda/python.exe'
./scripts/start.ps1
```

打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。保持终端运行，Ctrl+C 停止服务。首次启动自动建表并导入五组种子数据，重复启动不重复插入。默认数据库为根目录 `panel.db`，不进入 Git。

无需 `.env` 也能以 Demo 模式运行。需要自定义时，先将 `.env.example` 复制成根目录 `.env`；已有 `.env` 时不要覆盖。

## 开发运行（前后端分离）

终端一，从项目根目录：

```powershell
cd backend
../.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

终端二：

```powershell
cd frontend
npm run dev
```

打开 [http://127.0.0.1:5173](http://127.0.0.1:5173)。Vite 通过 `/api` 代理后端。请使用单进程后端；多 worker 不在当前支持范围内。

macOS/Linux 可使用 `python3 -m venv .venv`，随后以 `.venv/bin/python` 安装锁定依赖，`cd frontend && npm ci && npm run build`，再从 backend 启动 uvicorn。该平台尚未实机验收。

## DeepSeek 真实模式

只编辑根目录 `.env`，不要把 Key 写到前端或提交到仓库：

```dotenv
APP_MODE=live
LLM_API_KEY=在本机填写你的DeepSeek密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
LLM_JSON_MODE=true
LLM_THINKING=false
LLM_MAX_TOKENS=4096
```

修改后重启后端，创建一场新讨论。已有种子讨论仍标记为 Demo，避免把预设数据冒充真实模型结果。可将模型改为 `deepseek-flash`；模型可用性以账户为准。关闭思考模式用于缩短短回合等待，界面从不显示 `reasoning_content`。

配置依据（2026-11-17 核对）：[DeepSeek API](https://api-docs.deepseek.com/)、[JSON 输出](https://api-docs.deepseek.com/guides/json_mode/)、[思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)。JSON 模式仍需 Pydantic 与业务校验；空白、截断、格式错误最多重试一次。

| 环境变量 | 默认值 | 作用 |
| --- | --- | --- |
| APP_MODE | demo | demo/live；live 缺少密钥时启动即报错 |
| DATABASE_URL | 根目录 panel.db | SQLite 路径 |
| LLM_TIMEOUT | 45 | 单次模型请求超时秒数 |
| LLM_CONCURRENCY | 4 | 所有讨论共享的请求并发上限 |
| MAX_TURNS | 8 | 每场最多专家发言数 |
| MAX_DURATION | 600 | 讨论循环时间预算；在途请求及结尾有额外宽限 |
| MAX_CALLS | 180 | 每任务模型调用次数上限，重试也计数 |
| DEMO_DELAY | 1.3 | 演示模式节奏，自动化测试使用更小值 |
| SEED_ON_START | true | 是否自动补充五组种子数据 |

## 测试与构建

```powershell
cd backend
../.venv/Scripts/python.exe -m pytest -q
cd ../frontend
npm run build
npm run test:e2e
```

E2E 默认使用已安装的 Chrome，在 8001/5174 启动独立测试服务和新 SQLite 文件，不依赖人工运行的 8000/5173。无 Chrome 时可设置 `PLAYWRIGHT_CHANNEL=msedge` 使用已安装的 Edge。测试报告在 `frontend/playwright-report`，失败截图/追踪在 `frontend/test-results`，均不进入 Git。

测试覆盖包括：调度公平性、直接反驳、无人申请、人数校验、重复启动、并发讨论、证据隔离、SSE 游标补发、模型失败/超时/空白/截断、重启中断、种子幂等，以及创建到总结的桌面/手机完整流程。实际验证结果见 [验证记录](docs/verification.md)。

## API 与数据

自动 API 文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)。完整契约与错误格式见 [API 说明](docs/api.md)。

核心路径：`GET /api/discussions`、`POST /api/discussions`、`GET /api/discussions/{id}`、`POST /api/discussions/{id}/start`、`GET /api/discussions/{id}/events`。

手动初始化：从 backend 执行 `../.venv/Scripts/python.exe -m app.seed`。五组话题覆盖 AI 招聘、四天工作制、AI 教育、增长/盈利、城市交通；每组包含 1 主持人与 4 专家。

## 已知边界

- 当前是本地单进程 MVP，无登录、云部署、语音、外部事实检索。服务重启后未结束讨论标记中断，保留历史；重新讨论需要新建。
- 真实模型质量、延迟和费用尚未实测。Demo 是预设规则，不代表真实 AI 推理效果。
- 证据校验确保消息真实存在、属于当前讨论且涉及至少两位专家；语义是否足以支持共识仍需人工评估。
- 首版按完整短发言实时推送，不提供 token 逐字流式。
- 首页目前展示最新 100 场；API 支持分页。没有实现生产级跨进程任务队列或 SQLite 多写者扩展。
- 开发工具实际为 Codex，未使用 Claude Code，复盘不会冒写其他工具使用经历。

交付文档：[产品与验收](docs/product.md)、[架构](docs/architecture.md)、[Prompt 记录](docs/prompt-log.md)、[工作流复盘](docs/workflow.md)、[续接说明](docs/handoff.md)。
