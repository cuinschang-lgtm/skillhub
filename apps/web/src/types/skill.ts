export type SkillSummary = {
  id: string;
  name: string;
  book_title: string;
  domain?: string | null;
  visibility: string;
  chapter_count?: number | null;
  benchmark_verdict?: string | null;
  benchmark_delta?: number | null;
  benchmark_score?: number | null;
};

export type SkillDetail = {
  id: string;
  name: string;
  book_title: string;
  chapter_count?: number | null;
  benchmark_verdict?: string | null;
  benchmark_delta?: number | null;
  benchmark_score?: number | null;
};

export type SkillListResponse = {
  items?: SkillSummary[];
};

export type BenchmarkResult = {
  verdict: string;
  delta_pct: number;
  p_value: number;
  ci_lower: number;
  ci_upper: number;
  routing_accuracy: number;
  total_questions: number;
  with_correct: number;
  without_correct: number;
  per_chapter: { chapter: string; with_rate: number; without_rate: number }[];
  per_difficulty: { level: string; with: number; without: number }[];
};

export type Citation = {
  skill_id: string;
  skill_name: string;
  chapter: string;
  excerpt: string;
};
