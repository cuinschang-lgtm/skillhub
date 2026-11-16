import Link from "next/link";
import { BookOpen, Cpu, MessageCircle, ArrowRight, FileText, Layers, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

function FeatureCard({ icon: Icon, title, description }: { icon: React.ElementType; title: string; description: string }) {
  return (
    <div className="p-6 rounded-2xl bg-card border border-border shadow-[var(--shadow-panel)]">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-md bg-gradient-to-b from-[var(--metal-hi)] to-[var(--metal-lo)] shadow-[var(--edge-light)] flex items-center justify-center">
          <Icon className="w-5 h-5 text-primary" />
        </div>
        <h3 className="font-heading text-lg text-foreground">{title}</h3>
      </div>
      <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
    </div>
  );
}

const steps = [
  { step: "01", title: "上传教材", description: "拖入 PDF，自动识别目录结构与文本层，扫描版走 OCR" },
  { step: "02", title: "编译为 Skill", description: "章节切分、知识抽取、组装为可加载的 Skill 目录" },
  { step: "03", title: "真实测评", description: "自动出题做 WITH / WITHOUT 对比，评分可查、回答可溯源" },
];

/** Ribbon signature：夜色天际光带 —— 慢光条纹 + 地平线上一排「亮窗」光点（非星空、非月亮） */
function NightSky() {
  return (
    <div aria-hidden className="absolute inset-0 overflow-hidden rounded-2xl bg-[linear-gradient(to_bottom,oklch(20%_0.04_258),oklch(13.2%_0.022_258)_55%,oklch(16%_0.03_200))]">
      {/* 慢光条纹 */}
      <div className="absolute inset-x-0 top-[18%] h-px bg-gradient-to-r from-transparent via-oklch(72%_0.02_255/0.35) to-transparent" />
      <div className="absolute inset-x-0 top-[34%] h-px bg-gradient-to-r from-transparent via-oklch(72%_0.02_255/0.18) to-transparent" />
      <div className="absolute inset-x-0 top-[52%] h-px bg-gradient-to-r from-transparent via-oklch(72%_0.02_255/0.1) to-transparent" />
      {/* 地平线 */}
      <div className="absolute inset-x-0 bottom-[38%] h-px bg-oklch(27%_0.018_258)" />
      {/* 一排亮窗光点 */}
      <div className="absolute inset-x-0 bottom-[38%] flex justify-center gap-10 -translate-y-1/2">
        {[14, 30, 52, 44, 68, 36, 58, 24, 46].map((h, i) => (
          <div key={i} className="w-px relative" style={{ height: `${h}px` }}>
            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-oklch(82%_0.095_68/0.55) to-transparent" />
            <div className="absolute -top-0.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-primary shadow-[0_0_8px_oklch(82%_0.095_68/0.8)]" />
          </div>
        ))}
      </div>
      {/* 地面反光 */}
      <div className="absolute inset-x-0 bottom-0 h-[38%] bg-gradient-to-t from-oklch(11%_0.02_258) to-transparent" />
    </div>
  );
}

/** 机加工产品面板：编译管道作为三级「推子」部件，点亮的工作位 = 当前阶段 */
function MachinedPipeline() {
  const parts = [
    { icon: FileText, label: "上传", meta: "PDF · OCR", lit: true },
    { icon: Layers, label: "章节切片", meta: "切分 · 抽取", lit: true },
    { icon: Sparkles, label: "Skill", meta: "组装 · 测评", lit: false },
  ];
  return (
    <div className="relative rounded-2xl bg-card border border-border shadow-[var(--shadow-panel)] p-6">
      <div className="flex items-center justify-between mb-5">
        <span className="font-heading text-sm text-foreground">编译管道</span>
        <span className="font-mono text-[11px] text-muted-foreground">pipeline · running</span>
      </div>
      <div className="space-y-4">
        {parts.map((part) => (
          <div key={part.label} className="flex items-center gap-4">
            <div className={`w-9 h-9 rounded-md bg-gradient-to-b from-[var(--metal-hi)] to-[var(--metal-lo)] shadow-[var(--edge-light)] flex items-center justify-center shrink-0`}>
              <part.icon className={`w-4 h-4 ${part.lit ? "text-primary" : "text-muted-foreground"}`} />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm text-foreground">{part.label}</span>
                <span className="font-mono text-[11px] text-muted-foreground">{part.meta}</span>
              </div>
              {/* 推子轨道 + 点亮的指示线 */}
              <div className="h-1.5 rounded-full bg-[var(--metal-lo)] relative overflow-hidden">
                <div
                  className={`absolute inset-y-0 left-0 rounded-full ${part.lit ? "bg-primary shadow-[0_0_6px_oklch(82%_0.095_68/0.6)]" : "bg-[var(--metal-hi)]"}`}
                  style={{ width: part.lit ? "78%" : "22%" }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-5 pt-4 border-t border-border flex items-center justify-between">
        <span className="font-mono text-[11px] text-muted-foreground">3 chapters · 12 questions</span>
        <span className="font-mono text-[11px] text-primary">score 80/100</span>
      </div>
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-card/80 backdrop-blur-md border-b border-border">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-md bg-gradient-to-b from-[var(--metal-hi)] to-[var(--metal-lo)] shadow-[var(--edge-light)] flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-primary" />
            </div>
            <span className="font-heading text-lg text-foreground">SkillHub</span>
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
              <Button size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground rounded-full">免费注册</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero：夜色天际 + 机加工产品面板；首屏 1280x800 内完整可见 */}
      <section className="max-w-6xl mx-auto px-6 pt-16 pb-14">
        <div className="relative rounded-2xl border border-border overflow-hidden">
          <div className="relative grid lg:grid-cols-2 gap-10 items-center p-8 lg:p-12">
            <NightSky />
            <div className="relative">
              <p className="font-mono text-[11px] text-muted-foreground mb-4">PDF → 章节 → Skill → 测评</p>
              <h1 className="text-4xl lg:text-5xl text-foreground leading-[1.08]">
                让每一本教材
                <br />
                成为<span className="text-primary">可对话的知识库</span>
              </h1>
              <p className="mt-5 text-lg text-muted-foreground leading-relaxed max-w-lg">
                上传 PDF 教材，编译成 AI Skill，再用真实测评检验它是否真的有用。
              </p>
              <div className="mt-8 flex items-center gap-4">
                <Link href="/register" className="inline-flex">
                  <Button size="lg" className="bg-primary hover:bg-primary/90 text-primary-foreground gap-2 rounded-full shadow-[var(--shadow-part)]">
                    开始免费体验 <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
                <Link href="/login" className="inline-flex">
                  <Button variant="outline" size="lg" className="rounded-full border-border bg-card">演示登录</Button>
                </Link>
              </div>
            </div>
            <div className="relative hidden lg:block">
              <MachinedPipeline />
            </div>
          </div>
        </div>
      </section>

      {/* 工作流程 */}
      <section id="how" className="max-w-6xl mx-auto px-6 pb-16">
        <div className="grid md:grid-cols-3 gap-6">
          {steps.map((s) => (
            <div key={s.step} className="p-6 rounded-2xl bg-card border border-border">
              <div className="font-mono text-xs text-primary mb-3">{s.step}</div>
              <h3 className="font-heading text-lg text-foreground mb-1.5">{s.title}</h3>
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
            description="有文字层直接解析，扫描版走 MinerU OCR"
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
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded bg-gradient-to-b from-[var(--metal-hi)] to-[var(--metal-lo)] flex items-center justify-center">
              <BookOpen className="w-3 h-3 text-primary" />
            </div>
            <span className="text-sm text-foreground">SkillHub</span>
          </div>
          <p className="text-sm text-muted-foreground">© 2026 SkillHub</p>
        </div>
      </footer>
    </div>
  );
}
