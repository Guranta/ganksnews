import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import AppLayout from "@/components/layout/AppLayout";
import DashboardPage from "@/features/dashboard/DashboardPage";
import TargetAccountsPage from "@/features/target-accounts/TargetAccountsPage";
import MonitoringAccountsPage from "@/features/monitoring-accounts/MonitoringAccountsPage";
import BrowserProfilesPage from "@/features/browser-profiles/BrowserProfilesPage";
import MonitorListsPage from "@/features/monitor-lists/MonitorListsPage";
import WorkersPage from "@/features/workers/WorkersPage";
import QueuesPage from "@/features/queues/QueuesPage";
import EventsPage from "@/features/events/EventsPage";
import TweetsPage from "@/features/tweets/TweetsPage";
import LoginSessionsPage from "@/features/login-sessions/LoginSessionsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="target-accounts" element={<TargetAccountsPage />} />
              <Route path="monitoring-accounts" element={<MonitoringAccountsPage />} />
              <Route path="browser-profiles" element={<BrowserProfilesPage />} />
              <Route path="monitor-lists" element={<MonitorListsPage />} />
              <Route path="workers" element={<WorkersPage />} />
              <Route path="queues" element={<QueuesPage />} />
              <Route path="events" element={<EventsPage />} />
              <Route path="tweets" element={<TweetsPage />} />
              <Route path="login-sessions" element={<LoginSessionsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster richColors />
      </TooltipProvider>
    </QueryClientProvider>
  );
}
