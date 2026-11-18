# AI Panel Studio

本地运行的 AI 圆桌讨论 Web 应用。用户输入议题、选择专家人数并确认阵容后，观看主持人与专家讨论，实时查看发言、共识与分歧，最后获得自然语言总结。

**当前交付状态：演示模式闭环已验证；DeepSeek 调用适配器已实现，真实模型与用户人工验收尚未完成。** 完成情况及待办统一维护在[交付清单](docs/delivery.md)，不将自动化测试通过等同于全部作业要求通过。

## 快速运行

已验证环境：Windows、Python 3.14.7、Node.js 22.19.0、npm 10.9.3。安装 Python、Node.js 后，在项目根目录打开 PowerShell：

~~~powershell
./scripts/setup.ps1
./scripts/start.ps1
~~~

打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。运行终端需保持打开，Ctrl+C 停止。首次启动自动创建 SQLite 数据库并导入五组话题与阵容。

默认 Demo 模式无需 API Key，使用明确标注的预设内容。启用 DeepSeek、分开启动前后端、依赖说明和故障排查见[安装与开发指南](docs/development.md)。

## 开发文档

按下列顺序阅读即可了解需求、实现、验证和交付。每份文档只维护对应主题。

| 顺序 | 文档 | 回答的问题 |
| --- | --- | --- |
| 1 | [产品需求与验收标准](docs/product.md) | 产品为谁服务、必须实现哪些功能？ |
| 2 | [系统技术设计](docs/architecture.md) | 前后端如何协作，专家如何调度？ |
| 3 | [数据库设计](docs/database.md) | SQLite 有哪些表、关系与一致性约束？ |
| 4 | [API 与事件契约](docs/api.md) | 请求、响应、SSE 与错误格式是什么？ |
| 5 | [安装与开发指南](docs/development.md) | 如何安装、配置模型、启动和测试？ |
| 6 | [测试与验收记录](docs/verification.md) | 已验证什么，人工如何验收？ |
| 7 | [开发过程与工作流复盘](docs/workflow.md) | 如何分阶段实现、遇到什么问题？ |
| 8 | [Prompt 与开发指令记录](docs/prompt-log.md) | 有哪些可追溯记录，原始证据是否齐备？ |
| 9 | [交付清单](docs/delivery.md) | 原题规则和交付物完成到哪里？ |

[AGENTS.md](AGENTS.md) 是编码协作规则，供开发工具读取，不属于产品说明或用户操作手册。

## 技术与代码位置

- 前端：React、TypeScript、Vite、Zustand、Lucide、原生 CSS，位于 [frontend/src](frontend/src)。
- 后端：FastAPI、Pydantic、SQLAlchemy、SQLite，位于 [backend/app](backend/app)。
- 实时通信：HTTP 命令和快照 + SSE 持久化事件。
- 模型：后端 DeepSeek 适配器与独立 Demo 实现，密钥仅由后端读取。
- 测试：pytest + Playwright，历史结果为 27 项后端测试、6 项 E2E 通过，详见验证记录。
- 仓库：[CLOUD48696/1text1](https://github.com/CLOUD48696/1text1)，私有仓库。

## 使用边界

只支持本地单后端进程。服务重启后未完成讨论标记为中断，保留历史，不自动续跑。首页目前只展示最新 100 场讨论；SSE 按完整短发言更新。真实模型质量、延迟、费用及用户人工验收尚未验证。详细差距见交付清单。
