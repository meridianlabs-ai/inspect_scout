import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export interface ColumnPreset {
  name: string;
  columns: string[];
}

interface UserSettingsState {
  dataframeColumnPresets: ColumnPreset[];
  setDataframeColumnPresets: (presets: ColumnPreset[]) => void;
}

export const useUserSettings = create<UserSettingsState>()(
  persist(
    (set) => ({
      dataframeColumnPresets: [],
      setDataframeColumnPresets: (presets: ColumnPreset[]) => {
        set({ dataframeColumnPresets: presets });
      },
    }),
    {
      name: "inspect-scout-user-settings",
      storage: createJSONStorage(() => localStorage),
    }
  )
);
