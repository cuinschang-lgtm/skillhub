"use client";

import Link from "next/link";
import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen, GraduationCap, Users, Mail, Lock, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

function RegisterInner() {
  const [role, setRole] = useState<"teacher" | "student" | null>(null);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const sp = useSearchParams();
  const nextPath = useMemo(() => sp.get("next") || "/dashboard", [sp]);

  async function register() {
    setError("");
    if (!role) {
      setError("请选择身份");
      return;
    }
    const v = email.trim().toLowerCase();
    if (!v) {
      setError("请输入邮箱");
      return;
    }
    if (password.length < 8) {
      setError("密码长度至少 8 位");
      return;
    }
    if (password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: v,
          password,
          displayName: displayName.trim(),
          role,
        }),
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
        {/* Left: register form */}
        <Card className="shadow-[var(--shadow-panel)] border-border">
          <CardHeader className="text-center pb-2">
            <div className="flex justify-center mb-4">
              <div className="w-10 h-10 rounded-md bg-gradient-to-b from-[var(--metal-hi)] to-[var(--metal-lo)] shadow-[var(--edge-light)] flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-primary" />
              </div>
            </div>
            <h1 className="text-2xl font-bold text-foreground">创建账户</h1>
            <p className="text-sm text-muted-foreground mt-1">请选择你的身份角色并设置密码</p>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {error ? (
              <div className="text-sm text-destructive bg-destructive/10 border border-destructive/30 rounded-lg px-3 py-2">
                {error}
              </div>
            ) : null}
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setRole("teacher")}
                className={`p-4 rounded-xl border-2 text-left transition-colors ${
                  role === "teacher"
                    ? "border-primary bg-secondary"
                    : "border-border hover:border-primary/50"
                }`}
              >
                <div className="flex items-center gap-2">
                  <GraduationCap className="w-5 h-5 text-primary" />
                  <p className="font-semibold text-foreground">我是教师</p>
                </div>
                <p className="text-xs text-muted-foreground mt-1">上传教材、创建班级</p>
              </button>

              <button
                type="button"
                onClick={() => setRole("student")}
                className={`p-4 rounded-xl border-2 text-left transition-colors ${
                  role === "student"
                    ? "border-primary bg-secondary"
                    : "border-border hover:border-primary/50"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-accent" />
                  <p className="font-semibold text-foreground">我是学生</p>
                </div>
                <p className="text-xs text-muted-foreground mt-1">浏览知识库、向教材提问</p>
              </button>
            </div>

            <form
              className="space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                register();
              }}
            >
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
                    autoComplete="email"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="displayName">昵称（选填）</Label>
                <div className="relative">
                  <UserRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="displayName"
                    placeholder="你的昵称"
                    className="pl-10"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    autoComplete="nickname"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">密码</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="至少 8 位"
                    className="pl-10"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">确认密码</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="再次输入密码"
                    className="pl-10"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                </div>
              </div>

              <Button
                type="submit"
                className="w-full bg-primary hover:bg-primary/90 mt-4"
                size="lg"
                disabled={submitting || !role}
              >
                {submitting ? "注册中..." : "创建账户"}
              </Button>
            </form>

            <p className="text-center text-sm text-muted-foreground">
              已有账号？{" "}
              <Link href="/login" className="text-primary hover:underline font-medium">直接登录</Link>
            </p>

            <p className="text-center text-xs text-muted-foreground mt-2">
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
            <div className="p-4 rounded-xl bg-card border border-border shadow-sm">
              <div className="flex items-center gap-3 mb-2">
                <GraduationCap className="w-5 h-5 text-primary" />
                <span className="font-semibold text-foreground">教师功能</span>
              </div>
              <p className="text-sm text-muted-foreground">上传教材、创建班级、管理 Skill、查看学生使用数据</p>
            </div>
            <div className="p-4 rounded-xl bg-card border border-border shadow-sm">
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
