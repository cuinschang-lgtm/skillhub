"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { CheckCircle2, Download, MessageCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type SkillDetail = {
  id: string;
  name: string;
  book_title: string;
  chapter_count?: number | null;
  benchmark_verdict?: string | null;
  benchmark_delta?: number | null;
};

type BenchmarkPayload = {
  verdict: string;
  delta_pct: number;
  p_value: number;
  ci_lower: number;
  ci_upper: number;
  routing_accuracy: number;
  total_questions: number;
  with_correct: number;
  without_correct: number;
  per_chapter: { chapter: string; with_rate: number; without_rate: number }[];
  per_difficulty: { level: string; with: number; without: number }[];
};

function ComparisonBar({ label, withVal, withoutVal }: { label: string; withVal: number; withoutVal: number }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="text-foreground font-medium">Δ {(withVal - withoutVal).toFixed(1)}%</span>
      </div>
      <div className="flex gap-1 h-3">
        <div className="flex-1 bg-muted rounded-full overflow-hidden">
          <div className="h-full bg-primary rounded-full" style={{ width: `${withVal}%` }} />
        </div>
        <div className="flex-1 bg-muted rounded-full overflow-hidden">
          <div className="h-full bg-muted-foreground/30 rounded-full" style={{ width: `${withoutVal}%` }} />
        </div>
      </div>
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>WITH {withVal}%</span>
        <span>WITHOUT {withoutVal}%</span>
      </div>
    </div>
  );
}

export default function BenchmarkPage() {
  const { skillId } = useParams<{ skillId: string }>();
  const router = useRouter();
  const [skill, setSkill] = useState<SkillDetail | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkPayload | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [skillRes, benchmarkRes] = await Promise.all([
          fetch(`/api/skills/${skillId}`, { cache: "no-store" }),
          fetch(`/api/skills/${skillId}/benchmark`, { cache: "no-store" }),
        ]);

        const skillData = await skillRes.json().catch(() => null);
        const benchmarkData = await benchmarkRes.json().catch(() => null);
        if (!skillRes.ok || !benchmarkRes.ok) {
          if (!cancelled) setError(skillData?.detail || benchmarkData?.detail || "获取结果失败");
          return;
        }
        if (!cancelled) {
          setSkill(skillData);
          setBenchmark(benchmarkData);
          setError("");
        }
      } catch {
        if (!cancelled) setError("网络错误，请稍后重试");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [skillId]);

  const score = useMemo(() => {
    if (!benchmark) return 0;
    const accuracy = benchmark.total_questions ? benchmark.with_correct / benchmark.total_questions : 0;
    const deltaBoost = Math.max(0, benchmark.delta_pct) / 2;
    return Math.min(100, Math.round(accuracy * 80 + deltaBoost));
  }, [benchmark]);

  const verdictColor = benchmark?.delta_pct && benchmark.delta_pct > 0 ? "text-green-600" : "text-amber-600";
  const verdictBg = benchmark?.delta_pct && benchmark.delta_pct > 0 ? "bg-green-50" : "bg-amber-50";
  const statusText = benchmark?.delta_pct && benchmark.delta_pct > 0 ? "编译成功" : "编译完成";

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
          <div className="w-7 h-7 rounded-full bg-green-500 text-white text-xs font-bold flex items-center justify-center">
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <span className="text-sm text-muted-foreground">编译进度</span>
        </div>
        <div className="w-8 h-px bg-border" />
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center">3</div>
          <span className="text-sm font-medium text-foreground">编译结果</span>
        </div>
      </div>

      {error ? (
        <div className="mb-6 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </div>
      ) : null}

      {!benchmark || !skill ? null : (
        <>
          <Card className={`mb-6 border-green-200 ${verdictBg}`}>
            <CardContent className="p-6 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <CheckCircle2 className="w-10 h-10 text-green-500" />
                <div className="min-w-0">
                  <div className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${verdictColor} bg-white/80`}>
                    {statusText}
                  </div>
                  <h2 className={`mt-3 text-lg font-bold leading-7 ${verdictColor} break-words`}>
                    {benchmark.verdict}
                  </h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    {skill.book_title} 已编译完成，共 {skill.chapter_count || 0} 章。
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted-foreground">综合评分</p>
                <p className="text-4xl font-bold text-foreground">
                  {score}
                  <span className="text-lg text-muted-foreground">/100</span>
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="grid md:grid-cols-3 gap-6 mb-6">
            <Card>
              <CardContent className="p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4">回答准确率对比 (%)</h3>
                <div className="space-y-4">
                  {benchmark.per_difficulty.map((row) => (
                    <ComparisonBar key={row.level} label={row.level} withVal={row.with} withoutVal={row.without} />
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4">按章节准确率热力图 (%)</h3>
                <div className="grid grid-cols-4 gap-1.5">
                  {benchmark.per_chapter.map((row, index) => {
                    const diff = Math.max(0, row.with_rate - row.without_rate);
                    const intensity = Math.min(100, Math.round((diff / 30) * 100));
                    return (
                      <div
                        key={row.chapter}
                        className="aspect-square rounded-md flex items-center justify-center text-[10px] font-bold text-white"
                        style={{ backgroundColor: `hsl(250, ${40 + intensity}%, ${65 - intensity * 0.2}%)` }}
                        title={`${row.chapter}: WITH ${row.with_rate}% / WITHOUT ${row.without_rate}%`}
                      >
                        {index + 1}
                      </div>
                    );
                  })}
                </div>
                <div className="flex justify-between mt-3 text-[10px] text-muted-foreground">
                  <span>0</span>
                  <span>50%</span>
                  <span>100%</span>
                </div>
                <div className="h-1.5 rounded-full bg-gradient-to-r from-muted via-primary/50 to-primary mt-1" />
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4">置信区间（总体提升）</h3>
                <div className="flex flex-col items-center justify-center h-32">
                  <p className="text-3xl font-bold text-primary">{benchmark.delta_pct.toFixed(1)}%</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    95% CI [{benchmark.ci_lower.toFixed(1)}%, {benchmark.ci_upper.toFixed(1)}%]
                  </p>
                </div>
                <div className="mt-4 text-xs text-muted-foreground space-y-1">
                  <p>WITH: {benchmark.with_correct}/{benchmark.total_questions}</p>
                  <p>WITHOUT: {benchmark.without_correct}/{benchmark.total_questions}</p>
                  <p>p-value: {benchmark.p_value.toFixed(3)}</p>
                  <p>路由准确率: {benchmark.routing_accuracy.toFixed(1)}%</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="flex items-center gap-3">
            <Button className="bg-primary hover:bg-primary/90 gap-2" onClick={() => router.push(`/chat?skillId=${skill.id}`)}>
              <MessageCircle className="w-4 h-4" /> 开始问答
            </Button>
            <Button variant="outline" className="gap-2" onClick={() => router.push("/knowledge")}>
              <Download className="w-4 h-4" /> 查看知识库
            </Button>
            <Button variant="outline" className="gap-2" onClick={() => router.push("/upload")}>
              <RefreshCw className="w-4 h-4" /> 重新编译
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
