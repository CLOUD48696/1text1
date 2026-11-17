# AI Panel Studio

AI 圆桌讨论本地 Web App 面试项目。输入话题、确认 AI 生成的主持人与专家阵容，观看由当前讨论内容驱动的圆桌讨论，并实时查看共识与分歧。

## 当前状态

2026-11-17：完成本地 Git 初始化和开发规划。**尚未实现业务代码、安装项目依赖、运行应用或执行测试。** 用户因额度限制要求先保存规划，恢复后按照下列文档继续。

## 开发入口

- [项目协作约定](AGENTS.md)
- [产品方案与验收标准](docs/product.md)
- [技术方案、数据模型与 API 契约](docs/architecture.md)
- [24 小时实施计划](docs/implementation-plan.md)
- [当前进度与续接说明](docs/handoff.md)
- [真实 Prompt 与过程记录](docs/prompt-log.md)

## 计划技术栈

前端：React、TypeScript、Vite、Tailwind CSS、shadcn/ui、Lucide、Zustand。

后端：Python、FastAPI、Pydantic、SQLAlchemy、SQLite；HTTP API + SSE；独立模型适配层与轻量讨论状态机。

测试：pytest（核心业务与 API）、Playwright（完整用户流程）。

这些是待落实的选型，版本将在首次安装并验证兼容性后锁定。当前机器已检测到 Python 3.14.7、Node.js 22.19.0、npm 10.9.3；需验证依赖对当前运行时的支持。

## 启动与提交

启动命令、环境变量和测试命令将在脚手架建立后补齐，目前没有可运行版本。应用默认计划提供明确标注的演示模式，以及仅从后端环境变量读取密钥的真实模型模式。

尚未配置 GitHub 远程仓库，也未推送代码。目标是先完成本地可验收版本，再使用用户授权的仓库权限推送；不在聊天或仓库中记录密钥。
