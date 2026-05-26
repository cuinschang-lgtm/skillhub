import { getJson } from "@/lib/api-client/http";
import type { TaskDetail, TaskListResponse, TaskSummary } from "@/types/task";

export async function listTasks(): Promise<TaskSummary[]> {
  const payload = await getJson<TaskListResponse>("/api/tasks");
  return payload.items ?? [];
}

export async function getTask(taskId: string): Promise<TaskDetail> {
  return getJson<TaskDetail>(`/api/tasks/${taskId}`);
}
