import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { createSessionToken, getCookieName, type SessionUser } from "../_session";

const FIXED_CODE = "123456";

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
  if (code !== FIXED_CODE) return NextResponse.json({ message: "验证码错误" }, { status: 401 });

  const user: SessionUser = {
    email,
    role,
    displayName: email.split("@")[0] || email,
  };

  const ttlSeconds = remember ? 60 * 60 * 24 * 30 : 60 * 60 * 24;
  const token = createSessionToken(user, ttlSeconds);

  const jar = await cookies();
  jar.set(getCookieName(), token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: ttlSeconds,
  });

  return NextResponse.json({ user });
}

