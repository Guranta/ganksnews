import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api";
import type { MonitoringAccount, MonitoringAccountStatus, MonitoringAccountCreate, MonitoringAccountUpdate } from "@/types";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Trash2, Pencil, LogIn } from "lucide-react";
import { formatRelativeTime, statusColor } from "@/lib/format";
import { toast } from "sonner";

const STATUS_LABELS: Record<string, string> = {
  active: "已登录",
  needs_login: "需要登录",
  challenged: "需验证",
  suspended: "已封禁",
  inactive: "未激活",
};

export default function MonitoringAccountsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [editAcc, setEditAcc] = useState<MonitoringAccount | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["monitoring-accounts", page],
    queryFn: () => api.monitoringAccounts.list({ page, page_size: 20 }),
  });

  const createMutation = useMutation({
    mutationFn: (data: MonitoringAccountCreate) => api.monitoringAccounts.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monitoring-accounts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setCreateOpen(false);
      toast.success("监控账号已创建");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const createWithLoginMutation = useMutation({
    mutationFn: (data: MonitoringAccountCreate) => api.monitoringAccounts.createWithLoginSession(data),
    onSuccess: (resp) => {
      queryClient.invalidateQueries({ queryKey: ["monitoring-accounts"] });
      queryClient.invalidateQueries({ queryKey: ["browser-profiles"] });
      queryClient.invalidateQueries({ queryKey: ["login-sessions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setCreateOpen(false);
      toast.success("监控账号已创建，远程浏览器已启动");
      if (resp.vnc_url) {
        window.open(resp.vnc_url, "_blank");
      }
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: MonitoringAccountUpdate }) =>
      api.monitoringAccounts.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monitoring-accounts"] });
      setEditAcc(null);
      toast.success("监控账号已更新");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.monitoringAccounts.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monitoring-accounts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("监控账号已删除");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">监控账号</h1>
          <p className="text-muted-foreground">用于登录和监听的 Twitter/X 账号</p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button><LogIn className="h-4 w-4 mr-2" />添加并登录</Button>
          </DialogTrigger>
          <DialogContent>
            <CreateMonitoringForm
              onSubmit={(d) => createWithLoginMutation.mutate(d)}
              onSkipLogin={(d) => createMutation.mutate(d)}
              isLoading={createWithLoginMutation.isPending || createMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>用户名</TableHead>
                  <TableHead>显示名称</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>最后登录检查</TableHead>
                  <TableHead>备注</TableHead>
                  <TableHead className="w-[80px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((acc) => (
                  <TableRow key={acc.id}>
                    <TableCell className="font-medium">
                      <a href={`https://x.com/${acc.username}`} target="_blank" rel="noopener noreferrer" className="hover:underline text-blue-600">
                        @{acc.username}
                      </a>
                    </TableCell>
                    <TableCell>{acc.display_name || "—"}</TableCell>
                    <TableCell><Badge variant={statusColor(acc.status)}>{STATUS_LABELS[acc.status] || acc.status}</Badge></TableCell>
                    <TableCell className="text-muted-foreground text-sm">{formatRelativeTime(acc.last_login_check_at)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground max-w-xs truncate">{acc.notes || "—"}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button size="icon" variant="ghost" onClick={() => setEditAcc(acc)}>
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => { if (confirm(`确认删除 @${acc.username}？`)) deleteMutation.mutate(acc.id); }}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {data && data.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground py-8">暂无监控账号</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">共 {data?.total ?? 0} 个账号</p>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>上一页</Button>
            <span className="flex items-center px-2 text-sm text-muted-foreground">第 {page} / {totalPages} 页</span>
            <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>下一页</Button>
          </div>
        </div>
      )}

      <Dialog open={!!editAcc} onOpenChange={(o) => !o && setEditAcc(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑 @{editAcc?.username}</DialogTitle>
          </DialogHeader>
          {editAcc && (
            <EditMonitoringForm
              account={editAcc}
              onSubmit={(d) => updateMutation.mutate({ id: editAcc.id, data: d })}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CreateMonitoringForm({ onSubmit, onSkipLogin, isLoading }: {
  onSubmit: (data: MonitoringAccountCreate) => void;
  onSkipLogin: (data: MonitoringAccountCreate) => void;
  isLoading: boolean;
}) {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [notes, setNotes] = useState("");

  const formData: MonitoringAccountCreate = {
    username,
    display_name: displayName || undefined,
    notes: notes || undefined,
  };

  return (
    <>
      <DialogHeader>
        <DialogTitle>添加并登录监控账号</DialogTitle>
        <DialogDescription>
          输入用户名后点击"添加并登录"，系统将自动创建账号、浏览器配置和远程登录会话，然后打开远程浏览器供你完成 X/Twitter 登录。
        </DialogDescription>
      </DialogHeader>
      <div className="space-y-4">
        <div className="space-y-2">
          <Label>用户名 *</Label>
          <Input placeholder="monitoring_user" value={username} onChange={(e) => setUsername(e.target.value.replace(/^@/, ""))} />
        </div>
        <div className="space-y-2">
          <Label>显示名称</Label>
          <Input placeholder="可选显示名称" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>备注</Label>
          <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <DialogFooter className="flex gap-2 sm:justify-between">
        <Button
          variant="outline"
          onClick={() => onSkipLogin(formData)}
          disabled={isLoading}
        >
          仅创建账号
        </Button>
        <Button
          onClick={() => onSubmit(formData)}
          disabled={isLoading || !username.trim()}
        >
          {isLoading ? "创建中..." : "添加并登录"}
        </Button>
      </DialogFooter>
    </>
  );
}

function EditMonitoringForm({ account, onSubmit }: { account: MonitoringAccount; onSubmit: (data: MonitoringAccountUpdate) => void }) {
  const [displayName, setDisplayName] = useState(account.display_name || "");
  const [status, setStatus] = useState<MonitoringAccountStatus>(account.status);
  const [notes, setNotes] = useState(account.notes || "");

  return (
    <>
      <div className="space-y-4">
        <div className="space-y-2">
          <Label>显示名称</Label>
          <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>状态</Label>
          <Select value={status} onValueChange={(v) => setStatus(v as MonitoringAccountStatus)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="active">已登录</SelectItem>
              <SelectItem value="needs_login">需要登录</SelectItem>
              <SelectItem value="challenged">需验证</SelectItem>
              <SelectItem value="suspended">已封禁</SelectItem>
              <SelectItem value="inactive">未激活</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>备注</Label>
          <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <DialogFooter>
        <Button onClick={() => onSubmit({ display_name: displayName, status, notes })}>保存</Button>
      </DialogFooter>
    </>
  );
}
