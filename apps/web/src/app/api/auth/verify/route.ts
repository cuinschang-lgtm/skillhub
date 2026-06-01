import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getApiBaseUrl } from "@/lib/api-proxy";
import { getCookieName } from "../_session";

const API_BASE = getApiBaseUrl();
const IS_LOCAL_API = API_BASE.includes("127.0.0.1") || API_BASE.includes("localhost");

type ApiUser = {
  email: string;
  role: "teacher" | "student";
  display_name?: string;
};

type VerifyResponse = {
  access_token: string;
  expires_in: number;
  user: ApiUser;
};

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as
    | { email?: string; code?: string; role?: "teacher" | "student"; remember?: boolean }
    | null;

  const email = (body?.email || "").trim().toLowerCase();
  const code = (body?.code || "").trim();
  const role = body?.role === "teacher" ? "teacher" : "student";
  const remember = Boolean(body?.remember);

  if (!email) return NextResponse.json({ message: "请输入邮箱" }, { status: 400 });
  if (!code) return NextResponse.json({ message: "请输入验证码" }, { status: 400 });

  const isExplicitlyConfigured = Boolean(
    process.env.SKILLHUB_API_BASE_URL || process.env.SKILLHUB_API_HOSTPORT,
  );
  if (process.env.NODE_ENV === "production" && IS_LOCAL_API && !isExplicitlyConfigured) {
    return NextResponse.json(
      {
        message:
          "服务器未配置后端 API 地址。请在部署平台设置 SKILLHUB_API_BASE_URL 指向公网后端服务。",
      },
      { status: 503 },
    );
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/auth/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify({ email, code, role, remember }),
    });
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

  const payload = (await response.json().catch(() => null)) as
    | (VerifyResponse & { detail?: string; message?: string })
    | null;
  if (!response.ok) {
    return NextResponse.json(
      { message: payload?.detail || payload?.message || "登录失败" },
      { status: response.status },
    );
  }

  if (!payload?.access_token || !payload?.user) {
    return NextResponse.json({ message: "登录响应无效" }, { status: 502 });
  }

  const jar = await cookies();
  jar.set(getCookieName(), payload.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: payload.expires_in,
  });

  return NextResponse.json({
    user: {
      email: payload.user.email,
      role: payload.user.role,
      displayName: payload.user.display_name || payload.user.email.split("@")[0] || payload.user.email,
    },
  });
}
