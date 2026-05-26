# SkillHub Web

这是 SkillHub 的 Next.js 前端应用。

完整部署说明请看：

- [../../docs/deploy-skillhub.md](../../docs/deploy-skillhub.md)

## 本地开发

在仓库根目录先准备环境变量：

```bash
cp .env.example .env
```

然后启动前端：

```bash
cd apps/web
npm ci
npm run dev
```

默认访问地址：

- Web: `http://127.0.0.1:3000`

默认情况下，前端会通过以下变量定位后端：

- `SKILLHUB_API_BASE_URL`
- 或 `SKILLHUB_API_HOSTPORT`

若两者都未提供，默认回退到：

- `http://127.0.0.1:8000`

## 说明

- 浏览器只访问站内 `/api/*`
- Next Route Handler 会在服务端转发到后端 API
- 认证 cookie、Bearer token 透传和上游错误处理都在前端代理层完成

相关文件：

- [src/lib/api-proxy.ts](src/lib/api-proxy.ts)
- [../../render.yaml](../../render.yaml)
