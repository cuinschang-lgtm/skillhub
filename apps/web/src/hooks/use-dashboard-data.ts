"use client";

import { useEffect, useState } from "react";

import { listSkills } from "@/lib/api-client/skills";
import { listTasks } from "@/lib/api-client/tasks";
import type { SkillSummary } from "@/types/skill";
import type { TaskSummary } from "@/types/task";

type DashboardDataState = {
  tasks: TaskSummary[];
  skills: SkillSummary[];
  loading: boolean;
  error: string;
};

export function useDashboardData() {
  const [state, setState] = useState<DashboardDataState>({
    tasks: [],
    skills: [],
    loading: true,
    error: "",
  });

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const [tasks, skills] = await Promise.all([
          listTasks(),
          listSkills({ pageSize: 4 }),
        ]);
        if (!cancelled) {
          setState({ tasks, skills, loading: false, error: "" });
        }
      } catch (error) {
        if (!cancelled) {
          setState((current) => ({
            ...current,
            loading: false,
            error: error instanceof Error ? error.message : "加载失败",
          }));
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
