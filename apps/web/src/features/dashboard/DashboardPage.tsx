import { useQuery } from "@tanstack/react-query";
import { api } from "@/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Target, Eye, Globe, MessageSquare, Activity } from "lucide-react";
import type { DashboardSummary } from "@/types";

const cards = [
  { key: "active_target_accounts" as const, label: "活跃目标", icon: Target, color: "text-blue-600" },
  { key: "monitoring_accounts" as const, label: "监控账号", icon: Eye, color: "text-green-600" },
  { key: "browser_profiles" as const, label: "浏览器配置", icon: Globe, color: "text-purple-600" },
  { key: "total_tweets" as const, label: "推文总数", icon: MessageSquare, color: "text-orange-600" },
  { key: "workers_online" as const, label: "在线 Worker", icon: Activity, color: "text-emerald-600" },
];

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => api.dashboard.summary(),
    refetchInterval: 30_000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">仪表盘</h1>
        <p className="text-muted-foreground">LittleGankNews 系统概览</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {cards.map((c) => (
          <Card key={c.key}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{c.label}</CardTitle>
              <c.icon className={`h-4 w-4 ${c.color}`} />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <div className="text-2xl font-bold">{(data as DashboardSummary)?.[c.key] ?? 0}</div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
