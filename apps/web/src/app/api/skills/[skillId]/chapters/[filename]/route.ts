import { proxyToApi } from "@/lib/api-proxy";


export async function GET(
  _req: Request,
  { params }: { params: Promise<{ skillId: string; filename: string }> },
) {
  const { skillId, filename } = await params;
  return proxyToApi(`/api/v1/skills/${skillId}/chapters/${filename}`, { method: "GET" });
}
