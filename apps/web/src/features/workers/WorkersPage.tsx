import { useQuery } from "@tanstack/react-query";
import { api } from "@/api";
import type { WorkerSummary } from "@/types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatRelativeTime, statusColor } from "@/lib/format";

export default function WorkersPage() {
  const { data: workers, isLoading } = useQuery({
    queryKey: ["workers"],
    queryFn: () => api.workers.list(),
    refetchInterval: 10000,
  });

  const { data: summaries } = useQuery({
    queryKey: ["workers", "summary"],
    queryFn: () => api.workers.summary(),
    refetchInterval: 10000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Workers</h1>
        <p className="text-muted-foreground">后台工作进程状态</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {summaries?.map((s) => (
          <WorkerSummaryCard key={s.worker_type} summary={s} />
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>所有 Workers</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Worker ID</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>当前任务</TableHead>
                  <TableHead>最后心跳</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {workers?.map((w) => (
                  <TableRow key={w.id}>
                    <TableCell className="font-mono text-sm">{w.worker_id}</TableCell>
                    <TableCell><Badge variant="outline">{w.worker_type}</Badge></TableCell>
                    <TableCell><Badge variant={workerStatusColor(w.status)}>{w.status}</Badge></TableCell>
                    <TableCell className="text-sm text-muted-foreground max-w-xs truncate">{w.current_task || "—"}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{formatRelativeTime(w.updated_at)}</TableCell>
                  </TableRow>
                ))}
                {workers && workers.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground py-8">暂无 Worker 运行</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function WorkerSummaryCard({ summary }: { summary: WorkerSummary }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{summary.worker_type}</CardTitle>
        <Badge variant={summary.running > 0 ? "default" : "secondary"}>{summary.running > 0 ? "运行中" : "离线"}</Badge>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{summary.running} / {summary.total}</div>
        <p className="text-xs text-muted-foreground">
          运行 {summary.running} · 停止 {summary.stopped} · 错误 {summary.error}
        </p>
      </CardContent>
    </Card>
  );
}

function workerStatusColor(status: string): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "running":
      return "default";
    case "stopped":
      return "secondary";
    case "error":
      return "destructive";
    default:
      return "outline";
  }
}
