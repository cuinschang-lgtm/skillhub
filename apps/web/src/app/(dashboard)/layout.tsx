"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, Upload, Library, MessageCircle, Settings, LayoutDashboard, Bell, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const sidebarItems = [
  { href: "/knowledge", icon: Library, label: "知识库" },
  { href: "/chat", icon: MessageCircle, label: "我的问答" },
  { href: "/upload", icon: Upload, label: "教材上传" },
  { href: "/", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/settings", icon: Settings, label: "设置" },
];

function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 border-r border-border bg-white flex flex-col h-full">
      <div className="p-4 flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
          <BookOpen className="w-4 h-4 text-white" />
        </div>
        <span className="text-lg font-bold text-foreground">SkillHub</span>
      </div>
      <nav className="flex-1 px-3 py-2 space-y-1">
        {sidebarItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-secondary text-primary font-medium"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-border">
        <Button variant="ghost" size="sm" className="w-full justify-start text-muted-foreground text-xs">
          帮助中心
        </Button>
      </div>
    </aside>
  );
}

function TopBar() {
  return (
    <header className="h-14 border-b border-border bg-white flex items-center justify-between px-6">
      <div />
      <div className="flex items-center gap-4">
        <button className="relative p-2 rounded-lg hover:bg-muted transition-colors">
          <Bell className="w-5 h-5 text-muted-foreground" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full" />
        </button>
        <div className="flex items-center gap-2 cursor-pointer">
          <Avatar className="w-8 h-8">
            <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">张</AvatarFallback>
          </Avatar>
          <span className="text-sm font-medium text-foreground">张老师</span>
          <ChevronDown className="w-3 h-3 text-muted-foreground" />
        </div>
      </div>
    </header>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen flex bg-[var(--background)]">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
