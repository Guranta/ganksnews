const API_BASE = "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (res.status === 204) return undefined as T;
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

import type {
  DashboardSummary,
  HealthResponse,
  PaginatedResponse,
  TargetAccount,
  TargetAccountCreate,
  TargetAccountUpdate,
  TargetAccountBulkImportRequest,
  TargetAccountBulkImportResponse,
  MonitoringAccount,
  MonitoringAccountCreate,
  MonitoringAccountUpdate,
  BrowserProfile,
  BrowserProfileCreate,
  BrowserProfileUpdate,
  MonitorList,
  MonitorListCreate,
  MonitorListMembership,
  MonitorListMembershipCreate,
  TargetAccountStatus,
  WorkerInfo,
  WorkerSummary,
  QueueInfo,
  DeadLetterEntry,
  WebEventItem,
  Tweet,
  LoginSessionItem,
} from "@/types";

export const api = {
  health: {
    check: () => request<HealthResponse>("/health"),
    ready: () => request<HealthResponse>("/health/ready"),
  },

  dashboard: {
    summary: () => request<DashboardSummary>("/dashboard/summary"),
  },

  targetAccounts: {
    list: (params?: { page?: number; page_size?: number; status?: TargetAccountStatus; search?: string }) => {
      const sp = new URLSearchParams();
      if (params?.page) sp.set("page", String(params.page));
      if (params?.page_size) sp.set("page_size", String(params.page_size));
      if (params?.status) sp.set("status", params.status);
      if (params?.search) sp.set("search", params.search);
      const qs = sp.toString();
      return request<PaginatedResponse<TargetAccount>>(`/target-accounts${qs ? `?${qs}` : ""}`);
    },
    create: (data: TargetAccountCreate) =>
      request<TargetAccount>("/target-accounts", { method: "POST", body: JSON.stringify(data) }),
    import: (data: TargetAccountBulkImportRequest) =>
      request<TargetAccountBulkImportResponse>("/target-accounts/import", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: TargetAccountUpdate) =>
      request<TargetAccount>(`/target-accounts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string) =>
      request<void>(`/target-accounts/${id}`, { method: "DELETE" }),
  },

  monitoringAccounts: {
    list: (params?: { page?: number; page_size?: number }) => {
      const sp = new URLSearchParams();
      if (params?.page) sp.set("page", String(params.page));
      if (params?.page_size) sp.set("page_size", String(params.page_size));
      const qs = sp.toString();
      return request<PaginatedResponse<MonitoringAccount>>(`/monitoring-accounts${qs ? `?${qs}` : ""}`);
    },
    create: (data: MonitoringAccountCreate) =>
      request<MonitoringAccount>("/monitoring-accounts", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: MonitoringAccountUpdate) =>
      request<MonitoringAccount>(`/monitoring-accounts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string) =>
      request<void>(`/monitoring-accounts/${id}`, { method: "DELETE" }),
  },

  browserProfiles: {
    list: (params?: { page?: number; page_size?: number }) => {
      const sp = new URLSearchParams();
      if (params?.page) sp.set("page", String(params.page));
      if (params?.page_size) sp.set("page_size", String(params.page_size));
      const qs = sp.toString();
      return request<PaginatedResponse<BrowserProfile>>(`/browser-profiles${qs ? `?${qs}` : ""}`);
    },
    create: (data: BrowserProfileCreate) =>
      request<BrowserProfile>("/browser-profiles", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: BrowserProfileUpdate) =>
      request<BrowserProfile>(`/browser-profiles/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string) =>
      request<void>(`/browser-profiles/${id}`, { method: "DELETE" }),
  },

  monitorLists: {
    list: () => request<MonitorList[]>("/monitor-lists"),
    create: (data: MonitorListCreate) =>
      request<MonitorList>("/monitor-lists", { method: "POST", body: JSON.stringify(data) }),
    members: (listId: string) =>
      request<MonitorListMembership[]>(`/monitor-lists/${listId}/members`),
    addMember: (listId: string, data: MonitorListMembershipCreate) =>
      request<MonitorListMembership>(`/monitor-lists/${listId}/members`, { method: "POST", body: JSON.stringify(data) }),
    removeMember: (listId: string, targetAccountId: string) =>
      request<void>(`/monitor-lists/${listId}/members/${targetAccountId}`, { method: "DELETE" }),
  },

  workers: {
    list: () => request<WorkerInfo[]>("/workers"),
    summary: () => request<WorkerSummary[]>("/workers/summary"),
  },

  queues: {
    list: () => request<QueueInfo[]>("/queues"),
    deadLetter: (count?: number) => {
      const qs = count ? `?count=${count}` : "";
      return request<DeadLetterEntry[]>(`/queues/dead-letter${qs}`);
    },
  },

  events: {
    recent: (count?: number) => {
      const qs = count ? `?count=${count}` : "";
      return request<WebEventItem[]>(`/events/recent${qs}`);
    },
    test: (message?: string) => {
      const qs = message ? `?message=${encodeURIComponent(message)}` : "";
      return request<{ ok: boolean; stream_id: string }>(`/events/test${qs}`, { method: "POST" });
    },
  },

  tweets: {
    latest: (params?: { page?: number; page_size?: number; author?: string; search?: string }) => {
      const qs = new URLSearchParams();
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      if (params?.author) qs.set("author", params.author);
      if (params?.search) qs.set("search", params.search);
      const s = qs.toString();
      return request<PaginatedResponse<Tweet>>(`/tweets/latest${s ? `?${s}` : ""}`);
    },
    get: (id: string) => request<Tweet>(`/tweets/${id}`),
  },

  loginSessions: {
    list: (params?: { page?: number; page_size?: number; status?: string }) => {
      const qs = new URLSearchParams();
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      if (params?.status) qs.set("status", params.status);
      const s = qs.toString();
      return request<PaginatedResponse<LoginSessionItem>>(`/login-sessions${s ? `?${s}` : ""}`);
    },
    get: (id: string) => request<LoginSessionItem>(`/login-sessions/${id}`),
    create: (data: { browser_profile_id?: string; monitoring_account_id?: string }) =>
      request<LoginSessionItem>("/login-sessions", { method: "POST", body: JSON.stringify(data) }),
    complete: (id: string) => request<LoginSessionItem>(`/login-sessions/${id}/complete`, { method: "POST" }),
    cancel: (id: string) => request<LoginSessionItem>(`/login-sessions/${id}/cancel`, { method: "POST" }),
  },
};
