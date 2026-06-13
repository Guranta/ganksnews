import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api";
import { useSSE } from "@/hooks/useSSE";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Zap, Wifi, WifiOff } from "lucide-react";
import { toast } from "sonner";

const SSE_URL = "/api/v1/events/stream";

export default function EventsPage() {
  const queryClient = useQueryClient();
  const [testMsg, setTestMsg] = useState("hello from LittleGankNews");
  const { events, connected, clear } = useSSE(SSE_URL);

  const { data: recentEvents, isLoading } = useQuery({
    queryKey: ["events", "recent"],
    queryFn: () => api.events.recent(50),
  });

  const testMutation = useMutation({
    mutationFn: (message: string) => api.events.test(message),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events", "recent"] });
      toast.success("测试事件已发送");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Events</h1>
          <p className="text-muted-foreground">实时事件流</p>
        </div>
        <div className="flex items-center gap-2">
          {connected ? (
            <Badge variant="default" className="gap-1"><Wifi className="h-3 w-3" /> 已连接</Badge>
          ) : (
            <Badge variant="secondary" className="gap-1"><WifiOff className="h-3 w-3" /> 未连接</Badge>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">发送测试事件</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input value={testMsg} onChange={(e) => setTestMsg(e.target.value)} placeholder="消息内容" />
            <Button onClick={() => testMutation.mutate(testMsg)} disabled={testMutation.isPending}>
              <Zap className="h-4 w-4 mr-2" /> 发送
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>实时事件 (SSE)</CardTitle>
          <Button size="sm" variant="outline" onClick={clear}>清空</Button>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>数据</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...events].reverse().slice(0, 50).map((e, i) => (
                <TableRow key={`${e.id}-${i}`}>
                  <TableCell className="font-mono text-xs">{e.id}</TableCell>
                  <TableCell><Badge variant="outline">{e.type}</Badge></TableCell>
                  <TableCell className="text-sm max-w-md truncate">{JSON.stringify(e.payload)}</TableCell>
                </TableRow>
              ))}
              {events.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} className="text-center text-muted-foreground py-8">等待事件...</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>历史事件</CardTitle>
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
                  <TableHead>ID</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>数据</TableHead>
                  <TableHead>时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentEvents?.map((e, i) => (
                  <TableRow key={`${e.id}-${i}`}>
                    <TableCell className="font-mono text-xs">{e.id}</TableCell>
                    <TableCell><Badge variant="outline">{e.type}</Badge></TableCell>
                    <TableCell className="text-sm max-w-md truncate">{JSON.stringify(e.payload)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{e.ts}</TableCell>
                  </TableRow>
                ))}
                {recentEvents && recentEvents.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground py-8">暂无历史事件</TableCell>
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
