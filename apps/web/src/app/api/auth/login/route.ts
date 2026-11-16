import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getApiBaseUrl } from "@/lib/api-proxy";
import { getCookieName } from "../_session";

const API_BASE = getApiBaseUrl();

type ApiUser = {
  email: string;
  role: "teacher" | "student";
  display_name?: string;
};

type TokenResponse = {
  access_token: string;
  expires_in: number;
  user: ApiUser;
};

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as
    | { email?: string; password?: string; remember?: boolean }
    | null;

  const email = (body?.email || "").trim().toLowerCase();
  const password = body?.password || "";
  const remember = Boolean(body?.remember);

  if (!email) return NextResponse.json({ message: "请输入邮箱" }, { status: 400 });
  if (!password) return NextResponse.json({ message: "请输入密码" }, { status: 400 });

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify({ email, password }),
    });
  } catch (error) {
    const detail = error instanceof Error && error.message ? error.message : "unknown upstream error";
    return NextResponse.json(
      {
        message: "连接后端服务失败。请检查 SKILLHUB_API_BASE_URL 是否可访问，或确认后端服务正在运行。",
        detail,
      },
      { status: 502 },
    );
  }

  const payload = (await response.json().catch(() => null)) as
    | (TokenResponse & { detail?: string; message?: string })
    | null;
  if (!response.ok) {
    return NextResponse.json(
      { message: payload?.detail || payload?.message || "邮箱或密码错误" },
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
    maxAge: remember ? payload.expires_in : Math.min(payload.expires_in, 60 * 60 * 24),
  });

  return NextResponse.json({
    user: {
      email: payload.user.email,
      role: payload.user.role,
      displayName: payload.user.display_name || payload.user.email.split("@")[0] || payload.user.email,
    },
  });
}
