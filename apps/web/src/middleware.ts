import { NextResponse, type NextRequest } from "next/server";

const COOKIE_NAME = "skillhub_session";

export function middleware(req: NextRequest) {
  const token = req.cookies.get(COOKIE_NAME)?.value;
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

