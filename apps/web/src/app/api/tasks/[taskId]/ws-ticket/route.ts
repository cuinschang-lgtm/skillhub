import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { getCookieName } from "@/app/api/auth/_session";
import { getApiBaseUrl } from "@/lib/api-proxy";

const API_BASE = getApiBaseUrl();
const IS_LOCAL_API = API_BASE.includes("127.0.0.1") || API_BASE.includes("localhost");

type ApiWsTicketResponse = {
  token?: string;
  expires_in?: number;
  detail?: string;
  message?: string;
};

function isPrivateOrContainerHost(hostname: string) {
  const lowerHostname = hostname.toLowerCase();

  if (lowerHostname === "localhost" || lowerHostname.endsWith(".local")) {
    return true;
  }

  if (/^\d+\.\d+\.\d+\.\d+$/.test(lowerHostname)) {
    const octets = lowerHostname.split(".").map(Number);
    if (octets[0] === 10 || octets[0] === 127) {
      return true;
    }
    if (octets[0] === 192 && octets[1] === 168) {
      return true;
    }
    if (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31) {
      return true;
    }
    return false;
  }

  // A bare internal service name like `api` is only resolvable inside the container network.
  return !lowerHostname.includes(".");
}

function buildWebSocketUrl(taskId: string, token: string) {
  const upstream = new URL(API_BASE);
  upstream.protocol = upstream.protocol === "https:" ? "wss:" : "ws:";
  upstream.pathname = `/ws/progress/${taskId}`;
  upstream.search = `token=${encodeURIComponent(token)}`;
  return upstream.toString();
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ taskId: string }> },
) {
  const { taskId } = await params;
  const jar = await cookies();
  const token = jar.get(getCookieName())?.value || "";
  if (!token) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  }

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

  const upstream = new URL(API_BASE);
  if (isPrivateOrContainerHost(upstream.hostname)) {
    return NextResponse.json(
      {
        message:
          "当前后端地址仅适合服务端代理，浏览器无法直连实时进度通道。请配置 SKILLHUB_API_BASE_URL 为浏览器可访问的公网地址，或继续使用轮询进度。",
      },
      { status: 503 },
    );
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/tasks/${taskId}/ws-ticket`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
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

  const payload = (await response.json().catch(() => null)) as ApiWsTicketResponse | null;
  if (!response.ok || !payload?.token || !payload.expires_in) {
    const nextResponse = NextResponse.json(
      { message: payload?.detail || payload?.message || "获取实时连接凭证失败" },
      { status: response.status || 502 },
    );
    if (response.status === 401) {
      nextResponse.cookies.set(getCookieName(), "", {
        httpOnly: true,
        sameSite: "lax",
        secure: process.env.NODE_ENV === "production",
        path: "/",
        maxAge: 0,
      });
    }
    return nextResponse;
  }

  return NextResponse.json({
    url: buildWebSocketUrl(taskId, payload.token),
    expires_in: payload.expires_in,
  });
}
