import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api";
import type { TargetAccount, TargetAccountStatus, TargetAccountCreate, TargetAccountUpdate, TargetAccountBulkImportResponse } from "@/types";
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
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Plus, Search, Upload, Trash2, Pencil } from "lucide-react";
import { formatRelativeTime, statusColor, priorityColor } from "@/lib/format";
import { toast } from "sonner";

export default function TargetAccountsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<TargetAccountStatus | "all">("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<TargetAccount | null>(null);
  const [importText, setImportText] = useState("");
  const [importResult, setImportResult] = useState<TargetAccountBulkImportResponse | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["target-accounts", page, search, statusFilter],
    queryFn: () =>
      api.targetAccounts.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: statusFilter === "all" ? undefined : statusFilter,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (data: TargetAccountCreate) => api.targetAccounts.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["target-accounts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setCreateOpen(false);
      toast.success("目标账号已创建");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const importMutation = useMutation({
    mutationFn: () => api.targetAccounts.import({ text: importText }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["target-accounts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setImportResult(result);
      toast.success(`导入完成：新增 ${result.created_count}，更新 ${result.updated_count}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: TargetAccountUpdate }) =>
      api.targetAccounts.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["target-accounts"] });
      setEditTarget(null);
      toast.success("目标账号已更新");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.targetAccounts.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["target-accounts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("目标账号已删除");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">目标账号</h1>
          <p className="text-muted-foreground">正在监控的 Twitter/X 账号</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={importOpen} onOpenChange={(o) => { setImportOpen(o); if (!o) { setImportText(""); setImportResult(null); } }}>
            <DialogTrigger asChild>
              <Button variant="outline"><Upload className="h-4 w-4 mr-2" />批量导入</Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>批量导入目标账号</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>用户名（每行一个）</Label>
                  <Textarea
                    rows={10}
                    placeholder={"VitalikButerin\ncz_binance\na16zcrypto"}
                    value={importText}
                    onChange={(e) => setImportText(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">每行一个用户名，@ 前缀会自动去除。</p>
                </div>
                {importResult && (
                  <div className="rounded-md border p-3 text-sm space-y-1">
                    <div>新增：<span className="font-semibold">{importResult.created_count}</span></div>
                    <div>更新：<span className="font-semibold">{importResult.updated_count}</span></div>
                    <div>失败：<span className="font-semibold">{importResult.failed_count}</span></div>
                    {importResult.errors && importResult.errors.length > 0 && (
                      <div className="text-destructive mt-2">
                        {importResult.errors.map((e, i) => <div key={i}>{e}</div>)}
                      </div>
                    )}
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button
                  onClick={() => importMutation.mutate()}
                  disabled={!importText.trim() || importMutation.isPending}
                >
                  {importMutation.isPending ? "导入中..." : "导入"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button><Plus className="h-4 w-4 mr-2" />添加账号</Button>
            </DialogTrigger>
            <CreateTargetDialog onSubmit={(d) => createMutation.mutate(d)} />
          </Dialog>
        </div>
      </div>

      <div className="flex gap-3 items-center">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索用户名..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-8"
          />
        </div>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v as typeof statusFilter); setPage(1); }}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部</SelectItem>
            <SelectItem value="active">活跃</SelectItem>
            <SelectItem value="paused">已暂停</SelectItem>
            <SelectItem value="archived">已归档</SelectItem>
          </SelectContent>
        </Select>
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
                  <TableHead>优先级</TableHead>
                  <TableHead>标签</TableHead>
                  <TableHead>最后发现</TableHead>
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
                    <TableCell><Badge variant={statusColor(acc.status)}>{acc.status}</Badge></TableCell>
                    <TableCell><Badge variant={priorityColor(acc.priority)}>{acc.priority}</Badge></TableCell>
                    <TableCell>
                      {acc.tags && acc.tags.length > 0 ? (
                        <div className="flex gap-1 flex-wrap">
                          {acc.tags.map((t) => <Badge key={t} variant="outline" className="text-xs">{t}</Badge>)}
                        </div>
                      ) : "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">{formatRelativeTime(acc.last_seen_at)}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button size="icon" variant="ghost" onClick={() => setEditTarget(acc)}>
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
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">暂无目标账号</TableCell>
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

      <Dialog open={!!editTarget} onOpenChange={(o) => !o && setEditTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑 @{editTarget?.username}</DialogTitle>
          </DialogHeader>
          {editTarget && (
            <EditTargetForm
              target={editTarget}
              onSubmit={(d) => updateMutation.mutate({ id: editTarget.id, data: d })}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CreateTargetDialog({ onSubmit }: { onSubmit: (data: TargetAccountCreate) => void }) {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [priority, setPriority] = useState<"high" | "normal" | "low">("normal");
  const [notes, setNotes] = useState("");

  return (
    <>
      <DialogHeader>
        <DialogTitle>添加目标账号</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div className="space-y-2">
          <Label>用户名 *</Label>
          <Input placeholder="VitalikButerin" value={username} onChange={(e) => setUsername(e.target.value.replace(/^@/, ""))} />
        </div>
        <div className="space-y-2">
          <Label>显示名称</Label>
          <Input placeholder="Vitalik Buterin" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>优先级</Label>
          <Select value={priority} onValueChange={(v) => setPriority(v as typeof priority)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="high">高</SelectItem>
              <SelectItem value="normal">中</SelectItem>
              <SelectItem value="low">低</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>备注</Label>
          <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <DialogFooter>
        <Button onClick={() => onSubmit({ username, display_name: displayName || undefined, priority, notes: notes || undefined })}>
          创建
        </Button>
      </DialogFooter>
    </>
  );
}

function EditTargetForm({ target, onSubmit }: { target: TargetAccount; onSubmit: (data: TargetAccountUpdate) => void }) {
  const [displayName, setDisplayName] = useState(target.display_name || "");
  const [status, setStatus] = useState<TargetAccountStatus>(target.status);
  const [priority, setPriority] = useState(target.priority);
  const [notes, setNotes] = useState(target.notes || "");

  return (
    <>
      <div className="space-y-4">
        <div className="space-y-2">
          <Label>显示名称</Label>
          <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>状态</Label>
          <Select value={status} onValueChange={(v) => setStatus(v as TargetAccountStatus)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="active">活跃</SelectItem>
              <SelectItem value="paused">已暂停</SelectItem>
              <SelectItem value="archived">已归档</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>优先级</Label>
          <Select value={priority} onValueChange={(v) => setPriority(v as typeof priority)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="high">高</SelectItem>
              <SelectItem value="normal">中</SelectItem>
              <SelectItem value="low">低</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>备注</Label>
          <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <DialogFooter>
        <Button onClick={() => onSubmit({ display_name: displayName, status, priority, notes })}>保存</Button>
      </DialogFooter>
    </>
  );
}
