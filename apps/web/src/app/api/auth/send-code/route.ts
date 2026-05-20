import { NextResponse } from "next/server";

const FIXED_CODE = "123456";

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as { email?: string } | null;
  const email = (body?.email || "").trim().toLowerCase();
  if (!email) {
    return NextResponse.json({ message: "请输入邮箱" }, { status: 400 });
  }
  return NextResponse.json({ message: `演示环境不发邮件，验证码固定为 ${FIXED_CODE}` });
}

