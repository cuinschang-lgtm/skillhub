export type TaskSummary = {
  id: string;
  status: string;
  book_title: string;
  skill_name: string;
  current_stage: string;
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
