import { NextResponse, type NextRequest } from "next/server";

import { getCookieName } from "@/app/api/auth/_session";

/** JWT 格式与过期检查（不验签，真实鉴权由后端强制）；无效时清除 cookie 引导重新登录 */
function isPlausiblyValidToken(token: string): boolean {
  const parts = token.split(".");
  if (parts.length !== 3) return false;
  try {
    const payload = JSON.parse(Buffer.from(parts[1], "base64url").toString("utf8")) as {
      exp?: number;
      type?: string;
    };
    if (payload.type && payload.type !== "access") return false;
    return typeof payload.exp === "number" && payload.exp >= Math.floor(Date.now() / 1000);
  } catch {
    return false;
  }
}

export function middleware(req: NextRequest) {
  const token = req.cookies.get(getCookieName())?.value;
  if (token && isPlausiblyValidToken(token)) return NextResponse.next();

  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.searchParams.set("next", req.nextUrl.pathname);
  const res = NextResponse.redirect(url);
  if (token) res.cookies.delete(getCookieName());
  return res;
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/knowledge/:path*",
    "/chat/:path*",
    "/upload/:path*",
    "/settings/:path*",
    "/progress/:path*",
    "/benchmark/:path*",
  ],
};
