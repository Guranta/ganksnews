import { useQuery } from "@tanstack/react-query";
import { api } from "@/api";
import type { QueueInfo } from "@/types";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function QueuesPage() {
  const { data: queues, isLoading: queuesLoading } = useQuery({
    queryKey: ["queues"],
    queryFn: () => api.queues.list(),
    refetchInterval: 5000,
  });

  const { data: deadLetters, isLoading: dlLoading } = useQuery({
    queryKey: ["queues", "dead-letter"],
    queryFn: () => api.queues.deadLetter(100),
    refetchInterval: 10000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Queues</h1>
        <p className="text-muted-foreground">Redis Streams 队列状态</p>
      </div>

      <Tabs defaultValue="queues">
        <TabsList>
          <TabsTrigger value="queues">队列</TabsTrigger>
          <TabsTrigger value="dead-letter">死信 ({deadLetters?.length ?? 0})</TabsTrigger>
        </TabsList>

        <TabsContent value="queues" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {queuesLoading ? (
              Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-28" />)
            ) : (
              queues?.map((q) => <QueueCard key={q.stream} queue={q} />)
            )}
          </div>
        </TabsContent>

        <TabsContent value="dead-letter">
          <Card>
            <CardContent className="p-0">
              {dlLoading ? (
                <div className="p-6 space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>源 Stream</TableHead>
                      <TableHead>原始 ID</TableHead>
                      <TableHead>错误</TableHead>
                      <TableHead>时间</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {deadLetters?.map((dl) => (
                      <TableRow key={dl.id}>
                        <TableCell className="font-mono text-xs">{dl.id}</TableCell>
                        <TableCell className="text-sm">{dl.source_stream}</TableCell>
                        <TableCell className="font-mono text-xs">{dl.original_id}</TableCell>
                        <TableCell className="text-sm text-destructive max-w-xs truncate">{dl.error}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{dl.failed_at}</TableCell>
                      </TableRow>
                    ))}
                    {deadLetters && deadLetters.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-muted-foreground py-8">无死信消息</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function QueueCard({ queue }: { queue: QueueInfo }) {
  const streamShort = queue.stream.replace("lgn:", "");
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium font-mono">{streamShort}</CardTitle>
        <Badge variant={queue.length > 0 ? "default" : "secondary"}>{queue.length}</Badge>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{queue.length}</div>
        <p className="text-xs text-muted-foreground">
          {queue.groups.length} consumer group{queue.groups.length !== 1 ? "s" : ""}
        </p>
        {queue.groups.length > 0 && (
          <div className="mt-2 space-y-1">
            {queue.groups.map((g) => (
              <div key={g.name} className="flex items-center justify-between text-xs">
                <span className="font-mono">{g.name}</span>
                <span className="text-muted-foreground">{g.pending} pending · {g.consumers} consumers</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
