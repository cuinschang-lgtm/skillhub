"use client";

import { CheckCircle2, Download, MessageCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const mockBenchmark = {
  verdict: "推荐安装",
  verdictColor: "text-green-600",
  verdictBg: "bg-green-50",
  score: 92,
  withCorrect: 28,
  withoutCorrect: 23,
  total: 30,
  delta: "+16.7%",
  pValue: 0.031,
  ciLower: "+3.2%",
  ciUpper: "+30.1%",
  overallCI: "± 3.2% (95% CI)",
  routingAccuracy: 92.1,
  chapters: [
    { id: 1, withRate: 95, withoutRate: 80 },
    { id: 2, withRate: 90, withoutRate: 75 },
    { id: 3, withRate: 100, withoutRate: 85 },
    { id: 4, withRate: 85, withoutRate: 80 },
    { id: 5, withRate: 90, withoutRate: 70 },
    { id: 6, withRate: 95, withoutRate: 90 },
    { id: 7, withRate: 80, withoutRate: 75 },
    { id: 8, withRate: 100, withoutRate: 85 },
    { id: 9, withRate: 90, withoutRate: 80 },
    { id: 10, withRate: 85, withoutRate: 70 },
    { id: 11, withRate: 95, withoutRate: 85 },
  ],
  byDifficulty: [
    { level: "总体", with: 93.3, without: 76.7 },
    { level: "简单", with: 100, without: 90 },
    { level: "概念理解", with: 90, without: 70 },
    { level: "综合应用", with: 85, without: 65 },
  ],
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

      {/* Verdict Card */}
      <Card className={`mb-6 border-green-200 ${mockBenchmark.verdictBg}`}>
        <CardContent className="p-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <CheckCircle2 className="w-10 h-10 text-green-500" />
            <div>
              <h2 className={`text-2xl font-bold ${mockBenchmark.verdictColor}`}>
                {mockBenchmark.verdict}
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                该教材质量优良，知识覆盖全面，问答效果优良。
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">综合评分</p>
            <p className="text-4xl font-bold text-foreground">
              {mockBenchmark.score}<span className="text-lg text-muted-foreground">/100</span>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Charts Grid */}
      <div className="grid md:grid-cols-3 gap-6 mb-6">
        {/* Comparison bars */}
        <Card>
          <CardContent className="p-5">
            <h3 className="text-sm font-semibold text-foreground mb-4">回答准确率对比 (%)</h3>
            <div className="space-y-4">
              {mockBenchmark.byDifficulty.map((d) => (
                <ComparisonBar key={d.level} label={d.level} withVal={d.with} withoutVal={d.without} />
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Chapter heatmap */}
        <Card>
          <CardContent className="p-5">
            <h3 className="text-sm font-semibold text-foreground mb-4">按章节准确率热力图 (%)</h3>
            <div className="grid grid-cols-6 gap-1.5">
              {mockBenchmark.chapters.map((ch) => {
                const intensity = Math.round((ch.withRate - ch.withoutRate) / 30 * 100);
                return (
                  <div
                    key={ch.id}
                    className="aspect-square rounded-md flex items-center justify-center text-[10px] font-bold text-white"
                    style={{ backgroundColor: `hsl(250, ${40 + intensity}%, ${65 - intensity * 0.2}%)` }}
                    title={`第${ch.id}章: WITH ${ch.withRate}% / WITHOUT ${ch.withoutRate}%`}
                  >
                    {ch.id}
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

        {/* Confidence interval */}
        <Card>
          <CardContent className="p-5">
            <h3 className="text-sm font-semibold text-foreground mb-4">置信区间（总体准确率）</h3>
            <div className="flex flex-col items-center justify-center h-32">
              <p className="text-3xl font-bold text-primary">{mockBenchmark.routingAccuracy}%</p>
              <p className="text-sm text-muted-foreground mt-1">{mockBenchmark.overallCI}</p>
            </div>
            <div className="mt-4 flex justify-between text-xs text-muted-foreground">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
            <div className="relative h-2 bg-muted rounded-full mt-1">
              <div
                className="absolute h-full bg-primary/30 rounded-full"
                style={{ left: "60%", width: "30%" }}
              />
              <div
                className="absolute w-2 h-2 bg-primary rounded-full top-0"
                style={{ left: "92%" }}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <Button className="bg-primary hover:bg-primary/90 gap-2">
          <MessageCircle className="w-4 h-4" /> 开始问答
        </Button>
        <Button variant="outline" className="gap-2">
          <Download className="w-4 h-4" /> 导出 Skill
        </Button>
        <Button variant="outline" className="gap-2">
          <RefreshCw className="w-4 h-4" /> 重新编译
        </Button>
      </div>
    </div>
  );
}
