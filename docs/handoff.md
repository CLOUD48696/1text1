# 续接说明

更新：2026-11-18（Asia/Shanghai）。

## 当前状态

用户已经恢复“继续开发”，并限定真实模型暂时只用 DeepSeek。已实现本地 MVP，前后端完整闭环、SQLite、测试与文档已落地。本轮收尾安装复现与 GitHub 同步。远程是用户授权的私有仓库 https://github.com/CLOUD48696/1text1.git，分支 main。

## 已完成

- React/TypeScript/Vite 前端：首页、动态人数、阵容确认、三栏演播厅、小屏标签、专家状态、Transcript、共识/分歧及证据定位、总结与错误恢复。
- FastAPI/Pydantic/SQLAlchemy/SQLite：五类实体、五组种子、独立后台任务、专家意图仲裁、主持人开场/追问/总结、过程观点提炼。
- 一致快照与持久化 SSE，Last-Event-ID 补发，重复 start 幂等、多讨论隔离和引用校验。
- DeepSeek 适配器：默认 deepseek-v4-pro、JSON 模式、thinking disabled、max_tokens=4096；可配置 deepseek-flash。处理空白/截断/无效输出并有限重试。
- 明确标注的 Demo 模式使用预设内容，但走真实后端链路；live 失败不降级成演示。
- 本地 .env 已创建且被 Git 忽略，创建时未填 Key。后续不要输出此文件，以免用户已填写。
- 2026-11-17：后端 27 项测试通过，桌面/手机 E2E 6 项通过，TypeScript/Vite 构建通过；详细见 verification.md。
- API 文档、ER 图、启动脚本、过程记录、工作流复盘已编写。
- 2026-11-18 安装复现完成：setup.ps1、npm ci 和构建成功；start.ps1 运行后首页 HTTP 200，health 为 demo，列表含 5 场讨论。

## 阶段提交

- a6526f7：规划。
- 1819b48：类型契约和界面 Demo。
- 5bc13cb：调度与证据先行测试。
- 5f54be3：数据库、引擎、SSE 与集成测试。
- 1efc3f1：前端完整链路、组件拆分、E2E。
- 9309db8：DeepSeek 配置与异常验证。
- 文档收尾和远程状态以 git log、git status、origin/main 为准，不根据本清单猜测是否推送。

## 下一步

1. 先检查 Git 状态与 README，不覆盖用户变化，不读取/输出 .env 中的密钥。
2. 用户本地填写 LLM_API_KEY，改 APP_MODE=live 后重启，创建新讨论进行真实 DeepSeek 验收。记录模型、耗时、相关性、观点证据质量。现有种子仍是 Demo。
3. 用户按人工验收清单操作，记录真实反馈；不得将 AI 自测记为人工通过。
4. 开发工具实际是 Codex，未使用 Claude Code。Prompt 文档区分用户原话和 Codex 阶段指令，完整原始上下文在本聊天；若要求独立原始 Prompt 日志，需要如实补充聊天导出，不能伪造。
5. 如需要压缩包，排除 .env、.venv、node_modules、数据库、测试缓存等再打包。

## 启动与测试

根目录执行 ./scripts/setup.ps1，再 ./scripts/start.ps1；浏览器打开 http://127.0.0.1:8000。开发模式可在 frontend 运行 npm run dev，使用 5173。只支持单进程后端，不使用 --workers。

backend 下运行 ../.venv/Scripts/python.exe -m pytest -q；frontend 下运行 npm run build 和 npm run test:e2e。E2E 使用独立 8001/5174 端口、临时数据库和已安装的 Chrome；可用 PLAYWRIGHT_CHANNEL=msedge 指定 Edge。

## 边界与未完成

真实 API 与用户人工验收尚未完成；无云部署、语音、鉴权或 RAG。首页显示最新 100 场，API 支持分页；服务重启将遗留任务标记 interrupted，不做跨进程续跑。前端实际使用原生 CSS，未引入最初计划的 Tailwind/shadcn。SSE 不是逐 token 流。代码验证证据归属与专家数量，观点语义仍需人工评估。

## 环境问题

PowerShell profile 曾报 conda 初始化错误，命令使用 login=false。Python 可用路径 D:/miniconda/python.exe，项目环境 .venv。受限权限下本地监听可能存在但不可连通，不能仅凭 ready 文本判断启动成功；需验证 HTTP 200，不应改系统防火墙。

Windows 重装 npm 依赖前需关闭 Vite/esbuild。2026-11-17 的 npm ci 因 esbuild 占用失败；随后自动审批因额度耗尽未执行恢复操作。2026-11-18 用户明确要求继续，重新检查无残留进程后恢复安装。当前服务是否运行须实际检查，不假定旧 PID 有效。
