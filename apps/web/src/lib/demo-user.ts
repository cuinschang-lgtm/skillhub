import { cookies } from "next/headers";

import { getCookieName, verifySessionToken } from "@/app/api/auth/_session";


export async function getDemoUserFromCookies() {
  const jar = await cookies();
  const token = jar.get(getCookieName())?.value || "";
  if (!token) return null;
  const payload = verifySessionToken(token);
  return payload?.user ?? null;
}
