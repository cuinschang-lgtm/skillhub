import { getJson } from "@/lib/api-client/http";
import type {
  BenchmarkResult,
  SkillDetail,
  SkillListResponse,
  SkillSummary,
} from "@/types/skill";

export async function listSkills(params?: {
  search?: string;
  pageSize?: number;
}): Promise<SkillSummary[]> {
  const searchParams = new URLSearchParams();
  if (params?.search) {
    searchParams.set("search", params.search);
  }
  if (params?.pageSize) {
    searchParams.set("page_size", String(params.pageSize));
  }

  const query = searchParams.toString();
  const payload = await getJson<SkillListResponse>(
    query ? `/api/skills?${query}` : "/api/skills",
  );
  return payload.items ?? [];
}

export async function getSkillDetail(skillId: string): Promise<SkillDetail> {
  return getJson<SkillDetail>(`/api/skills/${skillId}`);
}

export async function getBenchmark(skillId: string): Promise<BenchmarkResult> {
  return getJson<BenchmarkResult>(`/api/skills/${skillId}/benchmark`);
}
