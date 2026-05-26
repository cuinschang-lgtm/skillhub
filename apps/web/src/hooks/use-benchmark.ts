"use client";

import { useEffect, useState } from "react";

import { getBenchmark, getSkillDetail } from "@/lib/api-client/skills";
import type { BenchmarkResult, SkillDetail } from "@/types/skill";

type BenchmarkState = {
  skillId: string;
  skill: SkillDetail | null;
  benchmark: BenchmarkResult | null;
  loading: boolean;
  error: string;
};

function createInitialState(skillId: string): BenchmarkState {
  return {
    skillId,
    skill: null,
    benchmark: null,
    loading: true,
    error: "",
  };
}

export function useBenchmark(skillId: string) {
  const [state, setState] = useState<BenchmarkState>(() => createInitialState(skillId));

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const [skill, benchmark] = await Promise.all([
          getSkillDetail(skillId),
          getBenchmark(skillId),
        ]);
        if (!cancelled) {
          setState({ skillId, skill, benchmark, loading: false, error: "" });
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            skillId,
            skill: null,
            benchmark: null,
            loading: false,
            error: error instanceof Error ? error.message : "加载失败",
          });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [skillId]);

  if (state.skillId !== skillId) {
    return createInitialState(skillId);
  }

  return state;
}
