"use client";

import { useEffect, useState } from "react";

import { getTask } from "@/lib/api-client/tasks";
import type { TaskDetail } from "@/types/task";

type TaskState = {
  task: TaskDetail | null;
  loading: boolean;
  error: string;
};

type UseTaskOptions = {
  pollInterval?: number;
};

export function useTask(taskId: string, options?: UseTaskOptions) {
  const pollInterval = options?.pollInterval ?? 3000;
  const [state, setState] = useState<TaskState>({
    task: null,
    loading: true,
    error: "",
  });

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const task = await getTask(taskId);
        if (!cancelled) {
          setState({ task, loading: false, error: "" });
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            task: null,
            loading: false,
            error: error instanceof Error ? error.message : "任务不存在或已失效",
          });
        }
      }
    };

    void load();
    const timer = setInterval(() => {
      void load();
    }, pollInterval);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [pollInterval, taskId]);

  return state;
}
