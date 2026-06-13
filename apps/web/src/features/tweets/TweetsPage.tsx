import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api";
import type { Tweet } from "@/types";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Search, ExternalLink, RefreshCw } from "lucide-react";

export default function TweetsPage() {
  const [page, setPage] = useState(1);
  const [author, setAuthor] = useState("");
  const [search, setSearch] = useState("");
  const [authorFilter, setAuthorFilter] = useState("");
  const [searchFilter, setSearchFilter] = useState("");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["tweets", "latest", page, authorFilter, searchFilter],
    queryFn: () =>
      api.tweets.latest({
        page,
        page_size: 20,
        author: authorFilter || undefined,
        search: searchFilter || undefined,
      }),
  });

  const handleSearch = () => {
    setAuthorFilter(author);
    setSearchFilter(search);
    setPage(1);
  };

  const handleClear = () => {
    setAuthor("");
    setSearch("");
    setAuthorFilter("");
    setSearchFilter("");
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tweets</h1>
          <p className="text-muted-foreground">最新抓取推文</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" /> 刷新
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <Input
              placeholder="作者用户名"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <Input
              placeholder="搜索文本"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <Button onClick={handleSearch}><Search className="h-4 w-4 mr-2" /> 搜索</Button>
            <Button variant="outline" onClick={handleClear}>清除</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>作者</TableHead>
                    <TableHead>内容</TableHead>
                    <TableHead>互动</TableHead>
                    <TableHead>时间</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data?.items.map((t: Tweet) => (
                    <TableRow key={t.id}>
                      <TableCell className="whitespace-nowrap">
                        <div className="font-medium">@{t.author_username}</div>
                        {t.author_display_name && (
                          <div className="text-xs text-muted-foreground">{t.author_display_name}</div>
                        )}
                      </TableCell>
                      <TableCell className="max-w-md">
                        <div className="flex items-start gap-1">
                          {t.is_retweet && <Badge variant="secondary" className="text-xs">RT</Badge>}
                          {t.is_quote && <Badge variant="outline" className="text-xs">引用</Badge>}
                          <span className="text-sm line-clamp-2">{t.text || "—"}</span>
                        </div>
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                        {t.like_count != null && <span>♥ {t.like_count}</span>}
                        {t.retweet_count != null && <span className="ml-2">🔁 {t.retweet_count}</span>}
                        {t.view_count != null && <span className="ml-2">👁 {t.view_count}</span>}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                        {t.posted_at ? new Date(t.posted_at).toLocaleString("zh-CN") : "—"}
                      </TableCell>
                      <TableCell>
                        {t.url && (
                          <a href={t.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                  {data?.items.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-8">暂无推文</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              {data && data.total > 20 && (
                <div className="flex items-center justify-between px-4 py-3 border-t">
                  <span className="text-sm text-muted-foreground">
                    共 {data.total} 条，第 {page} 页
                  </span>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</Button>
                    <Button size="sm" variant="outline" disabled={page * 20 >= data.total} onClick={() => setPage(page + 1)}>下一页</Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
