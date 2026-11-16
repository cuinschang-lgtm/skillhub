"use client";

import Link from "next/link";
import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen, Mail, Lock, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

function LoginInner() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [loggingIn, setLoggingIn] = useState(false);
  const [demoLoggingIn, setDemoLoggingIn] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const sp = useSearchParams();
  const nextPath = useMemo(() => sp.get("next") || "/dashboard", [sp]);

  async function submitLogin() {
    setError("");
    const v = email.trim().toLowerCase();
    if (!v) {
      setError("请输入邮箱");
      return;
    }
    if (!password) {
      setError("请输入密码");
      return;
    }
    setLoggingIn(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: v, password, remember }),
        credentials: "include",
      });
      const data = (await res.json().catch(() => null)) as { message?: string } | null;
      if (!res.ok) {
        setError(data?.message || "登录失败");
        return;
      }
      router.replace(nextPath);
    } catch {
      setError("网络错误，请稍后重试");
    } finally {
      setLoggingIn(false);
    }
  }

  async function demoLogin() {
    setError("");
    const v = email.trim().toLowerCase();
    if (!v) {
      setError("请先输入邮箱（演示登录任意邮箱均可）");
      return;
    }
    setDemoLoggingIn(true);
    try {
      const res = await fetch("/api/auth/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: v, code: "123456", role: "teacher", remember }),
        credentials: "include",
      });
      const data = (await res.json().catch(() => null)) as { message?: string } | null;
      if (!res.ok) {
        setError(data?.message || "演示登录失败");
        return;
      }
      router.replace(nextPath);
    } catch {
      setError("网络错误，请稍后重试");
    } finally {
      setDemoLoggingIn(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--background)] flex items-center justify-center p-6">
      <Card className="w-full max-w-md shadow-lg border-border">
        <CardHeader className="text-center pb-2">
          <div className="flex justify-center mb-4">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-foreground">欢迎回来 👋</h1>
          <p className="text-sm text-muted-foreground mt-1">登录你的账户，继续探索知识的边界</p>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          {error ? (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          ) : null}
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              submitLogin();
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
              <Label htmlFor="password">密码</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder="请输入密码"
                  className="pl-10"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-border"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                />
                <span className="text-muted-foreground">记住我</span>
              </label>
              <Link href="/register" className="text-primary hover:underline">没有账号？</Link>
            </div>

            <Button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90"
              size="lg"
              disabled={loggingIn || demoLoggingIn}
            >
              {loggingIn ? "登录中..." : "登录"}
            </Button>
          </form>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-card px-3 text-xs text-muted-foreground">或</span>
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            className="w-full"
            size="lg"
            onClick={demoLogin}
            disabled={loggingIn || demoLoggingIn}
          >
            <Sparkles className="w-4 h-4" />
            {demoLoggingIn ? "进入演示环境..." : "演示登录（免注册体验）"}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            还没有账号？{" "}
            <Link href="/register" className="text-primary hover:underline font-medium">立即注册</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginInner />
    </Suspense>
  );
}
