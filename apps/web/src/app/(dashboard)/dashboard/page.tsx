"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Upload, Library, Clock3, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type TaskItem = {
  id: string;
  status: string;
  book_title: string;
  skill_name: string;
  current_stage: string | null;
  progress_pct: number;
};

type SkillItem = {
  id: string;
  book_title: string;
  domain?: string | null;
  benchmark_delta?: number | null;
};

export default function DashboardPage() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [skills, setSkills] = useState<SkillItem[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [tasksRes, skillsRes] = await Promise.all([
          fetch("/api/tasks", { cache: "no-store" }),
          fetch("/api/skills?page_size=4", { cache: "no-store" }),
        ]);
        const tasksData = await tasksRes.json().catch(() => ({ items: [] }));
        const skillsData = await skillsRes.json().catch(() => ({ items: [] }));
        if (!cancelled) {
          setTasks(tasksData.items || []);
          setSkills(skillsData.items || []);
        }
      } catch {
        if (!cancelled) {
          setTasks([]);
          setSkills([]);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const runningTask = tasks.find((task) => task.status === "running" || task.status === "pending");

  return (
    <div className="space-y-6">
      <div className="grid lg:grid-cols-[1.3fr_1fr] gap-6">
        <Card className="border-border shadow-sm">
          <CardContent className="p-6">
            <p className="text-sm text-muted-foreground mb-2">演示环境工作台</p>
            <h1 className="text-3xl font-bold text-foreground leading-tight">
              把教材上传、编译成 Skill，
              <br />
              再用真实 benchmark 看它到底有没有价值。
            </h1>
            <p className="mt-4 text-sm text-muted-foreground max-w-2xl">
              当前网站已经接通上传任务、后台编译、结果页和知识库。下一步你可以直接上传一本教材开始跑完整流程。
            </p>
            <div className="mt-6 flex items-center gap-3">
              <Link href="/upload" className="inline-flex">
                <Button className="bg-primary hover:bg-primary/90 gap-2">
                  <Upload className="w-4 h-4" /> 上传教材
                </Button>
              </Link>
              <Link href="/knowledge" className="inline-flex">
                <Button variant="outline" className="gap-2">
                  <Library className="w-4 h-4" /> 查看知识库
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-3">
              <Clock3 className="w-4 h-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">最近任务</h2>
            </div>
            {runningTask ? (
              <div className="space-y-3">
                <div>
                  <p className="font-medium text-foreground">{runningTask.book_title}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    当前阶段：{runningTask.current_stage || "queued"} · {runningTask.progress_pct}%
                  </p>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div className="h-full bg-primary rounded-full" style={{ width: `${runningTask.progress_pct}%` }} />
                </div>
                <Link href={`/progress/${runningTask.id}`} className="inline-flex">
                  <Button variant="outline" size="sm" className="gap-2">
                    查看进度 <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">暂无运行中的任务。</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">累计任务</p>
            <p className="text-3xl font-bold text-foreground mt-2">{tasks.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">已生成 Skill</p>
            <p className="text-3xl font-bold text-foreground mt-2">{skills.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">可继续验证</p>
            <p className="text-3xl font-bold text-foreground mt-2">
              {skills.filter((skill) => (skill.benchmark_delta || 0) > 0).length}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-foreground mb-4">最近生成的 Skill</h2>
          {skills.length === 0 ? (
            <p className="text-sm text-muted-foreground">还没有生成任何 Skill，先去上传一本教材试试。</p>
          ) : (
            <div className="space-y-3">
              {skills.map((skill) => (
                <Link
                  key={skill.id}
                  href={`/benchmark/${skill.id}`}
                  className="flex items-center justify-between rounded-xl border border-border px-4 py-3 hover:bg-muted/40 transition-colors"
                >
                  <div>
                    <p className="font-medium text-foreground">{skill.book_title}</p>
                    <p className="text-xs text-muted-foreground mt-1">{skill.domain || "未分类"}</p>
                  </div>
                  <span className="text-sm font-semibold text-primary">
                    {skill.benchmark_delta?.toFixed(1) || "0.0"}%
                  </span>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
