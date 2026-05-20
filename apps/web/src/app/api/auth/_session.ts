import crypto from "crypto";

export type SessionUser = {
  email: string;
  role: "teacher" | "student";
  displayName: string;
};

type SessionPayload = {
  user: SessionUser;
  exp: number;
};

const COOKIE_NAME = "skillhub_session";

export function getCookieName() {
  return COOKIE_NAME;
}

function getSecret() {
  return process.env.SKILLHUB_SESSION_SECRET || "dev-secret-change-in-production";
}

function base64UrlEncode(input: string) {
  return Buffer.from(input, "utf8").toString("base64url");
}

function base64UrlDecode(input: string) {
  return Buffer.from(input, "base64url").toString("utf8");
}

function sign(payloadB64: string) {
  return crypto.createHmac("sha256", getSecret()).update(payloadB64).digest("base64url");
}

export function createSessionToken(user: SessionUser, ttlSeconds: number) {
  const payload: SessionPayload = {
    user,
    exp: Math.floor(Date.now() / 1000) + ttlSeconds,
  };
  const payloadB64 = base64UrlEncode(JSON.stringify(payload));
  const sig = sign(payloadB64);
  return `${payloadB64}.${sig}`;
}

export function verifySessionToken(token: string): SessionPayload | null {
  const [payloadB64, sig] = token.split(".", 2);
  if (!payloadB64 || !sig) return null;
  if (sign(payloadB64) !== sig) return null;
  let payload: SessionPayload;
  try {
    payload = JSON.parse(base64UrlDecode(payloadB64)) as SessionPayload;
  } catch {
    return null;
  }
  if (!payload?.user?.email || !payload?.exp) return null;
  if (payload.exp < Math.floor(Date.now() / 1000)) return null;
  return payload;
}

