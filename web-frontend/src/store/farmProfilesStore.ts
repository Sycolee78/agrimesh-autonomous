import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { FarmConfig, FarmProfile } from "@/types/farm";
import { useFarmStore } from "./farmStore";

interface FarmProfilesState {
  profiles: FarmProfile[];
  activeProfileId: string | null;

  createProfile: (
    config: FarmConfig,
    profileName: string,
    description?: string
  ) => void;
  updateProfile: (
    profileId: string,
    updates: Partial<FarmConfig> & {
      profileName?: string;
      description?: string;
    }
  ) => void;
  deleteProfile: (profileId: string) => void;
  setActiveProfile: (profileId: string | null) => void;
  loadProfileIntoSession: (profileId: string) => void;
}

export const useFarmProfilesStore = create<FarmProfilesState>()(
  persist(
    (set, get) => ({
      profiles: [],
      activeProfileId: null,

      createProfile: (config, profileName, description) => {
        const now = new Date().toISOString();
        const profileId = `profile-${Date.now()}`;
        const profile: FarmProfile = {
          profileId,
          profileName,
          description,
          farmConfig: { ...config, updatedAt: now },
          createdAt: now,
          updatedAt: now,
        };

        set((state) => ({
          profiles: [...state.profiles, profile],
          activeProfileId: profileId,
        }));

        // Also load into current session
        useFarmStore.setState({
          farmConfig: profile.farmConfig,
          mapCenter: profile.farmConfig.location,
          selectedLocation: profile.farmConfig.location,
        });
      },

      updateProfile: (profileId, updates) => {
        const now = new Date().toISOString();
        set((state) => ({
          profiles: state.profiles.map((p) =>
            p.profileId === profileId
              ? {
                  ...p,
                  profileName: updates.profileName ?? p.profileName,
                  description: updates.description ?? p.description,
                  farmConfig: {
                    ...p.farmConfig,
                    ...updates,
                    updatedAt: now,
                  },
                  updatedAt: now,
                }
              : p
          ),
        }));
      },

      deleteProfile: (profileId) =>
        set((state) => {
          const remaining = state.profiles.filter(
            (p) => p.profileId !== profileId
          );
          const activeProfileId =
            state.activeProfileId === profileId ? null : state.activeProfileId;
          return { profiles: remaining, activeProfileId };
        }),

      setActiveProfile: (profileId) => set({ activeProfileId: profileId }),

      loadProfileIntoSession: (profileId) => {
        const profile = get().profiles.find((p) => p.profileId === profileId);
        if (!profile) return;

        useFarmStore.setState({
          farmConfig: profile.farmConfig,
          mapCenter: profile.farmConfig.location,
          selectedLocation: profile.farmConfig.location,
        });
      },
    }),
    {
      name: "agrimesh-farm-profiles-storage",
    }
  )
);
