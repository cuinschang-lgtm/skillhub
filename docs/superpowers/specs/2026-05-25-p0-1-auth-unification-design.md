# SkillHub P0-1 统一认证链路设计

## 背景

当前项目存在两套并行认证链路：

- `apps/web` 在 Next 侧自行生成并验证 `skillhub_session` cookie
- `apps/web` 在转发后端请求时向 `apps/api` 注入 `x-demo-email`、`x-demo-role`、`x-demo-name`
- `apps/api` 的 `get_current_user()` 直接信任这些请求头，并在数据库中自动创建或更新用户

这导致前端可以自行构造用户身份，后端没有独立认证真相源。对于 P0 级问题，这属于必须优先修复的鉴权缺陷。

## 目标

- 将认证真相源统一收敛到 `apps/api`
- 保留当前 mock 登录体验，不在本次扩展为真实验证码系统
- 删除 `x-demo-*` 伪鉴权链路
- 让所有依赖 `get_current_user()` 的 API 统一改为 Bearer token 认证
- 保持前端现有页面与业务调用方式尽量不变

## 非目标

- 不接入真实短信或邮件验证码发送能力
- 不引入刷新 token、续签机制或完整会话管理
- 不在本次重写前端登录页交互
- 不在 Edge middleware 中实现完整 JWT 解码校验

## 已确认事实

- 后端已具备 `jwt_secret`、`jwt_expire_minutes` 配置
- 后端依赖中已包含 `python-jose[cryptography]`
- 前端当前的 `_session.ts` 使用本地 secret 自行签名 `user + exp`
- 前端代理层 `api-proxy.ts` 当前依赖 cookie 中的用户信息并向后端发送 `x-demo-*`
- 后端 `auth.py` 当前仍返回 `mock-jwt-token` 和固定用户信息

## 设计原则

- 后端签发，后端校验，前端只存储和转发
- 仅修复认证链路，不顺手扩大到真实登录系统
- 优先保持前端业务接口与页面调用面稳定
- 用最小改动完成 P0 闭环，避免引入不必要重构

## 方案选择

本次采用以下方案：

- `apps/api` 负责 mock 验证码校验、用户落库、JWT 签发、JWT 解码和当前用户识别
- `apps/web` 不再自行生成可表达用户身份的 session token，只存储后端签发的 `access_token`
- `apps/web` 在请求后端时统一注入 `Authorization: Bearer <token>`

不采用以下方案：

- 不采用后端 session 表方案，因为会引入额外状态管理与清理逻辑，超出本次最小修复范围
- 不采用前后端共享同一前端 session 签名方案，因为认证签发仍由前端参与，不满足本次统一认证目标

## 架构设计

### 后端认证源

`apps/api` 成为唯一认证真相源。

职责包括：

- 校验 mock 验证码
- 创建或更新用户记录
- 使用后端 secret 签发 JWT
- 从 Bearer token 中识别当前用户
- 对 token 非法、过期、缺失等情况统一返回 `401`

### 前端认证适配层

`apps/web` 只承担认证适配职责。

职责包括：

- 调用后端登录接口
- 将后端签发的 `access_token` 保存为 `httpOnly` cookie
- 在 Next API 路由或代理层读取 token 并转发给后端
- 不再本地验签用户身份，不再生成可冒充用户的身份头

## 组件改动

### `apps/api/app/api/v1/auth.py`

需要完成以下改造：

- `/auth/send-code` 继续保留 mock 行为，作为当前演示链路的兼容入口
- `/auth/verify`
  - 继续接受 `email`、`code`、`role`
  - 仅校验固定验证码，例如当前的 `123456`
  - 验证通过后按邮箱查找用户
  - 用户不存在则创建，存在则按当前登录信息更新 `role` 和 `display_name`
  - 签发真实 JWT，并返回 `access_token`、`token_type`、`user`
- `/auth/me`
  - 从 `Authorization` 头提取 Bearer token
  - 解码 token 后识别用户
  - 返回数据库中的当前用户信息，而不是固定 mock 数据

### `apps/api/app/deps.py`

`get_current_user()` 改为：

- 删除 `x_demo_email`、`x_demo_role`、`x_demo_name` 三个 Header 参数
- 改为读取标准 `Authorization` 头
- 严格要求 Bearer token 存在且合法
- 解码 JWT 后按用户标识查询数据库
- 当 token 缺失、格式错误、解码失败、用户不存在时，统一抛出 `401`

### `apps/web/src/app/api/auth/verify/route.ts`

需要改为：

- 接收当前前端登录参数
- 转发到后端 `/auth/verify`
- 获取后端返回的 `access_token` 和 `user`
- 将 `access_token` 写入 `httpOnly` cookie
- 将用户信息返回给前端页面层

### `apps/web/src/app/api/auth/me/route.ts`

需要改为：

- 从 cookie 读取 `access_token`
- 通过 Bearer token 请求后端 `/auth/me`
- 将后端识别结果返回给前端
- 不再本地解析 cookie 内容判断用户身份

