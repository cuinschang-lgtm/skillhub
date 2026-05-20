import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getCookieName, verifySessionToken } from "../_session";

export async function GET() {
  const jar = await cookies();
  const token = jar.get(getCookieName())?.value || "";
  if (!token) return NextResponse.json({ user: null }, { status: 401 });
  const payload = verifySessionToken(token);
  if (!payload) return NextResponse.json({ user: null }, { status: 401 });
  return NextResponse.json({ user: payload.user });
}

