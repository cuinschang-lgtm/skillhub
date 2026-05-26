export type ProfileSettings = {
  email: string;
  role: "teacher" | "student";
  display_name: string;
};

export type UpdateProfileSettingsRequest = {
  display_name: string;
};
