import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getCookieName } from "../_session";

export async function POST() {
  const jar = await cookies();
  jar.set(getCookieName(), "", {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
  return NextResponse.json({ ok: true });
}

