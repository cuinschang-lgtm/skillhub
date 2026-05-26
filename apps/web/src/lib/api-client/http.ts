export class ApiClientError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
  }
}

type ErrorPayload = {
  detail?: string;
  message?: string;
};

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }
  const candidate = payload as ErrorPayload;
  return candidate.detail || candidate.message || fallback;
}

export async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    cache: "no-store",
    ...init,
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiClientError(
      extractErrorMessage(payload, `请求失败 (${response.status})`),
      response.status,
    );
  }

  return payload as T;
}
