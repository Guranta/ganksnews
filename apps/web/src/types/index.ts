export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
  redis: string;
}

export interface DashboardSummary {
  active_target_accounts: number;
  monitoring_accounts: number;
  browser_profiles: number;
  total_tweets: number;
  workers_online: number;
}

export type TargetAccountStatus = "active" | "paused" | "archived";
export type TargetAccountPriority = "high" | "normal" | "low";

export interface TargetAccount {
  id: string;
  platform: string;
  username: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  tags: string[] | null;
  notes: string | null;
  status: TargetAccountStatus;
  priority: TargetAccountPriority;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TargetAccountCreate {
  username: string;
  display_name?: string;
  bio?: string;
  tags?: string[];
  notes?: string;
  priority?: TargetAccountPriority;
}

export interface TargetAccountUpdate {
  display_name?: string;
  bio?: string;
  avatar_url?: string;
  tags?: string[];
  notes?: string;
  status?: TargetAccountStatus;
  priority?: TargetAccountPriority;
}

export interface TargetAccountBulkImportRequest {
  text: string;
}

export interface TargetAccountBulkImportResponse {
  batch_id: string;
  total_count: number;
  created_count: number;
  updated_count: number;
  failed_count: number;
  errors: string[] | null;
}

export type MonitoringAccountStatus = "active" | "needs_login" | "challenged" | "suspended" | "inactive";

export interface MonitoringAccount {
  id: string;
  platform: string;
  username: string;
  display_name: string | null;
  status: MonitoringAccountStatus;
  notes: string | null;
  last_login_check_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MonitoringAccountCreate {
  username: string;
  display_name?: string;
  notes?: string;
}

export interface MonitoringAccountUpdate {
  display_name?: string;
  status?: MonitoringAccountStatus;
  notes?: string;
}

export interface MonitoringAccountWithLoginSessionResponse {
  account: MonitoringAccount;
  browser_profile: BrowserProfile;
  login_session: LoginSessionItem;
  vnc_url: string | null;
}

export type BrowserProfileStatus = "available" | "in_use" | "needs_login" | "error" | "unregistered";

export interface BrowserProfile {
  id: string;
  name: string;
  profile_path: string;
  monitoring_account_id: string | null;
  status: BrowserProfileStatus;
  provider: string;
  last_health_check_at: string | null;
  locked_by: string | null;
  locked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BrowserProfileCreate {
  name: string;
  profile_path: string;
  monitoring_account_id?: string;
  provider?: string;
}

export interface BrowserProfileUpdate {
  name?: string;
  profile_path?: string;
  monitoring_account_id?: string;
  status?: BrowserProfileStatus;
  provider?: string;
}

export interface MonitorList {
  id: string;
  name: string;
  list_type: string;
  external_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface MonitorListCreate {
  name: string;
  list_type?: string;
  external_id?: string;
  notes?: string;
}

export interface MonitorListUpdate {
  name?: string;
  list_type?: string;
  external_id?: string;
  notes?: string;
}

export interface MonitorListMembership {
  id: string;
  monitor_list_id: string;
  target_account_id: string;
  created_at: string;
}

export interface MonitorListMembershipCreate {
  target_account_id: string;
}

export interface WorkerInfo {
  id: string;
  worker_type: string;
  worker_id: string;
  status: string;
  current_task: string | null;
  metadata_: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface WorkerSummary {
  worker_type: string;
  running: number;
  stopped: number;
  error: number;
  total: number;
  workers: WorkerInfo[];
}

export interface QueueInfo {
  stream: string;
  length: number;
  groups: ConsumerGroupInfo[];
}

export interface ConsumerGroupInfo {
  name: string;
  pending: number;
  consumers: number;
}

export interface DeadLetterEntry {
  id: string;
  source_stream: string;
  original_id: string;
  error: string;
  original_data: Record<string, string>;
  failed_at: string;
}

export interface WebEventItem {
  id: string;
  type: string;
  payload: unknown;
  ts: string;
}

export interface Tweet {
  id: string;
  platform: string;
  tweet_id: string;
  author_username: string;
  author_display_name: string | null;
  text: string | null;
  url: string | null;
  posted_at: string | null;
  like_count: number | null;
  retweet_count: number | null;
  reply_count: number | null;
  quote_count: number | null;
  view_count: number | null;
  is_retweet: boolean;
  is_quote: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginSessionItem {
  id: string;
  browser_profile_id: string | null;
  monitoring_account_id: string | null;
  status: string;
  vnc_url: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}
