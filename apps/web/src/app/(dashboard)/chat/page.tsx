"use client";

import { useState } from "react";
import { Send, BookOpen, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: { chapter: string; excerpt: string }[];
}

const mockMessages: Message[] = [
  { id: "1", role: "user", content: "什么是拉格朗日中值定理？" },
  {
    id: "2",
    role: "assistant",
    content: "拉格朗日中值定理（Lagrange Mean Value Theorem）是微积分中的基本定理之一。\n\n**定理内容**：如果函数 f(x) 在闭区间 [a,b] 上连续，在开区间 (a,b) 内可导，则至少存在一点 ξ ∈ (a,b)，使得：\n\nf'(ξ) = [f(b) - f(a)] / (b - a)\n\n**几何意义**：曲线上至少存在一点，该点的切线平行于连接曲线两端点的割线。\n\n**应用**：常用于证明不等式、求极限、以及建立函数值与导数之间的关系。",
    citations: [{ chapter: "第3章 微分中值定理", excerpt: "拉格朗日中值定理是罗尔定理的推广..." }],
  },
];

const activeSkills = [
  { id: "1", name: "高等数学（第7版）", chapters: 11 },
  { id: "2", name: "线性代数（第25版）", chapters: 8 },
];

export default function ChatPage() {
  const [input, setInput] = useState("");

  return (
    <div className="h-full flex">
      {/* Left: Skill selector */}
      <div className="w-56 border-r border-border bg-white p-4 space-y-4 shrink-0">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">已激活 Skill</h3>
        <div className="space-y-2">
          {activeSkills.map((skill) => (
            <div key={skill.id} className="p-3 rounded-xl bg-secondary/50 border border-primary/10">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-primary" />
                <span className="text-xs font-medium text-foreground truncate">{skill.name}</span>
              </div>
              <span className="text-[10px] text-muted-foreground mt-1 block">{skill.chapters} 章</span>
            </div>
          ))}
        </div>
        <Button variant="outline" size="sm" className="w-full text-xs">
          + 添加 Skill
        </Button>
      </div>

      {/* Right: Chat area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {mockMessages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-2xl rounded-2xl px-5 py-3 ${
                msg.role === "user"
                  ? "bg-primary text-white"
                  : "bg-white border border-border shadow-sm"
              }`}>
                <p className={`text-sm whitespace-pre-wrap leading-relaxed ${
                  msg.role === "user" ? "text-white" : "text-foreground"
                }`}>
                  {msg.content}
                </p>
                {msg.citations && (
                  <div className="mt-3 pt-3 border-t border-border/50">
                    {msg.citations.map((c, i) => (
                      <Badge key={i} variant="secondary" className="text-[10px] gap-1">
                        <Sparkles className="w-3 h-3" />
                        来源：{c.chapter}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input */}
        <div className="border-t border-border bg-white p-4">
          <div className="flex items-center gap-3 max-w-3xl mx-auto">
            <input
              type="text"
              placeholder="输入你的问题..."
              className="flex-1 px-4 py-3 rounded-xl border border-border bg-muted/30 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <Button size="icon" className="bg-primary hover:bg-primary/90 rounded-xl w-11 h-11">
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