### `apps/web/src/lib/api-proxy.ts`

需要改为：

- 从 cookie 中读取 `access_token`
- 当 token 缺失时直接返回 `401`
- 将 `Authorization: Bearer <token>` 转发给后端
- 删除所有 `x-demo-*` 头注入逻辑

### `apps/web/src/app/api/auth/_session.ts`

需要收敛为最小能力：

- 仅保留 cookie 名称等简单常量工具，或在实现时直接删除并迁移为更轻量的 token cookie 工具
- 删除本地 session token 的签名与验签逻辑
- 删除 `SessionUser` 和 `SessionPayload` 这类前端自行定义的认证真相结构

### `apps/web/src/lib/demo-user.ts`

该文件不再符合设计目标。

处理方式：

- 删除该 helper，或改造成仅返回原始 token 的轻量工具
- 不再提供“从前端 cookie 里解出用户”的能力

## 请求流转

### 登录

1. 用户在前端提交邮箱、验证码、角色
2. `apps/web` 的 `/api/auth/verify` 调用 `apps/api` 的 `/auth/verify`
3. 后端校验 mock 验证码
4. 后端创建或更新用户并签发 JWT
5. 前端将后端返回的 `access_token` 保存到 `httpOnly` cookie
6. 前端页面收到用户信息并进入已登录状态

### 获取当前用户

1. 前端调用 `/api/auth/me`
2. Next 路由从 cookie 读取 `access_token`
3. Next 路由带着 Bearer token 请求后端 `/auth/me`
4. 后端完成 token 校验并返回当前用户
5. 前端以该结果作为唯一用户信息来源

### 业务接口访问

1. 前端页面调用 Next 侧 `/api/*`
2. `proxyToApi()` 从 cookie 读取 `access_token`
3. `proxyToApi()` 统一注入 `Authorization: Bearer <token>`
4. 后端业务接口通过 `get_current_user()` 获取当前用户

## 错误处理

- 登录缺少邮箱或验证码时，返回 `400`
- 验证码错误时，返回 `401`
- token 缺失时，`/api/auth/me` 和代理接口返回 `401`
- token 非法、过期或解码失败时，后端统一返回 `401`
- token 对应用户不存在时，后端统一返回 `401`
- 后端不可达时，前端代理层继续返回当前已有的 `502/503` 级错误提示

## Middleware 策略

本次保持最小策略：

- `middleware.ts` 仅检查认证 cookie 是否存在
- 有 cookie 则放行
- 无 cookie 则跳转登录页
- 不在 Edge 层实现 JWT 解码与完整鉴权

这样可以保证本次重点放在移除伪鉴权和统一认证真相源，而不把范围扩大到前端运行时兼容问题。

## 数据与兼容性

- 用户表继续沿用现有 `email`、`role`、`display_name` 结构
- 继续允许同一邮箱以不同角色登录时更新角色字段，保持当前演示行为
- 现有依赖 `get_current_user()` 的接口无需改变业务逻辑，只变更认证来源

## 验收标准

- 手工构造 `x-demo-*` 头无法再冒充任意用户访问后端接口
- 前端 cookie 中不再存放可由前端自行签发的完整用户身份信息
- `/api/auth/me` 返回的用户信息来自后端鉴权结果
- `chat`、`skills`、`tasks` 等接口在登录后仍可正常访问
- 未登录、token 非法、token 过期时，上述接口返回 `401`

## 测试与验证

实现完成后至少验证以下内容：

- 后端认证接口的最小冒烟验证
  - `/auth/verify` 正确签发 token
  - `/auth/me` 正确识别 token
- 前端认证路由验证
  - `/api/auth/verify` 能写入 cookie
  - `/api/auth/me` 能透传后端用户信息
- 业务代理验证
  - `proxyToApi()` 不再注入 `x-demo-*`
  - 已登录状态下可访问受保护接口
  - 未登录状态下返回 `401`
- 回归验证
  - 登录页和仪表盘页基础跳转正常
  - `middleware` 仍能在无 cookie 时重定向到 `/login`

## 风险与缓解

风险：

- 前端当前部分逻辑可能默认信任本地解析出的用户对象，改造后需要统一改为以后端结果为准
- 若 JWT payload 设计不稳妥，可能导致 `get_current_user()` 与 `/auth/me` 出现不一致
- `middleware` 只检查 cookie 存在，理论上非法 token 仍可能先通过页面路由保护，但会在真正请求 API 时被后端拦截

缓解：

- 将用户信息真相统一收口到后端 `/auth/me`
- 让所有业务 API 只依赖同一个 `get_current_user()` 路径
- 将前端 `middleware` 继续定位为轻门禁，而不是安全边界

## 产出

本次设计对应的实现产出应包括：

- 一套由后端统一签发与校验的 JWT 认证链路
- 前端基于 `httpOnly` cookie 的 token 存储与透传
- 删除 `x-demo-*` 伪鉴权实现
- 保持 mock 登录体验不变的最小可运行认证闭环
