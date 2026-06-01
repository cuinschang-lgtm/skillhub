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

export async function GET() {
  const jar = await cookies();
  const token = jar.get(getCookieName())?.value || "";
  if (!token) return NextResponse.json({ user: null }, { status: 401 });

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

  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    const payload = (await response.json().catch(() => null)) as
      | (ApiUser & { detail?: string; message?: string })
      | null;

    if (!response.ok || !payload?.email) {
      if (response.status === 401) {
        jar.set(getCookieName(), "", {
          httpOnly: true,
          sameSite: "lax",
          secure: process.env.NODE_ENV === "production",
          path: "/",
          maxAge: 0,
        });
      }
      return NextResponse.json({ user: null, message: payload?.detail || payload?.message }, { status: response.status });
    }

    return NextResponse.json({
      user: {
        email: payload.email,
        role: payload.role,
        displayName: payload.display_name || payload.email.split("@")[0] || payload.email,
      },
    });
  } catch (error) {
    const detail = error instanceof Error && error.message ? error.message : "unknown upstream error";
    return NextResponse.json(
      {
        user: null,
        message:
          "连接后端服务失败。请检查 SKILLHUB_API_BASE_URL 是否可访问，或确认后端服务正在运行。",
        detail,
      },
      { status: 502 },
    );
  }
}
