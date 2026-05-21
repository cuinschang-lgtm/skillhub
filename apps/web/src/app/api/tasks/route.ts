import { proxyToApi } from "@/lib/api-proxy";


export async function GET() {
  return proxyToApi("/api/v1/tasks", { method: "GET" });
}


export async function POST(req: Request) {
  const formData = await req.formData();
  return proxyToApi("/api/v1/tasks", {
    method: "POST",
    body: formData,
  });
}
