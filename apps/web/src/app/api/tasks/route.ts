import { proxyToApi } from "@/lib/api-proxy";


export async function GET() {
  return proxyToApi("/api/v1/tasks", { method: "GET" });
}


export async function POST(req: Request) {
  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  return proxyToApi("/api/v1/tasks", {
    method: "POST",
    headers,
    body: req.body,
  });
}
