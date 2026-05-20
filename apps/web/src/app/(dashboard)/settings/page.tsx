"use client";

import { Key, User, Users, CreditCard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";

export default function SettingsPage() {
  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-foreground mb-6">设置</h1>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList>
          <TabsTrigger value="profile" className="gap-2"><User className="w-4 h-4" /> 个人信息</TabsTrigger>
          <TabsTrigger value="apikeys" className="gap-2"><Key className="w-4 h-4" /> API Key</TabsTrigger>
          <TabsTrigger value="classroom" className="gap-2"><Users className="w-4 h-4" /> 班级管理</TabsTrigger>
          <TabsTrigger value="billing" className="gap-2"><CreditCard className="w-4 h-4" /> 额度与计费</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold">个人信息</h2>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>显示名称</Label>
                <Input defaultValue="张老师" />
              </div>
              <div className="space-y-2">
                <Label>邮箱</Label>
                <Input defaultValue="zhang@university.edu.cn" disabled />
              </div>
              <div className="space-y-2">
                <Label>角色</Label>
                <Badge variant="secondary">教师</Badge>
              </div>
              <Button className="bg-primary hover:bg-primary/90">保存修改</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="apikeys">
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold">API Key 管理</h2>
              <p className="text-sm text-muted-foreground">配置你自己的 API Key，超出免费额度后使用</p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>DeepSeek API Key</Label>
                <div className="flex gap-2">
                  <Input type="password" placeholder="sk-..." className="flex-1" />
                  <Button variant="outline" size="sm">验证</Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label>OpenAI API Key</Label>
                <div className="flex gap-2">
                  <Input type="password" placeholder="sk-..." className="flex-1" />
                  <Button variant="outline" size="sm">验证</Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label>MinerU Token（OCR）</Label>
                <div className="flex gap-2">
                  <Input type="password" placeholder="token..." className="flex-1" />
                  <Button variant="outline" size="sm">验证</Button>
                </div>
              </div>
              <Button className="bg-primary hover:bg-primary/90">保存 Key</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="classroom">
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold">班级管理</h2>
              <p className="text-sm text-muted-foreground">创建班级并分享 Skill 给学生</p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-xl border border-border bg-muted/30">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">2024 高等数学 A 班</p>
                    <p className="text-xs text-muted-foreground mt-1">邀请码：HGS2024A · 32 名学生</p>
                  </div>
                  <Button variant="outline" size="sm">管理</Button>
                </div>
              </div>
              <Button variant="outline" className="w-full">+ 创建新班级</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="billing">
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold">额度与计费</h2>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-xl border border-border">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-foreground font-medium">本月教材编译</span>
                  <span className="text-sm text-muted-foreground">1 / 2 本</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full" style={{ width: "50%" }} />
                </div>
              </div>
              <div className="p-4 rounded-xl border border-border">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-foreground font-medium">本月问答次数</span>
                  <span className="text-sm text-muted-foreground">47 / 100 次</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-accent rounded-full" style={{ width: "47%" }} />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                教育邮箱认证用户享受双倍免费额度。超出后可配置自己的 API Key 继续使用。
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
