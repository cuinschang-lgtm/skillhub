import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as { email?: string } | null;
  const email = (body?.email || "").trim().toLowerCase();
  if (!email) {
    return NextResponse.json({ message: "请输入邮箱" }, { status: 400 });
  }
  return NextResponse.json({ message: "验证码已发送" });
}

