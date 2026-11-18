# 系统技术设计

本文描述当前代码的实现，不保留已经废弃的候选方案。数据表详见[数据库设计](database.md)，端点与事件格式详见[API 契约](api.md)。

## 1. 架构与选型

~~~mermaid
flowchart LR
  UI["React / TypeScript"] -->|"HTTP 命令与快照"| API["FastAPI"]
  API --> Runner["讨论任务 Engine"]
  Runner --> Scheduler["意图仲裁"]
  Runner --> LLM["LLMClient"]
  LLM --> Demo["Demo 预设规则"]
  LLM --> Provider["DeepSeek 适配器"]
  API --> Store["Store / SQLAlchemy"]
  Runner --> Store
  Store --> DB[("SQLite")]
  DB -->|"持久化事件"| SSE["SSE"]
  SSE --> UI
~~~

| 层 | 实现 | 选择理由 |
| --- | --- | --- |
| 前端 | React、TypeScript、Vite、Zustand、Lucide、原生 CSS | 页面组件与事件状态分离，减少 MVP 依赖 |
| 后端 | FastAPI、Pydantic、SQLAlchemy | HTTP 接口、模型输出校验和持久化边界清晰 |
| 存储 | SQLite | 满足作业硬性要求，本地无需额外数据库服务 |
| 通信 | HTTP + SSE | 浏览器发命令，后端单向持续推送讨论进度 |
| 任务 | 单进程 asyncio 任务注册表 | 每场独立运行，无需 Redis/Celery |
| 模型 | DeepSeek HTTP 适配器、DemoLLM | 真实服务与可重复的测试替身分开 |

Vite 开发服务器代理 /api；构建后的前端由 FastAPI 静态托管。两种运行方式均保留前后端代码和 API 边界。服务绑定本机地址，无公网鉴权设计。

## 2. 实际模块

| 文件 | 职责 |
| --- | --- |
| [main.py](../backend/app/main.py) | 生命周期、HTTP 路由、错误处理、SSE、静态资源 |
| [config.py](../backend/app/config.py) | 后端环境变量与配置校验 |
| [models.py](../backend/app/models.py) / [database.py](../backend/app/database.py) | 数据表、短事务、快照、事件持久化 |
| [schemas.py](../backend/app/schemas.py) | 请求与模型输出结构 |
| [runner.py](../backend/app/services/runner.py) | 阵容生成、任务生命周期、模型调用、讨论循环 |
| [scheduler.py](../backend/app/services/scheduler.py) | 发言仲裁、阵容及观点证据校验 |
| [llm](../backend/app/llm) | 协议、DeepSeek 适配器、Demo、运行时 Prompt |
| [App.tsx](../frontend/src/App.tsx) / [components](../frontend/src/components) | 首页、阵容确认、演播厅、嘉宾头像 |
| [api.ts](../frontend/src/api.ts) / [store.ts](../frontend/src/store.ts) | HTTP 请求、快照与 SSE 状态归并 |
| [styles.css](../frontend/src/styles.css) | 主题、独立滚动、响应式布局 |

## 3. 状态与任务生命周期

正常状态流为 generating → ready → running → completed。任务异常进入 failed；退出或重启造成的未完成任务进入 interrupted。运行阶段实际使用 roster、opening、discussion、closing。

- 创建讨论后启动阵容生成任务，校验通过才进入 ready。
- 用户确认后从 ready 切换到 running；对 running 重复 start 返回当前状态。
- 任务注册表以 discussion_id 为键，避免同场重复运行。
- 观众订阅只读取事件；进入、退出、刷新页面均不控制任务生命周期。
- 任务异常转换为安全的失败状态，保留已有内容，不向浏览器暴露供应商原始错误。
- 服务重启将 generating/running 标记中断。恢复执行需新建讨论，不声称可从半轮自动续跑。

## 4. 专家自主意图与仲裁

每轮读取当前讨论上下文，各专家独立生成 wait、raise、supplement 或 rebut 意图，并提供紧迫度、可选回复消息和公开关注点。意图请求可以并发；单个专家请求失败可跳过，全部失败则终止任务。

仲裁仅选择主动申请者：

1. 紧迫度作为基础分。
2. 加入申请等待轮数的分值，上限为 10 轮。
3. 对有效目标的反驳加分；刚发过言者扣分。
4. 连续两次发言的专家本轮排除，避免三连发。
5. 只让胜出者生成完整发言；无人可选时主持人追问，连续两轮无人可选则结束讨论循环。

因此等待者不会被强制轮询。专家发言按标点检查最多两句、最多 220 字。主持人负责开场、中途追问与最后总结。

## 5. 上下文与模型边界

每次上下文包含话题、角色、最近 12 条消息、各角色更早发言中的最后一条 180 字摘录，以及已有观点。上下文按讨论构建；没有额外的模型滚动摘要任务。

运行时提示词位于 [prompts.py](../backend/app/llm/prompts.py)。DeepSeek 适配器发送任务说明、JSON Schema 和格式示例，读取 message.content，再执行 Pydantic 与业务校验；不向用户展示 reasoning_content。

模型负责角色与语义，应用负责状态、预算、校验及仲裁。每次调用最多两次尝试，使用全局并发上限和请求超时。讨论还受专家发言数、循环次数、调用次数和耗时预算约束，并预留总结空间。预算默认值统一见安装与开发指南。

## 6. 过程共识与分歧

从第二次专家发言起，每次专家发言后提炼观点。输入包含已有观点与当前上下文；后端检查引用存在于本讨论、涉及至少两位专家，并按类别与内容去重。

当前有效观点作为完整集合写入；未出现在新集合中的旧观点移除，相同观点保留 ID 并更新证据。界面可以点击证据定位发言。

校验能排除错房间、缺失消息和单人证据，不能证明文本真正达成共识或产生分歧；这一语义质量需真实模型和人工验收。

## 7. 持久化与事件恢复

消息、状态、观点与其事件在同一短事务中写入。SQLite 开启外键与 10 秒 busy timeout；单进程 RLock 协调访问，模型请求在数据库事务之外。未启用 WAL，不支持多 worker。

前端先取一致快照，再从 last_event_sequence 订阅 SSE；重连优先使用 Last-Event-ID。事件从 SQLite 读取，每 250ms 检查一次，约 10 秒心跳。终止状态事件发完后结束流。

Zustand 按讨论 ID 和序号拒绝过期事件，防止旧快照覆盖新状态；消息按 ID 去重。首次连接与快照之间的事件由数据库补发。首版推送完整短发言，不是逐 token 流。

## 8. 实现限制

单进程与本地文件存储适用于当前 MVP，不代表支持分布式任务或公网多租户。首页已接入服务端分类与分页；真实模型质量与耗时未验收。验证证据和交付差距分别维护在[测试记录](verification.md)与[交付清单](delivery.md)。
