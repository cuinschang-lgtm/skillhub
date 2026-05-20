"use client";

import { Search, SlidersHorizontal } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

interface SkillItem {
  id: string;
  title: string;
  edition: string;
  domain: string;
  author: string;
  authorInitial: string;
  score: number;
  chapters: number;
  color: string;
}

const mockSkills: SkillItem[] = [
  { id: "1", title: "高等数学", edition: "第7版", domain: "数学", author: "张老师", authorInitial: "张", score: 92, chapters: 11, color: "from-indigo-400 to-purple-500" },
  { id: "2", title: "线性代数", edition: "第25版", domain: "数学", author: "李老师", authorInitial: "李", score: 88, chapters: 8, color: "from-blue-400 to-indigo-500" },
  { id: "3", title: "大学物理", edition: "上册", domain: "物理", author: "王老师", authorInitial: "王", score: 87, chapters: 14, color: "from-emerald-400 to-teal-500" },
  { id: "4", title: "数据结构", edition: "C 语言版", domain: "计算机", author: "陈老师", authorInitial: "陈", score: 91, chapters: 12, color: "from-orange-400 to-red-500" },
  { id: "5", title: "概率论与数理统计", edition: "第5版", domain: "数学", author: "张老师", authorInitial: "张", score: 85, chapters: 9, color: "from-pink-400 to-rose-500" },
  { id: "6", title: "电路原理", edition: "第5版", domain: "电子", author: "刘老师", authorInitial: "刘", score: 89, chapters: 15, color: "from-cyan-400 to-blue-500" },
];

function SkillCard({ skill }: { skill: SkillItem }) {
  return (
    <div className="group rounded-2xl border border-border bg-white shadow-sm hover:shadow-md transition-all cursor-pointer overflow-hidden">
      {/* Cover */}
      <div className={`h-28 bg-gradient-to-br ${skill.color} flex items-center justify-center relative`}>
        <div className="w-16 h-20 bg-white/20 backdrop-blur-sm rounded-lg border border-white/30 flex items-center justify-center">
          <span className="text-white/80 text-xs font-medium text-center px-1">{skill.title}</span>
        </div>
        <div className="absolute bottom-2 right-2">
          <div className="w-9 h-9 rounded-full bg-white shadow-md flex items-center justify-center">
            <span className="text-xs font-bold text-primary">{skill.score}</span>
          </div>
        </div>
      </div>
      {/* Info */}
      <div className="p-4">
        <h3 className="font-semibold text-foreground text-sm group-hover:text-primary transition-colors">
          {skill.title}（{skill.edition}）
        </h3>
        <div className="flex items-center gap-2 mt-2">
          <Avatar className="w-5 h-5">
            <AvatarFallback className="text-[10px] bg-primary/10 text-primary">{skill.authorInitial}</AvatarFallback>
          </Avatar>
          <span className="text-xs text-muted-foreground">{skill.author}</span>
          <span className="text-xs text-muted-foreground">·</span>
          <span className="text-xs text-muted-foreground">{skill.chapters} 章</span>
        </div>
      </div>
    </div>
  );
}

export default function KnowledgePage() {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">知识库</h1>
          <p className="text-sm text-muted-foreground mt-1">浏览和发现所有可用的教材 Skill</p>
        </div>
      </div>

      {/* Search & Filter */}
      <div className="flex items-center gap-3 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="搜索教材、作者或领域..." className="pl-10" />
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="cursor-pointer hover:bg-primary hover:text-white transition-colors">
            领域：全部领域
          </Badge>
          <Badge variant="secondary" className="cursor-pointer hover:bg-primary hover:text-white transition-colors">
            学科：全部学科
          </Badge>
          <Badge variant="secondary" className="cursor-pointer hover:bg-primary hover:text-white transition-colors">
            排序：最新创建
          </Badge>
        </div>
        <button className="p-2 rounded-lg border border-border hover:bg-muted transition-colors">
          <SlidersHorizontal className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>

      {/* Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
        {mockSkills.map((skill) => (
          <SkillCard key={skill.id} skill={skill} />
        ))}
      </div>
    </div>
  );
}
