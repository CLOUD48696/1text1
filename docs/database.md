# 数据库设计

数据库使用 **SQLite**，ORM 为 SQLAlchemy。默认文件是项目根目录 panel.db，可通过后端 DATABASE_URL 修改；本地数据文件不提交 Git。

实现依据：[models.py](../backend/app/models.py)、[database.py](../backend/app/database.py)、[seed.py](../backend/app/seed.py)。

## 1. 实体关系

~~~mermaid
erDiagram
  discussions ||--o{ participants : contains
  discussions ||--o{ messages : records
  discussions ||--o{ insights : derives
  discussions ||--o{ events : publishes
  participants ||--o{ messages : speaks
  messages o|--o{ messages : replies_to
  discussions {
    string id PK
    string topic
    int expert_count
    string status
    string phase
    string mode
    string summary
    string error
    int event_seq
    int message_seq
    string created_at
    string updated_at
  }
  participants {
    string id PK
    string discussion_id FK
    int position
    string role
    string name
    string profession
    string title
    string stance
    string color
    string status
    string public_focus
  }
  messages {
    string id PK
    string discussion_id FK
    string participant_id FK
    int sequence
    string content
    string reply_to_message_id FK
    string created_at
  }
  insights {
    string id PK
    string discussion_id FK
    string kind
    string content
    json evidence_message_ids
    string updated_at
  }
  events {
    string id PK
    string discussion_id FK
    int sequence
    string type
    json data
    string created_at
  }
~~~

Insight 的证据 ID 存在 JSON 数组中，没有消息关联表或数据库外键；归属检查由业务层完成，故图中不将其画成物理外键关系。

## 2. 表与字段语义

| 表 | 字段说明 |
| --- | --- |
| discussions | topic 为议题；expert_count 不包含主持人；status 为生命周期，phase 为讨论阶段，mode 为 demo/live；summary、error 可空；event_seq 和 message_seq 分别计数 |
| participants | position 决定展示顺序；role 为 host/expert；身份、立场与颜色用于一致展示；status 为 idle/preparing/speaking；public_focus 仅保存公开关注点 |
| messages | participant_id 指向发言人；sequence 为讨论内发言序号；reply_to_message_id 可空，表示回应哪条发言 |
| insights | kind 为 consensus/disagreement；content 为观点文本；evidence_message_ids 为证据消息 ID 数组 |
| events | sequence 为讨论内事件序号；type 为语义事件类型；data 为当前讨论元数据和该事件的业务内容 |

普通记录 ID 为 UUID 字符串；种子讨论 ID 使用确定性 UUID，便于幂等初始化。时间以 UTC ISO 8601 字符串保存。事件和消息有独立序列，不能混用作游标。

## 3. 约束与隔离

- 所有子表都有 discussion_id 外键和索引。
- messages 和 events 各自具有 (discussion_id, sequence) 唯一约束。
- messages.participant_id、reply_to_message_id 为外键；业务层进一步检查其是否属于同场讨论。普通外键本身不足以防止跨场引用。
- 阵容人数、姓名不重复、专家短发言和观点证据要求由 Pydantic/业务层验证，未全部实现为数据库 CHECK 约束。
- 观点证据必须出现在当前讨论消息中，并至少涉及两位专家；无效观点被过滤。
- 主持人和专家数量由阵容校验保障，不依赖数据库唯一索引表达。

## 4. 事务与查询

Store 使用短事务更新业务记录并追加对应事件，成功提交后 SSE 才能读取，避免“页面收到事件但数据库尚未保存”的中间状态。

单进程 RLock 协调写入与快照读取；SQLite 启用 foreign_keys 和 busy_timeout=10000。网络请求不持有数据库事务。未开启 WAL，不支持多个后端 worker 共用任务状态。

列表按创建时间倒序、ID 辅助排序，cursor 实际为非负偏移量；事件按讨论内序号升序读取，每批最多 100 条。快照返回讨论、嘉宾、消息、观点和一致的最新事件序号。

## 5. 初始化与样例

服务启动时调用 create_all 建表，并在 SEED_ON_START=true 时导入种子。也可在项目根目录执行：

~~~powershell
cd backend
../.venv/Scripts/python.exe -m app.seed
~~~

种子提供五个话题、每场 1 主持人 + 4 专家；第一场是带证据和总结的已结束示例，其他四场待确认。重复运行不会重复创建已存在的种子讨论。

当前没有版本化迁移脚本；create_all 用于初始化缺失表，不会自动迁移已有表结构。后续改变 schema 需要单独设计迁移，不能把重新建库当作保留用户数据的升级方式。

## 6. 数据与交付

panel.db 属于本机运行数据，由脚本重建，不放入源码仓库。交付提供模型定义和初始化脚本；测试使用独立数据库。未保存 API Key 或模型隐藏思维链到这些表中。
