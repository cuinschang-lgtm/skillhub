import Link from "next/link";
import { BookOpen, Cpu, MessageCircle, ArrowRight, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

function FeatureCard({ icon: Icon, title, description }: { icon: React.ElementType; title: string; description: string }) {
  return (
    <div className="flex items-start gap-4 p-6 rounded-2xl bg-white border border-border shadow-sm hover:shadow-md transition-shadow">
      <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-secondary flex items-center justify-center">
        <Icon className="w-6 h-6 text-primary" />
      </div>
      <div>
        <h3 className="font-semibold text-foreground mb-1">{title}</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

function StatsBar() {
  return (
    <div className="flex flex-wrap items-center gap-6 lg:gap-8 px-8 py-5 rounded-2xl bg-white border border-border shadow-sm">
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">已公开的教材 Skill 数量</span>
        <span className="text-3xl font-bold text-foreground">12,842</span>
        <span className="text-xs text-primary bg-secondary px-2 py-0.5 rounded-full font-medium">+217 本周新增</span>
      </div>
      <div className="flex -space-x-2">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 to-accent/30 border-2 border-white" />
        ))}
      </div>
      <div className="ml-auto text-sm text-muted-foreground">
        来自全球 <span className="font-semibold text-foreground">6,193</span> 位教育者的贡献
      </div>
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-foreground">SkillHub</span>
          </div>
          <nav className="hidden md:flex items-center gap-8">
            <Link href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">功能</Link>
            <Link href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">解决方案</Link>
            <Link href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">定价</Link>
            <Link href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">文档</Link>
            <Link href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">关于我们</Link>
          </nav>
          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost" size="sm">登录</Button>
            </Link>
            <Link href="/register">
              <Button size="sm" className="bg-primary hover:bg-primary/90">免费注册</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 pt-20 pb-16">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <h1 className="text-4xl lg:text-5xl font-bold text-foreground leading-tight">
              让每一本教材
              <br />
              成为<span className="text-primary">可对话的知识库</span>
            </h1>
            <p className="mt-6 text-lg text-muted-foreground leading-relaxed max-w-lg">
              上传教材，智能编译，生成高质量的知识 Skill。
              <br />
              让 AI 基于你的教材回答问题，精准、可追溯、可控。
            </p>
            <div className="mt-8 flex items-center gap-4">
              <Link href="/register">
                <Button size="lg" className="bg-primary hover:bg-primary/90 gap-2">
                  开始免费体验 <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
              <Button variant="outline" size="lg" className="gap-2">
                查看演示 <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
          <div className="hidden lg:flex justify-center">
            <div className="w-80 h-64 rounded-3xl bg-gradient-to-br from-secondary via-white to-accent/10 border border-border shadow-lg flex items-center justify-center">
              <BookOpen className="w-24 h-24 text-primary/30" />
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-6 pb-16">
        <div className="grid md:grid-cols-3 gap-6">
          <FeatureCard
            icon={BookOpen}
            title="上传教材"
            description="支持 PDF 上传，自动识别目录与结构，智能解析教材内容"
          />
          <FeatureCard
            icon={Cpu}
            title="编译处理"
            description="采用 Pipeline 处理与质量评估，生成高质量知识 Skill"
          />
          <FeatureCard
            icon={MessageCircle}
            title="智能问答"
            description="基于你的教材进行问答，集章可溯源，精准可靠"
          />
        </div>
      </section>

      {/* Stats */}
      <section className="max-w-7xl mx-auto px-6 pb-20">
        <StatsBar />
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-white">
        <div className="max-w-7xl mx-auto px-6 py-8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-primary flex items-center justify-center">
              <BookOpen className="w-3 h-3 text-white" />
            </div>
            <span className="text-sm font-semibold text-foreground">SkillHub</span>
          </div>
          <p className="text-sm text-muted-foreground">© 2026 SkillHub. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
