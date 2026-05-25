import { NextResponse } from "next/server";

import { getApiBaseUrl } from "@/lib/api-proxy";

const API_BASE = getApiBaseUrl();
const IS_LOCAL_API = API_BASE.includes("127.0.0.1") || API_BASE.includes("localhost");

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as { email?: string } | null;
  const email = (body?.email || "").trim().toLowerCase();
  if (!email) {
    return NextResponse.json({ message: "请输入邮箱" }, { status: 400 });
  }

  if (process.env.NODE_ENV === "production" && IS_LOCAL_API) {
    return NextResponse.json(
      {
        message:
          "服务器未配置后端 API 地址。请在部署平台设置 SKILLHUB_API_BASE_URL 指向公网后端服务。",
      },
      { status: 503 },
    );
  }

  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/send-code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify({ email }),
    });
    const payload = (await response.json().catch(() => null)) as { message?: string; detail?: string } | null;
    if (!response.ok) {
      return NextResponse.json(
        { message: payload?.detail || payload?.message || "发送失败" },
        { status: response.status },
      );
    }
    return NextResponse.json(payload ?? { message: "验证码已发送" }, { status: response.status });
  } catch (error) {
    const detail = error instanceof Error && error.message ? error.message : "unknown upstream error";
    return NextResponse.json(
      {
        message:
          "连接后端服务失败。请检查 SKILLHUB_API_BASE_URL 是否可访问，或确认后端服务正在运行。",
        detail,
      },
      { status: 502 },
    );
  }
}
