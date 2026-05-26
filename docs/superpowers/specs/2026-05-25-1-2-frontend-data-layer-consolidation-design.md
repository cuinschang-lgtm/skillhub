# SkillHub 1-2 前端结构与数据获取模式收敛设计

## 背景

当前前端已经可用，但数据获取模式分散在页面中，表现为大量重复的：

- `useState + useEffect + fetch`
- 内联类型定义
- 页面内手写错误与空态处理

典型页面包括：

- `dashboard`
- `knowledge`
- `benchmark/[skillId]`
- `progress/[taskId]`
- `chat`
- `upload`

其中查询型页面（前四者）的数据获取模式高度一致，最适合作为第一阶段收敛对象。

## 目标

- 建立最小可用的前端数据层分层：`types`、`api-client`、`hooks`
- 先收敛查询型页面，减少重复 `fetch` 与内联类型
- 保持现有 UI 行为不变，避免大规模交互重写
- 为后续 `2-1`（debounce、会话、settings 接口）留出稳定基础层

## 非目标

- 不在本次引入 React Query/SWR
- 不在本次重构 `chat` 发送消息流程
- 不在本次重构 `upload` 提交任务流程
- 不在本次更改后端 API 契约
- 不在本次调整页面视觉样式

## 已确认事实

- 浏览器侧数据请求都走站内 `/api/*`，再由 Next Route Handler 转发到 API
- `api-proxy` 已经是服务端统一入口，不需要在本次改动
- 页面层存在较多重复类型和重复请求逻辑
- 目前缺少统一的 `types`、`api-client`、`hooks` 目录

## 设计原则

- 先收敛，再优化：优先统一结构，不追求一次性重构所有页面
- 查询优先：先处理读取型逻辑，再处理提交型逻辑
- 行为等价：迁移后页面行为应与当前保持一致
- 最小侵入：不改路由、不改后端、不改展示结构

## 方案选择

本次采用以下方案：

- 新增 `src/types/*` 统一承载查询型页面的数据类型
- 新增 `src/lib/api-client/*` 统一封装浏览器侧 `/api/*` 请求
- 新增 `src/hooks/*` 统一封装查询型页面的数据拉取和状态管理
- 迁移 4 个查询型页面：
  - `dashboard`
  - `knowledge`
  - `benchmark/[skillId]`
  - `progress/[taskId]`

不采用以下方案：

- 不一次性迁移 `chat` 和 `upload` 的提交逻辑
- 不直接引入新的状态管理库
- 不把收敛范围扩大到整个前端目录

## 分层设计

### Types 层

新增目录：

- `apps/web/src/types`

首批文件建议：

- `task.ts`
- `skill.ts`
- `chat.ts`（先建类型，不迁移发送逻辑）

目标：

- 把页面内联类型外移
- 消除同名类型在不同页面重复定义

### API Client 层

新增目录：

- `apps/web/src/lib/api-client`

首批模块建议：

- `tasks.ts`
- `skills.ts`
- `chat.ts`（先用于读取相关类型，发送逻辑可后续迁移）

目标：

- 页面不再直接写 `fetch("/api/...")`
- 统一请求、响应解析、错误提取
- 保留“只请求站内 `/api/*`”原则

### Hooks 层

新增目录：

- `apps/web/src/hooks`

首批 hooks 建议：

- `useDashboardData()`
- `useSkills(search)`
- `useBenchmark(skillId)`
- `useTask(taskId, { pollInterval })`

目标：

- 把查询状态（loading/error/data）和取消逻辑从页面抽离
- 页面只保留展示和交互拼装

## 页面迁移范围

### 第一阶段（本次）

- `dashboard/page.tsx`
- `knowledge/page.tsx`
- `benchmark/[skillId]/page.tsx`
- `progress/[taskId]/page.tsx`

迁移内容：

- 使用 `types` 替代页面内联类型
- 使用 `api-client` 替代页面内手写 fetch
- 使用 `hooks` 承载读取状态逻辑

### 第二阶段（后续）

- `chat/page.tsx`：主要是发送消息与会话管理逻辑
- `upload/page.tsx`：主要是提交任务与文件校验逻辑

## 错误处理与状态统一

本次收敛里，hooks 统一输出：

- `data`
- `loading`
- `error`

并统一约定：

- 非 `2xx` 响应优先读取 `detail/message`
- 网络错误返回统一文案
- 查询 hooks 保持可取消与安全卸载（避免 setState on unmounted）

## 目录结构目标

本次完成后，前端至少应新增：

- `apps/web/src/types/*`
- `apps/web/src/lib/api-client/*`
- `apps/web/src/hooks/*`

并让上述四个查询型页面不再内联大段请求逻辑。

## 验收标准

- 四个查询型页面不再直接写原始 `fetch("/api/...")`
- 页面内联查询类型明显减少，改为引用 `src/types/*`
- 查询逻辑统一经由 `api-client + hooks`
- 页面展示行为与当前一致：
  - dashboard 仍显示最近任务与 skill 摘要
  - knowledge 仍支持按关键词筛选
  - benchmark 仍并发拉 skill 与 benchmark 数据
  - progress 仍可轮询任务状态并自动跳转结果页

## 测试与验证

实现后至少验证：

- `npm run lint` 通过
- 四个页面可正常打开且数据加载无回归
- knowledge 搜索、progress 轮询、benchmark 双接口加载行为保持
- 关键错误态仍可展示（接口失败、网络失败）

## 风险与缓解

风险：

- hooks 抽离不当可能改变页面加载时机
- 类型统一时可能遗漏字段导致 UI 回归
- progress 轮询迁移后可能出现定时器泄漏

缓解：

- 保持每页“先替换实现、后校验行为”的迁移节奏
- 在 hooks 层显式保留轮询清理逻辑
- 优先迁移查询逻辑，不触碰提交逻辑

## 后续衔接

`1-2` 第一阶段完成后，更容易继续推进：

- `2-1` 搜索 debounce（可直接加在 `useSkills`）
- 聊天会话切换（在 `chat` hooks 层扩展）
- settings 页面真实数据接入（复用 api-client/hook 模式）

## 产出

本次设计对应的实现产出应包括：

- 一组基础 `types / api-client / hooks`
- 四个查询型页面的最小迁移
- 一份行为保持不变的前端数据层收敛结果
