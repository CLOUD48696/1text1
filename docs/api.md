# API 与事件契约

服务根地址为 http://127.0.0.1:8000；所有业务端点使用 /api 前缀。开发时由 Vite 代理，构建后页面与 API 同源。无需登录，仅用于本机运行。

实现：[main.py](../backend/app/main.py)、[schemas.py](../backend/app/schemas.py)。服务运行后可查看 [OpenAPI 页面](http://127.0.0.1:8000/docs)。

## 1. HTTP 路由

| 方法 | 路径 | 输入 | 成功响应 |
| --- | --- | --- | --- |
| GET | /api/health | 无 | 200，status 与 mode |
| GET | /api/discussions | limit 默认 50，范围 1–100；cursor 默认 0，为非负偏移量 | 200，items 与 next_cursor |
| POST | /api/discussions | topic、expert_count | 202，discussion_id 与 generating 状态 |
| GET | /api/discussions/{id} | 讨论 ID | 200，一致快照 |
| POST | /api/discussions/{id}/start | 无需请求体 | 202，当前 Discussion 对象 |
| POST | /api/discussions/{id}/retry-generation | 无需请求体 | 202，discussion_id 与 generating 状态 |
| GET | /api/discussions/{id}/events | after 默认 0，可选 Last-Event-ID 请求头 | 200，text/event-stream |

topic 去除首尾空白后要求 4–240 字；expert_count 默认 4，范围 2–6，不包含主持人。额外创建字段会被拒绝。

start 仅允许已确认的 ready 阵容进入运行；对 running 重复调用不新增任务。retry-generation 仅用于 failed、phase=roster 且无发言的讨论；其他失败或中断应新建讨论。

## 2. 创建、列表与快照示例

创建请求：

~~~json
{"topic":"小型团队应该优先使用 AI 编程工具还是增加招聘？","expert_count":4}
~~~

异步受理响应：

~~~json
{"discussion_id":"示例讨论ID","status":"generating"}
~~~

列表结构为 {"items": [...], "next_cursor": 50}，末页 next_cursor 为 null。items 是 Discussion 对象，不包含嘉宾和发言。

以下快照只示意字段结构，数组省略内容，并非一场完整讨论的实测响应：

~~~json
{
  "discussion": {
    "id": "示例讨论ID",
    "topic": "示例议题",
    "expert_count": 4,
    "status": "generating",
    "phase": "roster",
    "mode": "demo",
    "summary": null,
    "error": null,
    "event_seq": 0,
    "message_seq": 0,
    "created_at": "2026-11-18T00:00:00+00:00",
    "updated_at": "2026-11-18T00:00:00+00:00"
  },
  "participants": [],
  "messages": [],
  "insights": [],
  "last_event_sequence": 0
}
~~~

participants、messages、insights 的字段与[数据库设计](database.md)一致。participants 按 position、messages 按 sequence 排序。mode 随讨论保存；切换后端 live 配置不会把已有 Demo 记录变成真实模型记录。

## 3. SSE 事件格式

客户端先获取快照，再以 last_event_sequence 作为 after 订阅。重连时 Last-Event-ID 优先于 URL 中的 after；游标为当前讨论内的事件序号。

~~~text
id: 8
data: {"id":"示例事件ID","discussion_id":"示例讨论ID","sequence":8,"type":"message.created","data":{"discussion":{},"message":{}},"created_at":"2026-11-18T00:00:00+00:00"}

~~~

上例省略 discussion 和 message 的具体字段。标准帧以空行结束，不发送命名 event 字段。浏览器通过 onmessage 接收，再按 JSON 的 type 分发。

每条事件的 data 都包含 discussion；其他字段如下：

| type | data 中的附加字段 |
| --- | --- |
| roster.ready | participants |
| participant.updated | participants |
| message.created | message |
| insights.updated | insights，当前有效观点全集 |
| discussion.generating / running / completed / failed / interrupted | participants |

事件 ID 为 UUID，SSE 帧的 id 则为 sequence，客户端恢复使用后者。消息序号不能作为 SSE 游标。

## 4. 恢复与一致性

事件从数据库按序补发，观众连接不会创建运行任务。前端按 discussion_id 和 sequence 去重、忽略旧状态；insights.updated 替换观点集合，不是单项追加。

服务器每 250ms 读取新事件，约每 10 秒发送心跳注释。completed、failed、interrupted 的剩余事件发送完后结束流，前端停止自动重连。ready 仍可保持订阅，等待用户确认后运行。

负数、非整数或超过最新序号的游标返回 422。客户端应重新获取快照再订阅，不能静默跳过未知历史。

## 5. 错误契约

~~~json
{"code":"invalid_state","message":"当前讨论状态不允许此操作","retryable":false}
~~~

| HTTP 状态 | code | 情况 |
| --- | --- | --- |
| 404 | not_found | 讨论或 API 路径不存在 |
| 409 | invalid_state | 非法状态切换、任务尚未停止等 |
| 422 | invalid_input | 请求体、查询参数结构校验失败 |
| 422 | invalid_cursor | Last-Event-ID 或游标范围无效 |

后台模型失败发生在 202 响应之后，通过讨论 error 字段和 discussion.failed 事件通知，不代表最初 HTTP 创建请求失败。错误不返回 Key、供应商原始响应或内部堆栈。
