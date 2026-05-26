"use client";

import { useEffect, useState } from "react";

import { getProfileSettings, updateProfileSettings } from "@/lib/api-client/settings";
import type { ProfileSettings } from "@/types/settings";

type ProfileSettingsState = {
  profile: ProfileSettings | null;
  displayName: string;
  loading: boolean;
  saving: boolean;
  error: string;
  success: string;
};

export function useProfileSettings() {
  const [state, setState] = useState<ProfileSettingsState>({
    profile: null,
    displayName: "",
    loading: true,
    saving: false,
    error: "",
    success: "",
  });

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const profile = await getProfileSettings();
        if (!cancelled) {
          setState({
            profile,
            displayName: profile.display_name,
            loading: false,
            saving: false,
            error: "",
            success: "",
          });
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            profile: null,
            displayName: "",
            loading: false,
            saving: false,
            error: error instanceof Error ? error.message : "加载个人信息失败",
            success: "",
          });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const setDisplayName = (displayName: string) => {
    setState((current) => ({
      ...current,
      displayName,
      success: "",
    }));
  };

  const save = async () => {
    setState((current) => ({
      ...current,
      saving: true,
      error: "",
      success: "",
    }));

    try {
      const profile = await updateProfileSettings({
        display_name: state.displayName,
      });
      setState((current) => ({
        ...current,
        profile,
        displayName: profile.display_name,
        saving: false,
        error: "",
        success: "个人信息已保存",
      }));
      return true;
    } catch (error) {
      setState((current) => ({
        ...current,
        saving: false,
        error: error instanceof Error ? error.message : "保存失败",
        success: "",
      }));
      return false;
    }
  };

  return {
    ...state,
    setDisplayName,
    save,
  };
}
