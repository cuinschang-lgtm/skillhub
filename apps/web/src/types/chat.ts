import type { Citation } from "@/types/skill";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};

export type ChatResponse = {
  answer: string;
  citations: Citation[];
};
