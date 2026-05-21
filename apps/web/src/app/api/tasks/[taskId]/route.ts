import { proxyToApi } from "@/lib/api-proxy";


export async function GET(
  _req: Request,
  { params }: { params: Promise<{ taskId: string }> },
) {
  const { taskId } = await params;
  return proxyToApi(`/api/v1/tasks/${taskId}`, { method: "GET" });
}


export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ taskId: string }> },
) {
  const { taskId } = await params;
  return proxyToApi(`/api/v1/tasks/${taskId}`, { method: "DELETE" });
}
