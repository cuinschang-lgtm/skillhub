"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Send, BookOpen, Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: { skill_id: string; skill_name: string; chapter: string; excerpt: string }[];
}

type SkillItem = {
  id: string;
  name: string;
  book_title: string;
  chapter_count?: number | null;
  visibility: string;
};

function ChatPageInner() {
  const searchParams = useSearchParams();
  const requestedSkillId = searchParams.get("skillId");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "请选择要激活的教材 Skill，然后输入问题开始问答。",
    },
  ]);
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [selectedSkillIds, setSelectedSkillIds] = useState<string[]>([]);
  const [loadingSkills, setLoadingSkills] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadSkills() {
      setLoadingSkills(true);
      try {
        const res = await fetch("/api/skills", { cache: "no-store" });
        const data = (await res.json().catch(() => null)) as { items?: SkillItem[]; detail?: string } | null;
        if (!res.ok) {
          if (!cancelled) setError(data?.detail || "加载 Skill 失败");
          return;
        }
        if (!cancelled) {
          const items = data?.items || [];
          setSkills(items);
          setSelectedSkillIds((current) => {
            const existing = current.filter((id) => items.some((skill) => skill.id === id));
            if (existing.length > 0) return existing;
            if (requestedSkillId && items.some((skill) => skill.id === requestedSkillId)) {
              return [requestedSkillId];
            }
            return items[0] ? [items[0].id] : [];
          });
          setError("");
        }
      } catch {
        if (!cancelled) setError("网络错误，请稍后重试");
      } finally {
        if (!cancelled) setLoadingSkills(false);
      }
    }

    loadSkills();
    return () => {
      cancelled = true;
    };
  }, [requestedSkillId]);

  const activeSkills = useMemo(
    () => skills.filter((skill) => selectedSkillIds.includes(skill.id)),
    [selectedSkillIds, skills],
  );

  const inactiveSkills = useMemo(
    () => skills.filter((skill) => !selectedSkillIds.includes(skill.id)),
    [selectedSkillIds, skills],
  );

  async function handleSend() {
    const question = input.trim();
    if (!question || sending) return;
    if (selectedSkillIds.length === 0) {
      setError("请先激活至少一个 Skill");
      return;
    }

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: question,
    };

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setSending(true);
    setError("");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({
          question,
          active_skill_ids: selectedSkillIds,
        }),
      });
      const data = (await res.json().catch(() => null)) as
        | { answer?: string; citations?: Message["citations"]; detail?: string }
        | null;
      const answer = data?.answer;
      const citations = Array.isArray(data?.citations) ? data.citations : [];
      if (!res.ok || typeof answer !== "string") {
        const detail = data?.detail || "问答失败，请稍后重试";
        setError(detail);
        setMessages((current) => [
          ...current,
          {
            id: `assistant-error-${Date.now()}`,
            role: "assistant",
            content: `暂时无法完成问答：${detail}`,
          },
        ]);
        return;
      }

      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: answer,
          citations,
        },
      ]);
    } catch {
      const detail = "网络错误，请稍后重试";
      setError(detail);
      setMessages((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          content: `暂时无法完成问答：${detail}`,
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  function toggleSkill(skillId: string) {
    setSelectedSkillIds((current) =>
      current.includes(skillId) ? current.filter((id) => id !== skillId) : [...current, skillId],
    );
  }

  return (
    <div className="h-full flex">
      <div className="w-72 border-r border-border bg-white p-4 space-y-5 shrink-0 overflow-y-auto">
        <div>
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">已激活 Skill</h3>
          <div className="space-y-2 mt-3">
            {activeSkills.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border px-3 py-4 text-xs text-muted-foreground">
                还没有激活任何 Skill
              </div>
            ) : (
              activeSkills.map((skill) => (
                <button
                  key={skill.id}
                  type="button"
                  onClick={() => toggleSkill(skill.id)}
                  className="w-full p-3 rounded-xl bg-secondary/50 border border-primary/20 text-left"
                >
                  <div className="flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-primary" />
                    <span className="text-xs font-medium text-foreground truncate">{skill.book_title}</span>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">{skill.chapter_count || 0} 章</span>
                    <Badge variant="secondary">已激活</Badge>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        <div>
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">可添加 Skill</h3>
          <div className="space-y-2 mt-3">
            {loadingSkills ? (
              <div className="rounded-xl border border-dashed border-border px-3 py-4 text-xs text-muted-foreground flex items-center gap-2">
                <Loader2 className="w-3 h-3 animate-spin" /> 正在加载 Skill...
              </div>
            ) : inactiveSkills.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border px-3 py-4 text-xs text-muted-foreground">
                没有更多可添加的 Skill
              </div>
            ) : (
              inactiveSkills.map((skill) => (
                <button
                  key={skill.id}
                  type="button"
                  onClick={() => toggleSkill(skill.id)}
                  className="w-full p-3 rounded-xl bg-white border border-border hover:border-primary/30 text-left transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-muted-foreground" />
                    <span className="text-xs font-medium text-foreground truncate">{skill.book_title}</span>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">{skill.chapter_count || 0} 章</span>
                    <Badge variant="secondary">点击激活</Badge>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        {error ? (
          <div className="mx-6 mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
            {error}
          </div>
        ) : null}

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-2xl rounded-2xl px-5 py-3 ${
                  msg.role === "user" ? "bg-primary text-white" : "bg-white border border-border shadow-sm"
                }`}
              >
                <p className={`text-sm whitespace-pre-wrap leading-relaxed ${msg.role === "user" ? "text-white" : "text-foreground"}`}>
                  {msg.content}
                </p>
                {msg.citations && msg.citations.length > 0 ? (
                  <div className="mt-3 pt-3 border-t border-border/50">
                    <div className="flex flex-wrap gap-2">
                      {msg.citations.map((c, i) => (
                        <Badge key={`${c.skill_id}-${c.chapter}-${i}`} variant="secondary" className="text-[10px] gap-1">
                          <Sparkles className="w-3 h-3" />
                          {c.skill_name} · {c.chapter}
                        </Badge>
                      ))}
                    </div>
                    <div className="mt-3 space-y-2">
                      {msg.citations.map((c, i) => (
                        <div key={`${c.skill_id}-excerpt-${i}`} className="rounded-lg bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                          {c.excerpt}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>

        <div className="border-t border-border bg-white p-4">
          <div className="flex items-center gap-3 max-w-3xl mx-auto">
            <input
              type="text"
              placeholder="输入你的问题..."
              className="flex-1 px-4 py-3 rounded-xl border border-border bg-muted/30 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void handleSend();
                }
              }}
            />
            <Button
              size="icon"
              className="bg-primary hover:bg-primary/90 rounded-xl w-11 h-11"
              disabled={sending || selectedSkillIds.length === 0}
              onClick={() => void handleSend()}
            >
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="h-full bg-white" />}>
      <ChatPageInner />
    </Suspense>
  );
}
