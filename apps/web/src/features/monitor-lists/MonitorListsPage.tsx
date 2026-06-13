import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api";
import type { MonitorListCreate } from "@/types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
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
import { Plus, Trash2, ChevronRight, ChevronLeft } from "lucide-react";
import { formatRelativeTime } from "@/lib/format";
import { toast } from "sonner";

export default function MonitorListsPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedList, setSelectedList] = useState<string | null>(null);

  const { data: lists, isLoading } = useQuery({
    queryKey: ["monitor-lists"],
    queryFn: () => api.monitorLists.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: MonitorListCreate) => api.monitorLists.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monitor-lists"] });
      setCreateOpen(false);
      toast.success("监听列表已创建");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">监听列表</h1>
          <p className="text-muted-foreground">将目标账号分组以便组织监听</p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4 mr-2" />创建列表</Button>
          </DialogTrigger>
          <DialogContent>
            <CreateListForm onSubmit={(d) => createMutation.mutate(d)} />
          </DialogContent>
        </Dialog>
      </div>

      {selectedList ? (
        <ListMembersView listId={selectedList} onBack={() => setSelectedList(null)} />
      ) : (
        <Card>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-6 space-y-3">
                {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>外部 ID</TableHead>
                    <TableHead>备注</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead className="w-[80px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lists?.map((l) => (
                    <TableRow key={l.id} className="cursor-pointer" onClick={() => setSelectedList(l.id)}>
                      <TableCell className="font-medium">{l.name}</TableCell>
                      <TableCell><Badge variant="outline">{l.list_type}</Badge></TableCell>
                      <TableCell className="text-muted-foreground text-sm">{l.external_id || "—"}</TableCell>
                      <TableCell className="text-muted-foreground text-sm max-w-xs truncate">{l.notes || "—"}</TableCell>
                      <TableCell className="text-muted-foreground text-sm">{formatRelativeTime(l.created_at)}</TableCell>
                      <TableCell>
                        <Button size="icon" variant="ghost">
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {lists && lists.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-8">暂无监听列表</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ListMembersView({ listId, onBack }: { listId: string; onBack: () => void }) {
  const queryClient = useQueryClient();
  const [addMemberId, setAddMemberId] = useState("");

  const { data: members } = useQuery({
    queryKey: ["monitor-lists", listId, "members"],
    queryFn: () => api.monitorLists.members(listId),
  });

  const { data: targetsData } = useQuery({
    queryKey: ["target-accounts", "all-for-members"],
    queryFn: () => api.targetAccounts.list({ page: 1, page_size: 100 }),
  });

  const addMemberMutation = useMutation({
    mutationFn: (targetAccountId: string) => api.monitorLists.addMember(listId, { target_account_id: targetAccountId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monitor-lists", listId, "members"] });
      setAddMemberId("");
      toast.success("成员已添加");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const removeMemberMutation = useMutation({
    mutationFn: (targetAccountId: string) => api.monitorLists.removeMember(listId, targetAccountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monitor-lists", listId, "members"] });
      toast.success("成员已移除");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const targets = targetsData?.items ?? [];
  const memberTargetIds = new Set(members?.map((m) => m.target_account_id));
  const availableTargets = targets.filter((t) => !memberTargetIds.has(t.id));

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <Button size="icon" variant="ghost" onClick={onBack}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <CardTitle>列表成员</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2 items-end">
          <div className="flex-1 space-y-2">
            <Label>添加目标账号</Label>
            <Select value={addMemberId} onValueChange={setAddMemberId}>
              <SelectTrigger><SelectValue placeholder="选择账号..." /></SelectTrigger>
              <SelectContent>
                {availableTargets.map((t) => (
                  <SelectItem key={t.id} value={t.id}>@{t.username}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            disabled={!addMemberId}
            onClick={() => addMemberMutation.mutate(addMemberId)}
          >
            <Plus className="h-4 w-4 mr-2" />添加
          </Button>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>目标账号</TableHead>
              <TableHead>添加时间</TableHead>
              <TableHead className="w-[60px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {members?.map((m) => {
              const target = targets.find((t) => t.id === m.target_account_id);
              return (
                <TableRow key={m.id}>
                  <TableCell className="font-medium">@{target?.username ?? m.target_account_id.slice(0, 8)}</TableCell>
                  <TableCell className="text-muted-foreground text-sm">{formatRelativeTime(m.created_at)}</TableCell>
                  <TableCell>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => removeMemberMutation.mutate(m.target_account_id)}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
            {members && members.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground py-6">该列表暂无成员</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function CreateListForm({ onSubmit }: { onSubmit: (data: MonitorListCreate) => void }) {
  const [name, setName] = useState("");
  const [listType, setListType] = useState("internal");
  const [notes, setNotes] = useState("");

  return (
    <>
      <DialogHeader>
        <DialogTitle>创建监听列表</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div className="space-y-2">
          <Label>名称 *</Label>
          <Input placeholder="KOL 列表" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>类型</Label>
          <Select value={listType} onValueChange={setListType}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="internal">内部</SelectItem>
              <SelectItem value="twitter_list">Twitter List</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>备注</Label>
          <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <DialogFooter>
        <Button onClick={() => onSubmit({ name, list_type: listType, notes: notes || undefined })}>创建</Button>
      </DialogFooter>
    </>
  );
}
