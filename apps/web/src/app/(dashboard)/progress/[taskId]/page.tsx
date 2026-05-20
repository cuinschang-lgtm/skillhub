"use client";

import { CheckCircle2, Circle, Loader2, Clock } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

type StageStatus = "done" | "running" | "pending" | "failed";

interface Stage {
  id: string;
  name: string;
  status: StageStatus;
  summary?: string;
  eta?: string;
  progress?: number;
}

const mockStages: Stage[] = [
  { id: "probe", name: "解析文档结构", status: "done", summary: "识别为 PDF 文件，共 482 页" },
  { id: "toc", name: "提取目录与章节", status: "done", summary: "识别 11 章，策略：toc-first" },
  { id: "split", name: "文本清洗与分段", status: "done", summary: "共分段 1,842 段，平均长度 256 字" },
  { id: "ocr", name: "OCR 识别", status: "running", eta: "ETA 01:32", progress: 92 },
  { id: "extract", name: "向量化处理", status: "pending" },
  { id: "bench", name: "质量评估与生成", status: "pending" },
];

function StageIcon({ status }: { status: StageStatus }) {
  switch (status) {
    case "done":
      return <CheckCircle2 className="w-5 h-5 text-green-500" />;
    case "running":
      return <Loader2 className="w-5 h-5 text-primary animate-spin" />;
    case "failed":
      return <Circle className="w-5 h-5 text-red-500" />;
    default:
      return <Circle className="w-5 h-5 text-muted-foreground/40" />;
  }
}

export default function ProgressPage() {
  const currentStage = mockStages.find((s) => s.status === "running");

  return (
    <div>
      {/* Stepper */}
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

      <div className="grid lg:grid-cols-[1fr_360px] gap-8">
        {/* Left: Timeline */}
        <div className="space-y-0">
          {mockStages.map((stage, i) => (
            <div key={stage.id} className="flex gap-4">
              {/* Vertical line + icon */}
              <div className="flex flex-col items-center">
                <StageIcon status={stage.status} />
                {i < mockStages.length - 1 && (
                  <div className={`w-px flex-1 my-1 ${
                    stage.status === "done" ? "bg-green-300" : "bg-border"
                  }`} />
                )}
              </div>
              {/* Content */}
              <div className="pb-6 flex-1">
                <div className="flex items-center gap-3">
                  <span className={`text-sm font-medium ${
                    stage.status === "done" ? "text-foreground" :
                    stage.status === "running" ? "text-primary" :
                    "text-muted-foreground"
                  }`}>
                    {i + 1}. {stage.name}
                  </span>
                  {stage.status === "done" && (
                    <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">已完成</span>
                  )}
                  {stage.eta && (
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {stage.eta}
                    </span>
                  )}
                </div>
                {stage.summary && (
                  <p className="text-xs text-muted-foreground mt-1">{stage.summary}</p>
                )}
                {stage.progress !== undefined && stage.status === "running" && (
                  <div className="mt-2 w-full max-w-xs h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${stage.progress}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Right: Current stage detail + completed summaries */}
        <div className="space-y-4">
          {currentStage && (
            <Card className="border-primary/20">
              <CardContent className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-foreground">当前步骤：{currentStage.name}</h3>
                  <div className="relative w-14 h-14">
                    <svg className="w-14 h-14 -rotate-90" viewBox="0 0 56 56">
                      <circle cx="28" cy="28" r="24" fill="none" stroke="#E5E7EB" strokeWidth="4" />
                      <circle
                        cx="28" cy="28" r="24" fill="none" stroke="#6366F1" strokeWidth="4"
                        strokeDasharray={`${(currentStage.progress || 0) * 1.508} 150.8`}
                        strokeLinecap="round"
                      />
                    </svg>
                    <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-primary">
                      {currentStage.progress}%
                    </span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  正在识别和解析内容中的文字与公式...
                </p>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent className="p-5">
              <h3 className="text-sm font-semibold text-foreground mb-3">已完成摘要</h3>
              <div className="space-y-3">
                {mockStages.filter((s) => s.status === "done").map((stage) => (
                  <div key={stage.id} className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs font-medium text-foreground">{stage.name}</p>
                      <p className="text-xs text-muted-foreground">{stage.summary}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <p className="text-xs text-muted-foreground text-center">
            你可以关闭此页面，编译完成后我们会通过邮件通知你。
          </p>
        </div>
      </div>
    </div>
  );
}
