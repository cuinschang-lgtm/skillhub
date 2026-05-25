# SkillHub P0-2 任务进度 WebSocket 越权修复设计

## 背景

当前后端暴露了任务进度订阅端点：

- `apps/api/app/ws/progress.py` 中的 `GET ws /ws/progress/{task_id}`

该端点当前行为是：

- 只要客户端知道 `task_id`，就可以直接建立 WebSocket 连接
- 连接建立后立即订阅 `progress_bus` 对应频道
- 后端没有验证用户身份
- 后端没有校验 `Task.user_id` 是否属于当前用户

这意味着任意用户只要猜到或拿到他人的 `task_id`，就可能订阅并观察该任务的编译进度。这属于 P0 级越权风险。

## 目标

- 修复 `ws /ws/progress/{task_id}` 的越权订阅问题
- 将 WebSocket 订阅接入现有 JWT 认证体系
- 确保只有任务 owner 可以订阅自己的进度流
- 在本次修复中不改变前端现有进度页交互模式

## 非目标

- 不在本次把前端进度页从轮询切换到 WebSocket
- 不新增单独的 WebSocket session 或 task-specific token 体系
- 不扩展到其他任务接口的重构性调整

## 已确认事实

- 当前 `apps/api/app/ws/progress.py` 在 `accept()` 之后直接 `subscribe(task_id)`
- 当前 `apps/api/app/api/v1/tasks.py` 已对任务详情和取消任务做了 owner 校验
- 当前 `apps/web/src/app/(dashboard)/progress/[taskId]/page.tsx` 实际仍在轮询 `/api/tasks/{taskId}`
- 当前项目已在 `P0-1` 中完成 JWT 签发和 Bearer 鉴权基础能力

## 设计原则

- 优先堵住真实越权入口，不扩大前端交互范围
- 复用现有认证能力，不引入第二套鉴权体系
- 在建立订阅前完成身份与 owner 校验
- 保持错误暴露最小化，避免借由差异响应枚举他人任务

## 方案选择

本次采用以下方案：

- WebSocket 握手时携带 token
- 后端在握手前校验 token
- 后端根据 token 识别当前用户，并校验 `Task.user_id == 当前用户`
- 校验通过后才允许 `accept()` 和 `subscribe(task_id)`

不采用以下方案：

- 不采用“前端继续不用 WebSocket，因此无需修复”的方式，因为后端漏洞仍然存在
- 不采用单独 task token 方案，因为会增加新的签发逻辑，超出最小修复范围

## 架构设计

### 后端 WebSocket 鉴权

`apps/api/app/ws/progress.py` 将成为唯一改造重点。

处理流程：

1. 从 WebSocket 握手参数中提取 token
2. 解码 token 并识别当前用户
3. 校验 `task_id` 格式是否合法
4. 查询任务并校验 owner
5. 仅在校验通过后执行 `accept()` 和 `progress_bus.subscribe(task_id)`

### token 传递方式

本次优先支持 query 参数：

- `ws://.../ws/progress/{task_id}?token=<access_token>`

选择理由：

- 浏览器原生 `WebSocket` 不方便设置标准 `Authorization` 头
- query 参数方案足够支撑当前最小修复
- 后续如果前端接入 WebSocket，也可直接复用该方式

## 组件改动

### `apps/api/app/ws/progress.py`

需要完成以下改造：

- 在连接建立前读取 query 参数中的 `token`
- 复用现有 JWT 解码逻辑识别用户
- 对非法 token、缺失 token、过期 token 直接拒绝连接
- 将 `task_id` 解析为 UUID，并校验任务是否存在
- 校验任务 owner 是否等于当前用户
- 仅在全部通过时调用 `accept()`
- 仅在通过后创建并订阅 `queue`

### 认证复用

认证逻辑应尽量复用已有能力，例如：

- `app.security.decode_access_token()`

必要时可以在不破坏当前 HTTP 鉴权逻辑的前提下，抽出适合 WebSocket 使用的查询辅助函数，但不应复制一套新的 token 校验逻辑。

## 错误处理

- 未提供 token 时：拒绝连接
- token 非法或过期时：拒绝连接
- `task_id` 非法时：拒绝连接
- 任务不存在时：拒绝连接
- 任务不属于当前用户时：拒绝连接

错误处理原则：

- 不进入 `progress_bus.subscribe(task_id)`
- 不泄露额外任务元信息
- 拒绝行为保持简洁，不做细粒度区分暴露

## 前端影响

当前前端不需要功能改动。

原因：

- 进度页当前走 `/api/tasks/{taskId}` 轮询，owner 校验已经存在
- 本次修复目标是堵住后端公开 WebSocket 越权入口
- 不将本次范围扩大为“进度页协议切换”

若后续启用前端 WebSocket：

- 由前端在建立连接时附带 access token
- 后端按本次设计完成 owner 校验

## 验收标准

- 未登录访问 `ws /ws/progress/{task_id}`，连接失败
- 使用非法或过期 token 访问 `ws /ws/progress/{task_id}`，连接失败
- 用户 A 使用自己的 token 订阅用户 B 的任务，连接失败
- 用户本人使用自己的 token 订阅自己的任务，连接成功并可收到进度消息
- 当前进度页轮询模式不回归，`/api/tasks/{taskId}` 仍可正常工作

## 测试与验证

实现完成后至少验证以下内容：

- 后端启动正常
- 合法 token + 本人任务的 WebSocket 连接成功
- 无 token 的 WebSocket 连接失败
- 非 owner token 的 WebSocket 连接失败
- 任务详情页轮询接口仍正常返回

如环境允许，可补充：

- 手工模拟两名不同用户，验证跨用户订阅无法建立
- 在真实 pipeline 运行时观察 owner 用户是否能收到进度流

## 风险与缓解

风险：

- WebSocket 与 HTTP 不同，请求头获取方式不同，若处理不当容易接入失败
- 过度暴露拒绝原因可能帮助攻击者枚举任务存在性
- 若校验顺序不对，可能先 `accept()` 再失败，留下短暂可用窗口

缓解：

- 采用 query token 的最小可行接入方式
- 在 `accept()` 前完成全部校验
- 保持拒绝行为简单，不返回多余任务信息

## 产出

本次设计对应的实现产出应包括：

- 一个具备身份校验和 owner 校验的任务进度 WebSocket 端点
- 与现有 JWT 体系一致的认证复用
- 一个已被关闭的进度越权订阅入口
