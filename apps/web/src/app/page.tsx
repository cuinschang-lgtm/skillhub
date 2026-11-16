import Link from "next/link";
import { BookOpen, Cpu, MessageCircle, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

function FeatureCard({ icon: Icon, title, description }: { icon: React.ElementType; title: string; description: string }) {
  return (
    <div className="flex items-start gap-4 p-6 rounded-2xl bg-card border border-border shadow-sm hover:shadow-md transition-shadow">
      <div className="shrink-0 w-12 h-12 rounded-xl bg-secondary flex items-center justify-center">
        <Icon className="w-6 h-6 text-primary" />
      </div>
      <div>
        <h3 className="font-semibold text-foreground mb-1">{title}</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

const steps = [
  { step: "1", title: "上传教材", description: "拖入 PDF，自动识别目录结构与文本层" },
  { step: "2", title: "编译为 Skill", description: "切分章节、抽取知识、组装为可加载的 Skill 目录" },
  { step: "3", title: "真实测评", description: "自动出题做 WITH / WITHOUT 对比，评分可查、回答可溯源" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-card/80 backdrop-blur-md border-b border-border">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="text-lg font-bold text-foreground">SkillHub</span>
          </Link>
          <nav className="hidden md:flex items-center gap-8">
            <Link href="#how" className="text-sm text-muted-foreground hover:text-foreground transition-colors">工作流程</Link>
            <Link href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">功能</Link>
          </nav>
          <div className="flex items-center gap-3">
            <Link href="/login" className="inline-flex">
              <Button variant="ghost" size="sm">登录</Button>
            </Link>
            <Link href="/register" className="inline-flex">
              <Button size="sm" className="bg-primary hover:bg-primary/90">免费注册</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero：标题、一句话、主操作在 1280x800 首屏内完整可见 */}
      <section className="max-w-6xl mx-auto px-6 pt-20 pb-16">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <h1 className="text-4xl lg:text-5xl font-bold text-foreground leading-tight">
              让每一本教材
              <br />
              成为<span className="text-primary">可对话的知识库</span>
            </h1>
            <p className="mt-6 text-lg text-muted-foreground leading-relaxed max-w-lg">
              上传 PDF 教材，编译成 AI Skill，再用真实测评检验它是否真的有用。
            </p>
            <div className="mt-8 flex items-center gap-4">
              <Link href="/register" className="inline-flex">
                <Button size="lg" className="bg-primary hover:bg-primary/90 gap-2">
                  开始免费体验 <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
              <Link href="/login" className="inline-flex">
                <Button variant="outline" size="lg">演示登录</Button>
              </Link>
            </div>
          </div>
          <div className="hidden lg:flex justify-center">
            <div className="w-80 h-64 rounded-3xl bg-secondary border border-border shadow-lg flex flex-col items-center justify-center gap-4">
              <BookOpen className="w-20 h-20 text-primary/40" />
              <p className="text-sm text-muted-foreground">PDF → 章节切片 → 知识 Skill</p>
            </div>
          </div>
        </div>
      </section>

      {/* 工作流程（真实产品流程，非虚构数据） */}
      <section id="how" className="max-w-6xl mx-auto px-6 pb-16">
        <div className="grid md:grid-cols-3 gap-6">
          {steps.map((s) => (
            <div key={s.step} className="p-6 rounded-2xl bg-card border border-border">
              <div className="w-9 h-9 rounded-full bg-primary/10 text-primary font-semibold flex items-center justify-center mb-3">
                {s.step}
              </div>
              <h3 className="font-semibold text-foreground mb-1">{s.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{s.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-6 pb-20">
        <div className="grid md:grid-cols-3 gap-6">
          <FeatureCard
            icon={BookOpen}
            title="上传教材"
            description="支持 PDF 上传，有文字层直接解析，扫描版走 MinerU OCR"
          />
          <FeatureCard
            icon={Cpu}
            title="编译处理"
            description="章节切分、知识抽取与 Skill 组装，支持 DeepSeek / OpenAI / Anthropic"
          />
          <FeatureCard
            icon={MessageCircle}
            title="智能问答"
            description="基于教材章节回答问题，回答附章节出处，可追溯"
          />
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-card">
        <div className="max-w-6xl mx-auto px-6 py-8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-primary flex items-center justify-center">
              <BookOpen className="w-3 h-3 text-primary-foreground" />
            </div>
            <span className="text-sm font-semibold text-foreground">SkillHub</span>
          </div>
          <p className="text-sm text-muted-foreground">© 2026 SkillHub</p>
        </div>
      </footer>
    </div>
  );
}
