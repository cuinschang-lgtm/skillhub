"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, SlidersHorizontal } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useSkills } from "@/hooks/use-skills";
import type { SkillSummary } from "@/types/skill";

function SkillCard({ skill }: { skill: SkillSummary }) {
  const router = useRouter();
  const color = skill.benchmark_delta && skill.benchmark_delta > 0 ? "bg-primary" : "bg-muted-foreground/40";
  const authorInitial = skill.book_title.slice(0, 1) || "S";

  return (
    <button
      type="button"
      onClick={() => router.push(`/benchmark/${skill.id}`)}
      className="group rounded-2xl border border-border bg-white shadow-sm hover:shadow-md transition-colors cursor-pointer overflow-hidden text-left"
    >
      <div className={`h-28 ${color} flex items-center justify-center relative`}>
        <div className="w-16 h-20 bg-white/20 backdrop-blur-sm rounded-lg border border-white/30 flex items-center justify-center">
          <span className="text-white/80 text-xs font-medium text-center px-1">{skill.book_title}</span>
        </div>
        <div className="absolute bottom-2 right-2">
          <div className="px-2 py-1 rounded-full bg-white shadow-md flex items-center justify-center">
            <span className="text-[10px] font-bold text-primary">
              {typeof skill.benchmark_score === "number" ? `评分 ${skill.benchmark_score}` : "未测评"}
            </span>
          </div>
        </div>
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-foreground text-sm group-hover:text-primary transition-colors">
          {skill.book_title}
        </h3>
        <div className="flex items-center gap-2 mt-2">
          <Avatar className="w-5 h-5">
            <AvatarFallback className="text-[10px] bg-primary/10 text-primary">{authorInitial}</AvatarFallback>
          </Avatar>
          <span className="text-xs text-muted-foreground">{skill.domain || "未分类"}</span>
          <span className="text-xs text-muted-foreground">·</span>
          <span className="text-xs text-muted-foreground">{skill.chapter_count || 0} 章</span>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <Badge variant="secondary">{skill.visibility === "public" ? "公开" : "私有"}</Badge>
          {skill.benchmark_verdict ? <Badge variant="secondary">{skill.benchmark_verdict}</Badge> : null}
        </div>
      </div>
    </button>
  );
}

export default function KnowledgePage() {
  const [search, setSearch] = useState("");
  const { skills, loading, error } = useSkills(search);

  const emptyText = useMemo(() => {
    if (loading) return "正在加载知识库...";
    if (search.trim()) return "没有匹配到相关 Skill";
    return "还没有生成任何 Skill，先去上传一本教材试试。";
  }, [loading, search]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">知识库</h1>
          <p className="text-sm text-muted-foreground mt-1">浏览和发现所有可用的教材 Skill</p>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="搜索教材、领域..."
            className="pl-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">来源：真实数据</Badge>
          <Badge variant="secondary">排序：最新创建</Badge>
        </div>
        <button className="p-2 rounded-lg border border-border hover:bg-muted transition-colors">
          <SlidersHorizontal className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>

      {error ? (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </div>
      ) : null}

      {skills.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-white p-10 text-center text-sm text-muted-foreground">
          {emptyText}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {skills.map((skill) => (
            <SkillCard key={skill.id} skill={skill} />
          ))}
        </div>
      )}
    </div>
  );
}
