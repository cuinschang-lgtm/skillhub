"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { CheckCircle2, Circle, Loader2, Clock, AlertCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type TaskStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

type TaskDetail = {
  id: string;
  status: TaskStatus;
  book_title: string;
  skill_name: string;
  skill_slug?: string | null;
  current_stage: string | null;
  progress_pct: number;
  error_message?: string | null;
  skill_id?: string | null;
};

type TaskErrorPayload = {
  detail?: string;
};

const STAGES = [
  { id: "probe", name: "解析文档结构" },
  { id: "ocr", name: "文本提取 / OCR" },
  { id: "split", name: "章节切分" },
  { id: "extract", name: "知识抽取" },
  { id: "assemble", name: "Skill 组装" },
  { id: "bench", name: "质量评估与生成" },
];

function StageIcon({ state }: { state: "done" | "running" | "pending" | "failed" }) {
  switch (state) {
    case "done":
      return <CheckCircle2 className="w-5 h-5 text-green-500" />;
    case "running":
      return <Loader2 className="w-5 h-5 text-primary animate-spin" />;
    case "failed":
      return <AlertCircle className="w-5 h-5 text-red-500" />;
    default:
      return <Circle className="w-5 h-5 text-muted-foreground/40" />;
  }
}

export default function ProgressPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const router = useRouter();
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadTask() {
      try {
        const res = await fetch(`/api/tasks/${taskId}`, { cache: "no-store" });
        const payload = (await res.json().catch(() => null)) as TaskDetail | TaskErrorPayload | null;
        if (!res.ok || !payload || !("id" in payload)) {
          const message = payload && "detail" in payload ? payload.detail : undefined;
          if (!cancelled) setError(message || "获取任务失败");
          return;
        }
        if (!cancelled) {
          setTask(payload);
          setError("");
          if (payload.status === "completed" && payload.skill_id) {
            router.replace(`/benchmark/${payload.skill_id}`);
          }
        }
      } catch {
        if (!cancelled) setError("网络错误，请稍后重试");
      }
    }

    loadTask();
    const timer = window.setInterval(loadTask, 3000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [router, taskId]);

  const stageItems = useMemo(() => {
    const currentIndex = STAGES.findIndex((s) => s.id === task?.current_stage);
    return STAGES.map((stage, index) => {
      let state: "done" | "running" | "pending" | "failed" = "pending";
      if (task?.status === "failed") {
        if (stage.id === task.current_stage || (task.current_stage === "failed" && index === currentIndex)) {
          state = "failed";
        } else if (currentIndex >= 0 && index < currentIndex) {
          state = "done";
        }
      } else if (task?.status === "completed") {
        state = "done";
      } else if (currentIndex >= 0) {
        if (index < currentIndex) state = "done";
        if (index === currentIndex) state = "running";
      }
      return { ...stage, state };
    });
  }, [task]);

  const currentStage = stageItems.find((stage) => stage.state === "running");

  return (
    <div>
      <div className="flex items-center gap-3 mb-8">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-green-500 text-white text-xs font-bold flex items-center justify-center">
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <span className="text-sm text-muted-foreground">上传 & 配置</span>
        </div>
        <div className="w-8 h-px bg-border" />
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center">2</div>
          <span className="text-sm font-medium text-foreground">编译进度</span>
        </div>
        <div className="w-8 h-px bg-border" />
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-muted text-muted-foreground text-xs font-bold flex items-center justify-center">3</div>
          <span className="text-sm text-muted-foreground">编译结果</span>
        </div>
      </div>

      {error ? (
        <div className="mb-6 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </div>
      ) : null}

      <div className="grid lg:grid-cols-[1fr_360px] gap-8">
        <div className="space-y-0">
          {stageItems.map((stage, i) => (
            <div key={stage.id} className="flex gap-4">
              <div className="flex flex-col items-center">
                <StageIcon state={stage.state} />
                {i < stageItems.length - 1 && (
                  <div className={`w-px flex-1 my-1 ${stage.state === "done" ? "bg-green-300" : "bg-border"}`} />
                )}
              </div>
              <div className="pb-6 flex-1">
                <div className="flex items-center gap-3">
                  <span
                    className={`text-sm font-medium ${
                      stage.state === "done"
                        ? "text-foreground"
                        : stage.state === "running"
                          ? "text-primary"
                          : stage.state === "failed"
                            ? "text-red-600"
                            : "text-muted-foreground"
                    }`}
                  >
                    {i + 1}. {stage.name}
                  </span>
                  {stage.state === "done" ? (
                    <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">已完成</span>
                  ) : null}
                  {stage.state === "running" ? (
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="w-3 h-3" /> 进行中
                    </span>
                  ) : null}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-4">
          <Card className="border-primary/20">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">
                    {task?.book_title || "正在准备任务"}
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    当前步骤：{currentStage?.name || task?.current_stage || "排队中"}
                  </p>
                </div>
                <div className="relative w-14 h-14">
                  <svg className="w-14 h-14 -rotate-90" viewBox="0 0 56 56">
                    <circle cx="28" cy="28" r="24" fill="none" stroke="#E5E7EB" strokeWidth="4" />
                    <circle
                      cx="28"
                      cy="28"
                      r="24"
                      fill="none"
                      stroke="#6366F1"
                      strokeWidth="4"
                      strokeDasharray={`${(task?.progress_pct || 0) * 1.508} 150.8`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-primary">
                    {task?.progress_pct || 0}%
                  </span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                {task?.status === "failed"
                  ? task.error_message || "任务失败"
                  : task?.status === "completed"
                    ? "已完成，正在跳转结果页..."
                    : "后台正在运行教材编译流程。"}
              </p>
            </CardContent>
          </Card>

          {task?.status === "failed" ? (
            <Card>
              <CardContent className="p-5">
                <h3 className="text-sm font-semibold text-foreground mb-3">任务失败</h3>
                <p className="text-xs text-muted-foreground mb-4 whitespace-pre-wrap">
                  {task.error_message || "未知错误"}
                </p>
                <Button variant="outline" onClick={() => router.push("/upload")}>
                  返回重新上传
                </Button>
              </CardContent>
            </Card>
          ) : null}

          <p className="text-xs text-muted-foreground text-center">
            保持页面打开即可自动刷新；完成后会自动进入编译结果页。
          </p>
        </div>
      </div>
    </div>
  );
}
