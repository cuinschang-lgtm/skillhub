"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileText, Check, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [bookTitle, setBookTitle] = useState("");
  const [domain, setDomain] = useState("");
  const [skillName, setSkillName] = useState("");
  const [visibility, setVisibility] = useState<"public" | "private">("public");
  const [llmProvider, setLlmProvider] = useState("deepseek");
  const [ocrProvider, setOcrProvider] = useState("mineru");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const suggestedSkillName = skillName || bookTitle;

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped?.type === "application/pdf") {
      setFile(dropped);
    }
  };

  const handleSubmit = async () => {
    if (!file || !bookTitle || !domain) return;
    setSubmitting(true);
    setError("");
    try {
      const formData = new FormData();
      formData.set("pdf", file);
      formData.set("book_title", bookTitle);
      formData.set("domain", domain);
      formData.set("skill_name", skillName || bookTitle);
      formData.set("visibility", visibility);
      formData.set("llm_provider", llmProvider);
      formData.set("ocr_provider", ocrProvider);

      const res = await fetch("/api/tasks", {
        method: "POST",
        body: formData,
      });
      const data = (await res.json().catch(() => null)) as { id?: string; detail?: string; message?: string } | null;
      if (!res.ok || !data?.id) {
        setError(data?.detail || data?.message || "创建任务失败");
        return;
      }
      router.push(`/progress/${data.id}`);
    } catch {
      setError("网络错误，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      {/* Stepper */}
      <div className="flex items-center gap-3 mb-8">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center">1</div>
          <span className="text-sm font-medium text-foreground">上传 & 配置</span>
        </div>
        <div className="w-8 h-px bg-border" />
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-muted text-muted-foreground text-xs font-bold flex items-center justify-center">2</div>
          <span className="text-sm text-muted-foreground">编译进度</span>
        </div>
        <div className="w-8 h-px bg-border" />
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-muted text-muted-foreground text-xs font-bold flex items-center justify-center">3</div>
          <span className="text-sm text-muted-foreground">编译结果</span>
        </div>
      </div>

      {error ? (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </div>
      ) : null}

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left: Drop zone */}
        <div>
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="border-2 border-dashed border-border rounded-2xl p-12 text-center hover:border-primary/50 transition-colors cursor-pointer bg-white"
          >
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center">
                <Upload className="w-8 h-8 text-primary" />
              </div>
              <p className="text-sm text-muted-foreground">
                拖拽 PDF 文件到这里上传
              </p>
              <p className="text-xs text-muted-foreground">或</p>
              <label className="cursor-pointer">
                <span className="text-sm text-primary hover:underline font-medium">点击选择文件</span>
                <input
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) setFile(f);
                  }}
                />
              </label>
            </div>
          </div>

          {file && (
            <Card className="mt-4">
              <CardContent className="flex items-center gap-3 py-3 px-4">
                <FileText className="w-5 h-5 text-primary" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{file.name}</p>
                  <p className="text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
                </div>
                <Check className="w-4 h-4 text-green-500" />
                <button onClick={() => setFile(null)} className="p-1 hover:bg-muted rounded">
                  <Trash2 className="w-4 h-4 text-muted-foreground" />
                </button>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right: Config form */}
        <div className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="bookTitle">书名 *</Label>
            <Input
              id="bookTitle"
              placeholder="高等数学（第7版）"
              value={bookTitle}
              onChange={(e) => setBookTitle(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="domain">领域 *</Label>
            <Input
              id="domain"
              placeholder="理工科 > 数学 > 高等数学"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="skillName">Skill 名称</Label>
            <Input
              id="skillName"
              placeholder="gaodeng-shuxue"
              value={skillName}
              onChange={(e) => setSkillName(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              用于系统内部标识；不填会自动根据书名生成。
            </p>
          </div>

          <div className="rounded-xl border border-border bg-muted/30 px-4 py-3 text-xs text-muted-foreground">
            当前将显示为：<span className="font-medium text-foreground">{suggestedSkillName || "未命名教材"}</span>
          </div>

          <div className="space-y-2">
            <Label>可见性 *</Label>
            <div className="flex gap-3">
              <button
                onClick={() => setVisibility("public")}
                className={`flex-1 py-2.5 px-4 rounded-lg border text-sm transition-all ${
                  visibility === "public"
                    ? "border-primary bg-secondary text-primary font-medium"
                    : "border-border text-muted-foreground hover:border-primary/50"
                }`}
              >
                公开（所有人可见）
              </button>
              <button
                onClick={() => setVisibility("private")}
                className={`flex-1 py-2.5 px-4 rounded-lg border text-sm transition-all ${
                  visibility === "private"
                    ? "border-primary bg-secondary text-primary font-medium"
                    : "border-border text-muted-foreground hover:border-primary/50"
                }`}
              >
                私有（仅自己可见）
              </button>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="llmProvider">LLM Provider</Label>
              <select
                id="llmProvider"
                value={llmProvider}
                onChange={(e) => setLlmProvider(e.target.value)}
                className="w-full rounded-lg border border-border bg-white px-3 py-2.5 text-sm"
              >
                <option value="deepseek">DeepSeek</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="ocrProvider">OCR Provider</Label>
              <select
                id="ocrProvider"
                value={ocrProvider}
                onChange={(e) => setOcrProvider(e.target.value)}
                className="w-full rounded-lg border border-border bg-white px-3 py-2.5 text-sm"
              >
                <option value="mineru">MinerU</option>
              </select>
            </div>
          </div>

          <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-xs text-blue-900">
            演示环境已接入服务端 LLM key。若 PDF 本身有文字层，会优先直接提取文本；扫描版 PDF 会走 OCR。
          </div>

          <Button
            className="w-full bg-primary hover:bg-primary/90 mt-4"
            size="lg"
            disabled={!file || !bookTitle || !domain || submitting}
            onClick={handleSubmit}
          >
            {submitting ? "创建任务中..." : "开始编译 →"}
          </Button>
        </div>
      </div>
    </div>
  );
}
