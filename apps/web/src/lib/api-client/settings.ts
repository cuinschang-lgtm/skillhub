import { getJson } from "@/lib/api-client/http";
import type { ProfileSettings, UpdateProfileSettingsRequest } from "@/types/settings";

export async function getProfileSettings(): Promise<ProfileSettings> {
  return getJson<ProfileSettings>("/api/settings/profile");
}

export async function updateProfileSettings(
  payload: UpdateProfileSettingsRequest,
): Promise<ProfileSettings> {
  return getJson<ProfileSettings>("/api/settings/profile", {
    method: "PATCH",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}
