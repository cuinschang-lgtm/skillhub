import { proxyToApi } from "@/lib/api-proxy";

export async function GET() {
  return proxyToApi("/api/v1/settings/profile");
}

export async function PATCH(request: Request) {
  return proxyToApi("/api/v1/settings/profile", {
    method: "PATCH",
    headers: {
      "content-type": "application/json",
    },
    body: await request.text(),
  });
}
