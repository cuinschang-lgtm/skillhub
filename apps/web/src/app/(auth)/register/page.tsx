"use client";

import Link from "next/link";
import { useState } from "react";
import { BookOpen, GraduationCap, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function RegisterPage() {
  const [role, setRole] = useState<"teacher" | "student" | null>(null);

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

            <Button
              className="w-full bg-primary hover:bg-primary/90 mt-4"
              size="lg"
              disabled={!role}
            >
              继续注册
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
