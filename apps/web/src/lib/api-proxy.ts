import { NextResponse } from "next/server";

import { getDemoUserFromCookies } from "@/lib/demo-user";


function getConfiguredApiBase() {
  const explicitBase = process.env.SKILLHUB_API_BASE_URL;
  if (explicitBase) {
    return explicitBase;
  }

  const internalHostPort = process.env.SKILLHUB_API_HOSTPORT;
  if (internalHostPort) {
    return `http://${internalHostPort}`;
  }

  return "http://127.0.0.1:8000";
}

const API_BASE = getConfiguredApiBase();
const IS_LOCAL_API =
  API_BASE.includes("127.0.0.1") ||
  API_BASE.includes("localhost");


export async function proxyToApi(path: string, init: RequestInit = {}) {
  const user = await getDemoUserFromCookies();
  if (!user) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
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

  const headers = new Headers(init.headers);
  headers.set("x-demo-email", user.email);
  headers.set("x-demo-role", user.role);
  headers.set("x-demo-name", user.displayName);

  let response: Response;
  try {
    const requestInit: RequestInit & { duplex?: "half" } = {
      ...init,
      headers,
      cache: "no-store",
    };
    if (init.body) {
      requestInit.duplex = "half";
    }
    response = await fetch(`${API_BASE}${path}`, requestInit);
  } catch (error) {
    const detail =
      error instanceof Error && error.message
        ? error.message
        : "unknown upstream error";
    return NextResponse.json(
      {
        message:
          "连接后端服务失败。请检查 SKILLHUB_API_BASE_URL 是否可访问，或确认后端服务正在运行。",
        detail,
      },
      { status: 502 },
    );
  }

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json() : await response.text();

  if (isJson) {
    return NextResponse.json(payload, { status: response.status });
  }

  return new NextResponse(payload, {
    status: response.status,
    headers: { "content-type": contentType || "text/plain; charset=utf-8" },
  });
}


export function getApiBaseUrl() {
  return API_BASE;
}
