export type TaskStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export type TaskSummary = {
  id: string;
  status: TaskStatus;
  book_title: string;
  skill_name: string;
  current_stage?: string | null;
  progress_pct: number;
  created_at?: string;
  completed_at?: string | null;
  skill_id?: string | null;
  skill_slug?: string | null;
  error_message?: string | null;
};

export type TaskDetail = TaskSummary;

export type TaskListResponse = {
  items?: TaskSummary[];
};

export type TaskProgressTicket = {
  url: string;
  expires_in: number;
};

export type TaskProgressEvent = {
  stage: string;
  status: string;
  message?: string;
  progress?: number;
  extra?: {
    skill_id?: string;
  };
};
