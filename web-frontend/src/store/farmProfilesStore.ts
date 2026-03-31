import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { FarmConfig, FarmProfile } from "@/types/farm";
import { useFarmStore } from "./farmStore";
import { apiClient } from "@/lib/api";

interface FarmProfilesState {
  profiles: FarmProfile[];
  activeProfileId: string | null;
  backendSync: "idle" | "loading" | "error";

  hydrateFromBackend: () => Promise<void>;
  createProfile: (
    config: FarmConfig,
    profileName: string,
    description?: string
  ) => Promise<void>;
  updateProfile: (
    profileId: string,
    updates: Partial<FarmConfig> & {
      profileName?: string;
      description?: string;
    }
  ) => Promise<void>;
  deleteProfile: (profileId: string) => Promise<void>;
  setActiveProfile: (profileId: string | null) => void;
  loadProfileIntoSession: (profileId: string) => void;
}

export const useFarmProfilesStore = create<FarmProfilesState>()(
  persist(
    (set, get) => ({
      profiles: [],
      activeProfileId: null,
      backendSync: "idle",

      hydrateFromBackend: async () => {
        try {
          set({ backendSync: "loading" });
          const remote = await apiClient.listFarmProfiles();
          if (remote && Array.isArray(remote) && remote.length > 0) {
            set({ profiles: remote, backendSync: "idle" });
          } else {
            set({ backendSync: "idle" });
          }
        } catch (err) {
          console.warn("Failed to hydrate farm profiles from backend", err);
          set({ backendSync: "error" });
        }
      },

      createProfile: async (config, profileName, description) => {
        const now = new Date().toISOString();
        const localProfile: FarmProfile = {
          profileId: "", // filled after backend save
          profileName,
          description,
          farmConfig: { ...config, updatedAt: now },
          createdAt: now,
          updatedAt: now,
        };

        try {
          const saved = await apiClient.saveFarmProfile(localProfile);
          set((state) => ({
            profiles: [...state.profiles, saved],
            activeProfileId: saved.profileId,
            backendSync: "idle",
          }));

          useFarmStore.setState({
            farmConfig: saved.farmConfig,
            mapCenter: saved.farmConfig.location,
            selectedLocation: saved.farmConfig.location,
          });
        } catch (err) {
          console.warn("Failed to save farm profile to backend, falling back to local only", err);
          const profileId = `profile-${Date.now()}`;
          const fallbackProfile: FarmProfile = { ...localProfile, profileId };
          set((state) => ({
            profiles: [...state.profiles, fallbackProfile],
            activeProfileId: profileId,
            backendSync: "error",
          }));

          useFarmStore.setState({
            farmConfig: fallbackProfile.farmConfig,
            mapCenter: fallbackProfile.farmConfig.location,
            selectedLocation: fallbackProfile.farmConfig.location,
          });
        }
      },

      updateProfile: async (profileId, updates) => {
        const existing = get().profiles.find((p) => p.profileId === profileId);
        if (!existing) return;
        const merged: FarmProfile = {
          ...existing,
          profileName: updates.profileName ?? existing.profileName,
          description: updates.description ?? existing.description,
          farmConfig: {
            ...existing.farmConfig,
            ...updates,
            updatedAt: new Date().toISOString(),
          },
          updatedAt: new Date().toISOString(),
        };

        try {
          const saved = await apiClient.saveFarmProfile(merged);
          set((state) => ({
            profiles: state.profiles.map((p) =>
              p.profileId === profileId ? saved : p
            ),
            backendSync: "idle",
          }));
        } catch (err) {
          console.warn("Failed to update farm profile on backend", err);
          set((state) => ({
            profiles: state.profiles.map((p) =>
              p.profileId === profileId ? merged : p
            ),
            backendSync: "error",
          }));
        }
      },

      deleteProfile: async (profileId) => {
        try {
          await apiClient.deleteFarmProfile(profileId);
        } catch (err) {
          console.warn("Failed to delete farm profile on backend", err);
        }

        set((state) => {
          const remaining = state.profiles.filter(
            (p) => p.profileId !== profileId
          );
          const activeProfileId =
            state.activeProfileId === profileId ? null : state.activeProfileId;
          return { profiles: remaining, activeProfileId };
        });
      },

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
