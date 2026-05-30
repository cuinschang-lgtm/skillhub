"use client";

import { useEffect, useReducer } from "react";

import { listSkills } from "@/lib/api-client/skills";
import type { SkillSummary } from "@/types/skill";

type UseSkillsState = {
  skills: SkillSummary[];
  loading: boolean;
  error: string;
};

type UseSkillsAction =
  | { type: "start" }
  | { type: "success"; skills: SkillSummary[] }
  | { type: "error"; message: string };

function reducer(state: UseSkillsState, action: UseSkillsAction): UseSkillsState {
  switch (action.type) {
    case "start":
      return {
        ...state,
        loading: true,
        error: "",
      };
    case "success":
      return {
        skills: action.skills,
        loading: false,
        error: "",
      };
    case "error":
      return {
        skills: [],
        loading: false,
        error: action.message,
      };
    default:
      return state;
  }
}

export function useSkills(search = "") {
  const [state, dispatch] = useReducer(reducer, {
    skills: [],
    loading: true,
    error: "",
  });

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      if (cancelled) return;

      dispatch({ type: "start" });

      (async () => {
        try {
          const skills = await listSkills({ search });
          if (!cancelled) {
            dispatch({ type: "success", skills });
          }
        } catch (error) {
          if (!cancelled) {
            dispatch({
              type: "error",
              message: error instanceof Error ? error.message : "加载失败",
            });
          }
        }
      })();
    }, 300);

    return () => {
      cancelled = true;
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [search]);

  return state;
}
