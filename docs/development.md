# 安装与开发指南

本文集中说明环境、依赖、启动、模型配置与开发命令。产品功能见[产品需求](product.md)，测试结果见[验证记录](verification.md)。

## 1. 环境与目录

已验证组合：Windows、Python 3.14.7、Node.js 22.19.0、npm 10.9.3。启动脚本提示 Python 3.11+，但其他解释器组合和 macOS/Linux 未进行完整实机验收。

| 路径 | 用途 |
| --- | --- |
| backend/app | 后端业务、SQLite 模型、DeepSeek 适配器 |
| backend/tests | 后端单元与集成测试 |
| frontend/src | 页面、组件、状态与样式 |
| frontend/tests/e2e | Playwright 浏览器测试 |
| scripts | 安装、启动脚本 |
| docs | 需求、设计、验证和交付文档 |
| .env.example | 可提交的配置模板，不含真实 Key |
| .env | 本机后端配置，不提交 Git |
| panel.db | 本机 SQLite 数据，由初始化创建 |
| .venv、frontend/node_modules | 安装生成的依赖目录，不提交 Git |

## 2. requirements 文件是什么

这里的 requirements 指 Python 安装依赖，产品需求文档是 product.md。

| 文件 | 用途 | 维护方式 |
| --- | --- | --- |
| [backend/requirements.txt](../backend/requirements.txt) | 直接依赖及允许版本范围，例如 fastapi>=0.115,<1 | 新增或调整依赖时修改 |
| [backend/requirements.lock.txt](../backend/requirements.lock.txt) | 已验证环境的精确版本，含间接依赖，例如 fastapi==0.163.1 | 依赖调整后在隔离环境安装、验证并更新 |
| [frontend/package.json](../frontend/package.json) | 前端依赖声明与命令 | 维护前端依赖和脚本 |
| [frontend/package-lock.json](../frontend/package-lock.json) | 前端依赖解析结果 | npm 随依赖变更更新，安装使用 npm ci |

setup.ps1 使用 requirements.lock.txt 安装后端，不需要把两份 requirements 分别安装一遍。它是固定版本清单，不包含包哈希，也不保证所有操作系统均兼容。纯文档修改不需要更新锁文件。

## 3. 首次安装与启动

在项目根目录打开 PowerShell：

~~~powershell
./scripts/setup.ps1
./scripts/start.ps1
~~~

setup.ps1 创建 .venv，按锁文件安装 Python 依赖，运行 npm ci 并构建前端。若 Python 不在 PATH，使用显式解释器路径：

~~~powershell
./scripts/setup.ps1 -Python 'C:/你的Python安装目录/python.exe'
~~~

打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。保持服务终端运行，Ctrl+C 停止。首次启动自动建表并导入五组种子；详细机制见[数据库设计](database.md)。

无需 .env 即可运行 Demo。需要自定义时将 .env.example 复制为根目录 .env；如果 .env 已存在，直接编辑，避免覆盖已有配置。

## 4. DeepSeek 配置

浏览器调用项目后端，后端从环境变量读取 Key 并请求 DeepSeek；前端不保存或填写 Key，符合本作业要求。

在根目录 .env 中配置：

~~~dotenv
APP_MODE=live
LLM_API_KEY=在本机填写你的DeepSeek密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=填写账户可调用的模型标识
~~~

LLM_MODEL 的示例是占位说明，必须替换为真实模型标识。当前代码默认值为 deepseek-v4-pro；这是代码配置事实，不代表已经验证账户权限或实际调用成功。

保存后停止旧服务并重新启动，新建讨论进行验证。已有 Demo 种子保留原模式。live 出错不会自动切换成预设文本；错误会在页面显示。真实模型验收步骤见验证记录。

接入代码：[provider.py](../backend/app/llm/provider.py)；配置读取：[config.py](../backend/app/config.py)；运行时提示词：[prompts.py](../backend/app/llm/prompts.py)。适配器请求后端配置地址下的 /chat/completions，不将密钥发给浏览器或写入 Git。

## 5. 配置项

实际默认值以 config.py 为准，进程环境变量可覆盖 .env。

| 变量 | 当前默认值 | 说明 |
| --- | --- | --- |
| APP_MODE | demo | demo/live；live 缺少 Key 或模型名时拒绝启动 |
| DATABASE_URL | 项目根目录 panel.db 的 SQLite URL | 本机持久化位置 |
| LLM_API_KEY | 空 | 仅后端读取 |
| LLM_BASE_URL | https://api.deepseek.com | 模型接口基础地址 |
| LLM_MODEL | deepseek-v4-pro | 模型标识，真实可用性待验收 |
| LLM_JSON_MODE | true | 请求 JSON object 输出 |
| LLM_THINKING | false | 适配器发送 thinking disabled |
| LLM_MAX_TOKENS | 4096 | 单次输出 token 上限 |
| LLM_TIMEOUT | 45 | 每次调用超时秒数，包含等待并发许可 |
| LLM_CONCURRENCY | 4 | 进程内全部讨论共享的模型并发上限 |
| MAX_TURNS | 8 | 每场最多专家发言数，主持人不计入 |
| MAX_DURATION | 600 | 讨论循环耗时预算；任务外层另有两次请求超时的宽限 |
| MAX_CALLS | 180 | 单个生成/讨论任务调用预算，重试计数；阵容与讨论分别计数 |
| DEMO_DELAY | 1.3 | 演示节奏延迟秒数 |
| SEED_ON_START | true | 启动时补充缺失种子 |

## 6. 前后端开发运行

终端一，在项目根目录执行：

~~~powershell
cd backend
../.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

终端二，在项目根目录执行：

~~~powershell
cd frontend
npm run dev
~~~

访问 [http://127.0.0.1:5173](http://127.0.0.1:5173)。Vite 将 /api 代理到 8000。仅使用一个后端进程，不添加 --workers。如果已有 start.ps1 服务占用 8000，先停止它。

## 7. 测试命令

从项目根目录执行：

~~~powershell
cd backend
../.venv/Scripts/python.exe -m pytest -q
cd ../frontend
npm run build
npm run test:e2e
~~~

E2E 自动启动独立 8001/5174 服务与测试数据库，使用 DemoLLM，不访问真实 DeepSeek。默认使用已安装的 Chrome；可在当前终端设置 PLAYWRIGHT_CHANNEL=msedge 后改用已安装的 Edge。

浏览器报告位于 frontend/playwright-report，失败截图/追踪位于 frontend/test-results，这些生成文件不提交 Git。真实模型验证单独记录，不能混入替身测试的通过数。

## 8. 常见问题

| 现象 | 检查与处理 |
| --- | --- |
| 页面打不开 | 确认服务终端仍运行；构建版用 8000，开发版用 5173；访问 /api/health 检查实际连通 |
| 8000 有健康响应但首页不可用 | 确认 npm run build 成功；构建完成后重启后端，使其挂载 dist |
| npm ci 提示 esbuild 文件被占用 | 关闭该项目 Vite 开发服务后重试安装 |
| live 启动失败 | 检查本机 APP_MODE、Key、模型名；不要把 Key 粘贴到日志或聊天 |
| 页面显示模型失败 | 检查网络、模型权限、额度及输出格式；目前不会自动降级 Demo |
| 刷新后看到中断 | 服务重启中断了任务；历史保留，需要新建讨论 |
| 修改 .env 后没有变化 | 后端在启动时读取配置，需要重启 |

进程输出 ready 只代表启动阶段信息，验收还要确认 HTTP 能连接并能在浏览器完成操作。
