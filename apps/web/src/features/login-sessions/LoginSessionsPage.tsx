import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api";
import type { LoginSessionItem } from "@/types";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Plus, CheckCircle, XCircle, RefreshCw, Monitor } from "lucide-react";
import { toast } from "sonner";

const STATUS_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  pending: "secondary",
  running: "default",
  completed: "outline",
  failed: "destructive",
  cancelled: "secondary",
};

export default function LoginSessionsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["login-sessions", page, statusFilter],
    queryFn: () =>
      api.loginSessions.list({
        page,
        page_size: 20,
        status: statusFilter !== "all" ? statusFilter : undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: () => api.loginSessions.create({}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["login-sessions"] });
      setDialogOpen(false);
      toast.success("Login session 已创建");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const completeMutation = useMutation({
    mutationFn: (id: string) => api.loginSessions.complete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["login-sessions"] });
      toast.success("Login session 已完成");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => api.loginSessions.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["login-sessions"] });
      toast.success("Login session 已取消");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Login Sessions</h1>
          <p className="text-muted-foreground">浏览器登录会话管理</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
            <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="pending">pending</SelectItem>
              <SelectItem value="running">running</SelectItem>
              <SelectItem value="completed">completed</SelectItem>
              <SelectItem value="failed">failed</SelectItem>
              <SelectItem value="cancelled">cancelled</SelectItem>
            </SelectContent>
          </Select>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm"><Plus className="h-4 w-4 mr-2" /> 新建</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>创建 Login Session</DialogTitle>
              </DialogHeader>
              <p className="text-sm text-muted-foreground">
                创建新的浏览器登录会话。系统将启动远程浏览器，你可以通过 VNC 完成 X/Twitter 登录。
              </p>
              <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
                确认创建
              </Button>
            </DialogContent>
          </Dialog>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" /> 刷新
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>Profile</TableHead>
                <TableHead>VNC</TableHead>
                <TableHead>开始时间</TableHead>
                <TableHead>完成时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow><TableCell colSpan={7} className="text-center py-8">加载中...</TableCell></TableRow>
              ) : (
                data?.items.map((s: LoginSessionItem) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-mono text-xs">{s.id.slice(0, 8)}...</TableCell>
                    <TableCell>
                      <Badge variant={STATUS_COLORS[s.status] || "secondary"}>{s.status}</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{s.browser_profile_id?.slice(0, 8) || "—"}</TableCell>
                    <TableCell>
                      {s.vnc_url ? (
                        <a href={s.vnc_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline flex items-center gap-1">
                          <Monitor className="h-4 w-4" /> 打开
                        </a>
                      ) : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {s.started_at ? new Date(s.started_at).toLocaleString("zh-CN") : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {s.completed_at ? new Date(s.completed_at).toLocaleString("zh-CN") : "—"}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {(s.status === "pending" || s.status === "running") && (
                          <>
                            <Button size="sm" variant="outline" onClick={() => completeMutation.mutate(s.id)}>
                              <CheckCircle className="h-3 w-3 mr-1" /> 完成
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => cancelMutation.mutate(s.id)}>
                              <XCircle className="h-3 w-3 mr-1" /> 取消
                            </Button>
                          </>
                        )}
                        {s.error_message && (
                          <span className="text-xs text-destructive truncate max-w-[120px]" title={s.error_message}>{s.error_message}</span>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
              {data?.items.length === 0 && (
                <TableRow><TableCell colSpan={7} className="text-center text-muted-foreground py-8">暂无登录会话</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
          {data && data.total > 20 && (
            <div className="flex items-center justify-between px-4 py-3 border-t">
              <span className="text-sm text-muted-foreground">共 {data.total} 条</span>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</Button>
                <Button size="sm" variant="outline" disabled={page * 20 >= data.total} onClick={() => setPage(page + 1)}>下一页</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
