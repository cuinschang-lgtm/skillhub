"use client";

import { useEffect, useState } from "react";

import { ApiClientError } from "@/lib/api-client/http";
import { getTask, getTaskProgressTicket } from "@/lib/api-client/tasks";
import type { TaskDetail, TaskProgressEvent, TaskStatus } from "@/types/task";

type TaskState = {
  task: TaskDetail | null;
  loading: boolean;
  error: string;
  transport: "connecting" | "realtime" | "polling" | "idle";
  statusMessage: string;
};

type UseTaskOptions = {
  pollInterval?: number;
};

const FINAL_STATUSES = new Set<TaskStatus>(["completed", "failed", "cancelled"]);

function isRetryableTaskError(error: unknown) {
  if (error instanceof ApiClientError) {
    return error.status >= 500;
  }
  return true;
}

function toTaskStatus(status: string, fallback: TaskStatus): TaskStatus {
  if (status === "completed" || status === "failed" || status === "cancelled" || status === "running" || status === "pending") {
    return status;
  }
  return fallback;
}

function applyProgressEvent(task: TaskDetail | null, event: TaskProgressEvent): TaskDetail | null {
  if (!task) {
    return task;
  }

  const nextStatus =
    event.status === "done"
      ? task.status
      : toTaskStatus(event.status || task.status, task.status);

  return {
    ...task,
    status: nextStatus,
    current_stage:
      nextStatus === "completed"
        ? "done"
        : nextStatus === "failed"
          ? "failed"
          : event.stage || task.current_stage,
    progress_pct:
      typeof event.progress === "number"
        ? Math.max(0, Math.min(100, Math.round(event.progress)))
        : task.progress_pct,
    skill_id: event.extra?.skill_id || task.skill_id,
    error_message: nextStatus === "failed" ? event.message || task.error_message : task.error_message,
  };
}

export function useTask(taskId: string, options?: UseTaskOptions) {
  const pollInterval = options?.pollInterval ?? 3000;
  const [state, setState] = useState<TaskState>({
    task: null,
    loading: true,
    error: "",
    transport: "connecting",
    statusMessage: "",
  });

  useEffect(() => {
    let cancelled = false;
    let closedByEffect = false;
    let finished = false;
    let pollTimer: number | undefined;
    let socket: WebSocket | null = null;

    const stopPolling = () => {
      if (pollTimer) {
        window.clearInterval(pollTimer);
        pollTimer = undefined;
      }
    };

    const loadTask = async (): Promise<{ task: TaskDetail | null; retryable: boolean }> => {
      try {
        const task = await getTask(taskId);
        finished = FINAL_STATUSES.has(task.status);
        if (!cancelled) {
          setState((current) => ({
            ...current,
            task,
            loading: false,
            error: "",
            transport: finished ? "idle" : current.transport,
          }));
        }
        return { task, retryable: false };
      } catch (error) {
        if (!cancelled) {
          setState((current) => ({
            ...current,
            loading: false,
            error: error instanceof Error ? error.message : "任务不存在或已失效",
          }));
        }
        return { task: null, retryable: isRetryableTaskError(error) };
      }
    };

    const startPolling = () => {
      if (cancelled || finished || pollTimer) {
        return;
      }
      if (!cancelled) {
        setState((current) => ({
          ...current,
          transport: "polling",
        }));
      }
      void loadTask();
      pollTimer = window.setInterval(() => {
        void loadTask();
      }, pollInterval);
    };

    const connectRealtime = async () => {
      try {
        const ticket = await getTaskProgressTicket(taskId);
        if (cancelled || finished) {
          return;
        }
        socket = new WebSocket(ticket.url);
        socket.onopen = () => {
          if (!cancelled) {
            setState((current) => ({
              ...current,
              transport: "realtime",
            }));
          }
        };
        socket.onmessage = (messageEvent) => {
          try {
            const payload = JSON.parse(messageEvent.data) as TaskProgressEvent;
            let terminalFromMessage = false;
            if (!cancelled) {
              setState((current) => {
                const updatedTask = applyProgressEvent(current.task, payload);
                const updatedStatus = updatedTask?.status;
                terminalFromMessage = Boolean(updatedStatus && FINAL_STATUSES.has(updatedStatus));
                finished = terminalFromMessage;
                return {
                  ...current,
                  task: updatedTask,
                  loading: false,
                  error: "",
                  transport:
                    updatedStatus && FINAL_STATUSES.has(updatedStatus)
                      ? "idle"
                      : "realtime",
                  statusMessage: payload.message || current.statusMessage,
                };
              });
            }
            if (terminalFromMessage) {
              stopPolling();
              socket?.close();
              void loadTask();
            }
          } catch {
            startPolling();
          }
        };
        socket.onerror = () => {
          startPolling();
        };
        socket.onclose = () => {
          if (!closedByEffect) {
            startPolling();
          }
        };
      } catch (error) {
        return isRetryableTaskError(error);
      }
      return true;
    };

    void (async () => {
      const result = await loadTask();
      if (!result || cancelled) {
        return;
      }

      if (!result.task || finished) {
        if (!result.task && result.retryable) {
          startPolling();
        }
        return;
      }

      const realtimeEligible = await connectRealtime();
      if (!realtimeEligible) {
        setState((current) => ({
          ...current,
          transport: "idle",
        }));
      }
    })();

    return () => {
      cancelled = true;
      closedByEffect = true;
      stopPolling();
      if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
        socket.close();
      }
    };
  }, [pollInterval, taskId]);

  return state;
}
