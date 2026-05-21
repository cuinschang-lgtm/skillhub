import { proxyToApi } from "@/lib/api-proxy";


export async function GET(
  _req: Request,
  { params }: { params: Promise<{ skillId: string }> },
) {
  const { skillId } = await params;
  return proxyToApi(`/api/v1/skills/${skillId}/benchmark`, { method: "GET" });
}
