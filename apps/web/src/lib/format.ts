import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";

export function formatRelativeTime(date: string | null): string {
  if (!date) return "—";
  return formatDistanceToNow(new Date(date), { addSuffix: true, locale: zhCN });
}

export function statusColor(status: string): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "active":
    case "available":
      return "default";
    case "paused":
    case "in_use":
    case "needs_login":
      return "secondary";
    case "challenged":
    case "suspended":
    case "error":
      return "destructive";
    default:
      return "outline";
  }
}

export function priorityColor(priority: string): "default" | "secondary" | "destructive" | "outline" {
  switch (priority) {
    case "high":
      return "destructive";
    case "normal":
      return "default";
    case "low":
      return "secondary";
    default:
      return "outline";
  }
}
