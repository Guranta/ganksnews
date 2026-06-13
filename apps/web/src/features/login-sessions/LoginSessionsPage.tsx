import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api";
import type { LoginSessionItem, MonitoringAccount, BrowserProfile } from "@/types";
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
  DialogFooter,
  DialogDescription,
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Plus, CheckCircle, XCircle, RefreshCw, Monitor, ExternalLink } from "lucide-react";
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
  const [confirmAction, setConfirmAction] = useState<{ id: string; type: "complete" | "cancel" } | null>(null);
  const [selectedProfileId, setSelectedProfileId] = useState<string>("");
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["login-sessions", page, statusFilter],
    queryFn: () =>
      api.loginSessions.list({
        page,
        page_size: 20,
        status: statusFilter !== "all" ? statusFilter : undefined,
      }),
  });

  const { data: profilesData } = useQuery({
    queryKey: ["browser-profiles-for-login"],
    queryFn: () => api.browserProfiles.list({ page: 1, page_size: 100 }),
  });

  const { data: accountsData } = useQuery({
    queryKey: ["monitoring-accounts-for-login"],
    queryFn: () => api.monitoringAccounts.list({ page: 1, page_size: 100 }),
  });

  const hasRunningSession = data?.items.some((s: LoginSessionItem) => s.status === "running") ?? false;

  const createMutation = useMutation({
    mutationFn: () =>
      api.loginSessions.create({
        browser_profile_id: selectedProfileId && selectedProfileId !== "none" ? selectedProfileId : undefined,
        monitoring_account_id: selectedAccountId && selectedAccountId !== "none" ? selectedAccountId : undefined,
      }),
    onSuccess: (resp) => {
      queryClient.invalidateQueries({ queryKey: ["login-sessions"] });
      setDialogOpen(false);
      setSelectedProfileId("");
      setSelectedAccountId("");
      toast.success("Login session 已创建，远程浏览器已启动");
      if (resp?.vnc_url) {
        window.open(resp.vnc_url, "_blank", "noopener,noreferrer");
      }
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

  useEffect(() => {
    const es = new EventSource("/api/v1/events/stream");
    es.onmessage = () => {
      queryClient.invalidateQueries({ queryKey: ["login-sessions"] });
    };
    es.onerror = () => {};
    return () => { es.close(); };
  }, [queryClient]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Login Sessions</h1>
          <p className="text-muted-foreground">
            服务器远程浏览器登录 — 在服务器端 Chromium 中手动登录 X/Twitter，系统不保存密码
          </p>
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
              <Button size="sm" disabled={hasRunningSession}>
                <Plus className="h-4 w-4 mr-2" /> 新建
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>创建 Login Session</DialogTitle>
                <DialogDescription>
                  创建新的远程浏览器登录会话。系统将启动远程 Chromium，你可以通过 noVNC 完成 X/Twitter 登录。同一时间只允许一个运行中的会话。
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-2">
                <div>
                  <label className="text-sm font-medium">关联 Browser Profile（可选）</label>
                  <Select value={selectedProfileId} onValueChange={setSelectedProfileId}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="选择 Profile" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">不关联</SelectItem>
                      {(profilesData?.items ?? []).map((p: BrowserProfile) => (
                        <SelectItem key={p.id} value={p.id}>{p.name} ({p.status})</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-sm font-medium">关联 Monitoring Account（可选）</label>
                  <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="选择 Account" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">不关联</SelectItem>
                      {(accountsData?.items ?? []).map((a: MonitoringAccount) => (
                        <SelectItem key={a.id} value={a.id}>{a.username} ({a.status})</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
                <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
                  {createMutation.isPending ? "创建中..." : "确认创建"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" /> 刷新
          </Button>
        </div>
      </div>

      {hasRunningSession && (
        <Card className="border-primary/50 bg-primary/5">
          <CardContent className="py-3">
            <div className="flex items-center gap-2 text-sm">
              <Monitor className="h-4 w-4 text-primary" />
              <span className="font-medium">当前有运行中的远程浏览器会话</span>
              {data?.items
                .filter((s: LoginSessionItem) => s.status === "running" && s.vnc_url)
                .map((s: LoginSessionItem) => (
                  <a
                    key={s.id}
                    href={s.vnc_url!}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-primary hover:underline font-medium"
                  >
                    <ExternalLink className="h-3 w-3" /> 打开远程浏览器
                  </a>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>Profile</TableHead>
                <TableHead>Account</TableHead>
                <TableHead>VNC</TableHead>
                <TableHead>开始时间</TableHead>
                <TableHead>完成时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow><TableCell colSpan={8} className="text-center py-8">加载中...</TableCell></TableRow>
              ) : (
                data?.items.map((s: LoginSessionItem) => (
                  <TableRow key={s.id} className={s.status === "running" ? "bg-primary/5" : undefined}>
                    <TableCell className="font-mono text-xs">{s.id.slice(0, 8)}...</TableCell>
                    <TableCell>
                      <Badge variant={STATUS_COLORS[s.status] || "secondary"}>{s.status}</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{s.browser_profile_id?.slice(0, 8) || "—"}</TableCell>
                    <TableCell className="font-mono text-xs">{s.monitoring_account_id?.slice(0, 8) || "—"}</TableCell>
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
                            <Button size="sm" variant="outline" onClick={() => setConfirmAction({ id: s.id, type: "complete" })}>
                              <CheckCircle className="h-3 w-3 mr-1" /> 完成
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => setConfirmAction({ id: s.id, type: "cancel" })}>
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
                <TableRow><TableCell colSpan={8} className="text-center text-muted-foreground py-8">暂无登录会话</TableCell></TableRow>
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

      <AlertDialog open={confirmAction !== null} onOpenChange={(open) => { if (!open) setConfirmAction(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmAction?.type === "complete" ? "确认完成登录" : "确认取消会话"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmAction?.type === "complete"
                ? "确认已在远程浏览器中完成 X/Twitter 登录？完成后远程浏览器将关闭，关联的 Profile 和 Account 将标记为可用。"
                : "确认取消此登录会话？远程浏览器将关闭，token 将立即失效。"}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>再想想</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (!confirmAction) return;
                if (confirmAction.type === "complete") {
                  completeMutation.mutate(confirmAction.id);
                } else {
                  cancelMutation.mutate(confirmAction.id);
                }
                setConfirmAction(null);
              }}
            >
              确认
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
