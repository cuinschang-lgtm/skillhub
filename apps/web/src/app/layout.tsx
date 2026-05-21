import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SkillHub - 让每一本教材成为可对话的知识库",
  description: "上传教材，智能编译，生成高质量的知识 Skill。让 AI 基于你的教材回答问题，精准、可追溯、可控。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
