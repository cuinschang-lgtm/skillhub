import { NextResponse } from "next/server";

import { getDemoUserFromCookies } from "@/lib/demo-user";


const API_BASE = process.env.SKILLHUB_API_BASE_URL || "http://127.0.0.1:8000";


export async function proxyToApi(path: string, init: RequestInit = {}) {
  const user = await getDemoUserFromCookies();
  if (!user) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  }

  const headers = new Headers(init.headers);
  headers.set("x-demo-email", user.email);
  headers.set("x-demo-role", user.role);
  headers.set("x-demo-name", user.displayName);

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

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
