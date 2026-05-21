import { proxyToApi } from "@/lib/api-proxy";


export async function GET(req: Request) {
  const url = new URL(req.url);
  const qs = url.searchParams.toString();
  const suffix = qs ? `?${qs}` : "";
  return proxyToApi(`/api/v1/skills${suffix}`, { method: "GET" });
}
