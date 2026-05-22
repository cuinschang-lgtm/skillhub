import { proxyToApi } from "@/lib/api-proxy";


export async function POST(req: Request) {
  const payload = await req.json();
  return proxyToApi("/api/v1/chat", {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}
