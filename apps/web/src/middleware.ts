import { NextResponse, type NextRequest } from "next/server";

import { getCookieName } from "@/app/api/auth/_session";

export function middleware(req: NextRequest) {
  const token = req.cookies.get(getCookieName())?.value;
  if (token) return NextResponse.next();
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.searchParams.set("next", req.nextUrl.pathname);
  return NextResponse.redirect(url);
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
