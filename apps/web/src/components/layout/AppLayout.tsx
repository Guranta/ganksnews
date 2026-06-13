import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Target,
  Eye,
  Globe,
  List,
  Activity,
  Cpu,
  Layers,
  Radio,
  MessageSquare,
  Monitor,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";

const navGroups = [
  {
    label: "监控",
    items: [
      { title: "仪表盘", href: "/", icon: LayoutDashboard },
      { title: "目标账号", href: "/target-accounts", icon: Target },
      { title: "最新推文", href: "/tweets", icon: MessageSquare },
      { title: "监听列表", href: "/monitor-lists", icon: List },
    ],
  },
  {
    label: "登录与账号",
    items: [
      { title: "监控账号", href: "/monitoring-accounts", icon: Eye },
      { title: "浏览器配置", href: "/browser-profiles", icon: Globe },
      { title: "登录会话", href: "/login-sessions", icon: Monitor },
    ],
  },
  {
    label: "运行状态",
    items: [
      { title: "Workers", href: "/workers", icon: Cpu },
      { title: "Queues", href: "/queues", icon: Layers },
      { title: "Events", href: "/events", icon: Radio },
    ],
  },
];

function AppSidebar() {
  return (
    <Sidebar className="border-r border-border/70">
      <SidebarHeader className="border-b bg-muted/20 px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <div className="font-semibold leading-none">LittleGankNews</div>
            <div className="mt-1 text-xs text-muted-foreground">X monitor console</div>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent className="px-2 py-3">
        {navGroups.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel className="text-[11px] uppercase tracking-wider text-muted-foreground/80">
              {group.label}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild>
                      <NavLink
                        to={item.href}
                        end={item.href === "/"}
                        className={({ isActive }) =>
                          isActive
                            ? "bg-primary/10 text-primary font-medium shadow-sm"
                            : "text-muted-foreground hover:text-foreground"
                        }
                      >
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
    </Sidebar>
  );
}

export default function AppLayout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="flex-1 overflow-auto">
        <header className="flex h-12 items-center gap-3 border-b px-4">
          <SidebarTrigger />
          <Separator orientation="vertical" className="h-5" />
        </header>
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </SidebarProvider>
  );
}
