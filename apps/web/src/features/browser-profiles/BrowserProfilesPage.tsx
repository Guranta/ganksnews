import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api";
import type { BrowserProfile, BrowserProfileStatus, BrowserProfileCreate, BrowserProfileUpdate } from "@/types";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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
import { Plus, Trash2, Pencil } from "lucide-react";
import { formatRelativeTime, statusColor } from "@/lib/format";
import { toast } from "sonner";

export default function BrowserProfilesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [editProfile, setEditProfile] = useState<BrowserProfile | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["browser-profiles", page],
    queryFn: () => api.browserProfiles.list({ page, page_size: 20 }),
  });

  const { data: monitoringAccountsData } = useQuery({
    queryKey: ["monitoring-accounts", "all"],
    queryFn: () => api.monitoringAccounts.list({ page: 1, page_size: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: (data: BrowserProfileCreate) => api.browserProfiles.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["browser-profiles"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setCreateOpen(false);
      toast.success("浏览器配置已创建");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: BrowserProfileUpdate }) =>
      api.browserProfiles.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["browser-profiles"] });
      setEditProfile(null);
      toast.success("浏览器配置已更新");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.browserProfiles.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["browser-profiles"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("浏览器配置已删除");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">浏览器配置</h1>
          <p className="text-muted-foreground">CloakBrowser 持久化配置管理</p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4 mr-2" />添加配置</Button>
          </DialogTrigger>
          <DialogContent>
            <CreateProfileForm
              monitoringAccounts={monitoringAccountsData?.items ?? []}
              onSubmit={(d) => createMutation.mutate(d)}
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
                  <TableHead>名称</TableHead>
                  <TableHead>路径</TableHead>
                  <TableHead>提供方</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>健康检查</TableHead>
                  <TableHead>锁定者</TableHead>
                  <TableHead className="w-[80px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">{p.name}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground max-w-xs truncate">{p.profile_path}</TableCell>
                    <TableCell><Badge variant="outline">{p.provider}</Badge></TableCell>
                    <TableCell><Badge variant={statusColor(p.status)}>{p.status}</Badge></TableCell>
                    <TableCell className="text-muted-foreground text-sm">{formatRelativeTime(p.last_health_check_at)}</TableCell>
                    <TableCell className="text-sm">{p.locked_by || "—"}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button size="icon" variant="ghost" onClick={() => setEditProfile(p)}>
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => { if (confirm(`确认删除"${p.name}"？`)) deleteMutation.mutate(p.id); }}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {data && data.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">暂无浏览器配置</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">共 {data?.total ?? 0} 个配置</p>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>上一页</Button>
            <span className="flex items-center px-2 text-sm text-muted-foreground">第 {page} / {totalPages} 页</span>
            <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>下一页</Button>
          </div>
        </div>
      )}

      <Dialog open={!!editProfile} onOpenChange={(o) => !o && setEditProfile(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑"{editProfile?.name}"</DialogTitle>
          </DialogHeader>
          {editProfile && (
            <EditProfileForm
              profile={editProfile}
              monitoringAccounts={monitoringAccountsData?.items ?? []}
              onSubmit={(d) => updateMutation.mutate({ id: editProfile.id, data: d })}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CreateProfileForm({ monitoringAccounts, onSubmit }: {
  monitoringAccounts: { id: string; username: string }[];
  onSubmit: (data: BrowserProfileCreate) => void;
}) {
  const [name, setName] = useState("");
  const [profilePath, setProfilePath] = useState("");
  const [provider, setProvider] = useState("cloakbrowser");
  const [monitoringAccountId, setMonitoringAccountId] = useState<string>("");

  return (
    <>
      <DialogHeader>
        <DialogTitle>添加浏览器配置</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div className="space-y-2">
          <Label>名称 *</Label>
          <Input placeholder="配置 1" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>配置路径 *</Label>
          <Input placeholder="/path/to/profile" value={profilePath} onChange={(e) => setProfilePath(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>提供方</Label>
          <Select value={provider} onValueChange={setProvider}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="cloakbrowser">cloakbrowser</SelectItem>
              <SelectItem value="playwright">playwright</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>关联监控账号</Label>
          <Select value={monitoringAccountId} onValueChange={setMonitoringAccountId}>
            <SelectTrigger><SelectValue placeholder="无" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="">无</SelectItem>
              {monitoringAccounts.map((a) => (
                <SelectItem key={a.id} value={a.id}>@{a.username}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <DialogFooter>
        <Button onClick={() => onSubmit({
          name,
          profile_path: profilePath,
          provider,
          monitoring_account_id: monitoringAccountId || undefined,
        })}>创建</Button>
      </DialogFooter>
    </>
  );
}

function EditProfileForm({ profile, monitoringAccounts, onSubmit }: {
  profile: BrowserProfile;
  monitoringAccounts: { id: string; username: string }[];
  onSubmit: (data: BrowserProfileUpdate) => void;
}) {
  const [name, setName] = useState(profile.name);
  const [status, setStatus] = useState<BrowserProfileStatus>(profile.status);
  const [monitoringAccountId, setMonitoringAccountId] = useState(profile.monitoring_account_id || "");

  return (
    <>
      <div className="space-y-4">
        <div className="space-y-2">
          <Label>名称</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>状态</Label>
          <Select value={status} onValueChange={(v) => setStatus(v as BrowserProfileStatus)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="available">可用</SelectItem>
              <SelectItem value="in_use">使用中</SelectItem>
              <SelectItem value="needs_login">需要登录</SelectItem>
              <SelectItem value="error">异常</SelectItem>
              <SelectItem value="unregistered">未注册</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>关联监控账号</Label>
          <Select value={monitoringAccountId} onValueChange={setMonitoringAccountId}>
            <SelectTrigger><SelectValue placeholder="无" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="">无</SelectItem>
              {monitoringAccounts.map((a) => (
                <SelectItem key={a.id} value={a.id}>@{a.username}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <DialogFooter>
        <Button onClick={() => onSubmit({ name, status, monitoring_account_id: monitoringAccountId || undefined })}>保存</Button>
      </DialogFooter>
    </>
  );
}
