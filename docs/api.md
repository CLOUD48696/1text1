# API 与事件说明

本地服务根地址 `http://127.0.0.1:8000`，前端开发通过 Vite `/api` 代理。无需登录，服务仅绑定 loopback；这不是面向公网的鉴权方案。

## 路由

| 方法 | 路径 | 输入 | 成功响应 |
| --- | --- | --- | --- |
| GET | /api/health | 无 | `{status: "ok", mode: "demo"}` |
| GET | /api/discussions | limit=1..100、cursor>=0 | `{items: Discussion[], next_cursor: number|null}` |
| POST | /api/discussions | `{topic: string, expert_count: 2..6}` | 202，`{discussion_id, status: "generating"}` |
| GET | /api/discussions/{id} | 无 | 一致快照，见下方 |
| POST | /api/discussions/{id}/start | 无或 `{}` | 202 + 当前 Discussion；running 重复调用不创建新任务 |
| POST | /api/discussions/{id}/retry-generation | 无或 `{}` | 202；只允许生成阶段失败且尚无消息 |
| GET | /api/discussions/{id}/events | after>=0、可选 Last-Event-ID | text/event-stream |

topic 先去除首尾空白，再校验 4–240 字。人数默认 4，不包含主持人。不同角色均为虚构人物。

错误格式：`{code, message, retryable}`。找不到讨论为 404，输入或游标错误为 422，非法状态转换为 409。后台模型错误通过讨论状态和持久化事件返回，不暴露供应商原始响应、Key 或堆栈。

## 快照

```json
{
  "discussion": {"id": "uuid", "topic": "议题", "expert_count": 4, "status": "ready", "phase": "roster", "mode": "demo", "summary": null, "error": null},
  "participants": [],
  "messages": [],
  "insights": [],
  "last_event_sequence": 0
}
```

示例省略时间、内部计数等附加字段。Participant 包含 id、role、name、profession、title、stance、color、status、public_focus、position。Message 包含 id、participant_id、sequence、content、reply_to_message_id、created_at。Insight 包含 id、kind、content、evidence_message_ids、updated_at。

## SSE

先获取快照，再使用其 last_event_sequence 订阅。断线重连时 Last-Event-ID 优先于 URL 的 after。服务端从数据库按序补发，不会由于观众连接而启动 Runner。

```text
id: 8
data: {"discussion_id":"uuid","sequence":8,"type":"message.created","data":{"discussion":{},"message":{}},"created_at":"UTC ISO 8601"}

```

不使用 SSE 的命名 event 字段，前端统一通过 `onmessage` 接收，再读取 JSON 的 type。每条事件都带当前 Discussion 元数据；参与者状态、消息和观点按事件类型附加。

| type | data 附加字段 |
| --- | --- |
| roster.ready | participants |
| participant.updated | participants |
| message.created | message |
| insights.updated | insights（当前有效观点全集） |
| discussion.generating / running / completed / failed / interrupted | participants |

序号在同场讨论内单调递增，前端按 discussion_id + sequence 去重。消息/状态更新和事件写入处于同一短事务，提交后才被订阅者读取。服务端每 250ms 查询新事件，约每 10 秒发心跳注释；终止状态的事件补发完后关闭流，前端也主动停止重连。

请求负数、非整数或超过当前最新事件的游标会返回 422。直接重新获取快照即可恢复；不会因错误游标静默漏掉历史。
