"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen, GraduationCap, Users, Mail, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

function RegisterInner() {
  const [role, setRole] = useState<"teacher" | "student" | null>(null);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [remember, setRemember] = useState(true);
  const [sending, setSending] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [error, setError] = useState("");
  const router = useRouter();
  const sp = useSearchParams();
  const nextPath = useMemo(() => sp.get("next") || "/dashboard", [sp]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = window.setInterval(() => setCooldown((v) => Math.max(0, v - 1)), 1000);
    return () => window.clearInterval(t);
  }, [cooldown]);

  async function sendCode() {
    setError("");
    const v = email.trim().toLowerCase();
    if (!v) {
      setError("请输入邮箱");
      return;
    }
    setSending(true);
    try {
      const res = await fetch("/api/auth/send-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: v }),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { message?: string } | null;
        setError(data?.message || "发送失败");
        return;
      }
      setCooldown(60);
    } catch {
      setError("网络错误，请稍后重试");
    } finally {
      setSending(false);
    }
  }

  async function register() {
    setError("");
    const v = email.trim().toLowerCase();
    if (!role) {
      setError("请选择身份");
      return;
    }
    if (!v) {
      setError("请输入邮箱");
      return;
    }
    if (!code.trim()) {
      setError("请输入验证码");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch("/api/auth/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: v, code, role, remember }),
        credentials: "include",
      });
      const data = (await res.json().catch(() => null)) as { message?: string } | null;
      if (!res.ok) {
        setError(data?.message || "注册失败");
        return;
      }
      router.replace(nextPath);
    } catch {
      setError("网络错误，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--background)] flex items-center justify-center p-6">
      <div className="w-full max-w-3xl grid md:grid-cols-2 gap-6">
        {/* Left: Login form redirect */}
        <Card className="shadow-lg border-border">
          <CardHeader className="text-center pb-2">
            <div className="flex justify-center mb-4">
              <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-white" />
              </div>
            </div>
            <h1 className="text-2xl font-bold text-foreground">创建账户</h1>
            <p className="text-sm text-muted-foreground mt-1">请选择你的身份角色</p>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="text-sm text-muted-foreground bg-muted border border-border rounded-lg px-3 py-2">
              演示环境不发送邮件验证码，固定为 <span className="font-semibold text-foreground">123456</span>
            </div>
            {error ? (
              <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </div>
            ) : null}
            <button
              onClick={() => setRole("teacher")}
              className={`w-full p-4 rounded-xl border-2 text-left transition-all ${
                role === "teacher"
                  ? "border-primary bg-secondary"
                  : "border-border hover:border-primary/50"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <GraduationCap className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <p className="font-semibold text-foreground">我是教师</p>
                  <p className="text-xs text-muted-foreground">新增更多学习功能与资源配置。</p>
                </div>
              </div>
            </button>

            <button
              onClick={() => setRole("student")}
              className={`w-full p-4 rounded-xl border-2 text-left transition-all ${
                role === "student"
                  ? "border-primary bg-secondary"
                  : "border-border hover:border-primary/50"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
                  <Users className="w-5 h-5 text-accent" />
                </div>
                <div>
                  <p className="font-semibold text-foreground">我是学生</p>
                  <p className="text-xs text-muted-foreground">加入班级，学习课程，向教材提问，获取个性化学习体验。</p>
                </div>
              </div>
            </button>

            <div className="space-y-2">
              <Label htmlFor="email">邮箱</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="请输入教育邮箱"
                  className="pl-10"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="code">验证码</Label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="code"
                    placeholder="请输入验证码"
                    className="pl-10"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") register();
                    }}
                  />
                </div>
                <Button
                  variant="outline"
                  size="default"
                  className="shrink-0"
                  onClick={sendCode}
                  disabled={sending || cooldown > 0}
                >
                  {cooldown > 0 ? `${cooldown}s` : "获取验证码"}
                </Button>
              </div>
            </div>

            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                className="rounded border-border"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
              />
              <span className="text-muted-foreground">记住我</span>
            </label>

            <Button
              className="w-full bg-primary hover:bg-primary/90 mt-4"
              size="lg"
              disabled={!role}
              onClick={register}
            >
              {submitting ? "注册中..." : "继续注册"}
            </Button>

            <p className="text-center text-xs text-muted-foreground mt-4">
              注册即表示你同意我们的{" "}
              <Link href="#" className="text-primary hover:underline">《服务条款》</Link>
              {" "}与{" "}
              <Link href="#" className="text-primary hover:underline">《隐私政策》</Link>
            </p>
          </CardContent>
        </Card>

        {/* Right: Info panel */}
        <div className="hidden md:flex flex-col justify-center space-y-6 p-6">
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-white border border-border shadow-sm">
              <div className="flex items-center gap-3 mb-2">
                <GraduationCap className="w-5 h-5 text-primary" />
                <span className="font-semibold text-foreground">教师功能</span>
              </div>
              <p className="text-sm text-muted-foreground">上传教材、创建班级、管理 Skill、查看学生使用数据</p>
            </div>
            <div className="p-4 rounded-xl bg-white border border-border shadow-sm">
              <div className="flex items-center gap-3 mb-2">
                <Users className="w-5 h-5 text-accent" />
                <span className="font-semibold text-foreground">学生功能</span>
              </div>
              <p className="text-sm text-muted-foreground">加入班级、浏览知识库、向教材提问、获取个性化学习体验</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterInner />
    </Suspense>
  );
}
