"use client";

import * as React from "react";
import { useFarmProfilesStore } from "@/store/farmProfilesStore";

interface FarmProfileSelectorProps {
  onNewFarm: () => void;
  onManageProfiles: () => void;
}

export function FarmProfileSelector({ onNewFarm, onManageProfiles }: FarmProfileSelectorProps) {
  const { profiles, activeProfileId, loadProfileIntoSession, setActiveProfile, hydrateFromBackend, backendSync } =
    useFarmProfilesStore();

  React.useEffect(() => {
    hydrateFromBackend();
  }, [hydrateFromBackend]);

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const profileId = event.target.value || null;
    if (!profileId) {
      setActiveProfile(null);
      return;
    }
    setActiveProfile(profileId);
    loadProfileIntoSession(profileId);
  };

  const syncColor =
    backendSync === "idle"
      ? "text-emerald-600 border-emerald-300"
      : backendSync === "loading"
      ? "text-amber-600 border-amber-300"
      : "text-red-600 border-red-300";
  const syncLabel =
    backendSync === "idle"
      ? "Backend OK"
      : backendSync === "loading"
      ? "Syncing..."
      : "Offline";

  return (
    <div className="flex items-center gap-2">
      <select
        className="border rounded px-2 py-1 text-sm bg-background"
        value={activeProfileId ?? ""}
        onChange={handleChange}
      >
        <option value="">Select farm...</option>
        {profiles.map((profile) => (
          <option key={profile.profileId} value={profile.profileId}>
            {profile.profileName}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="text-sm px-3 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700"
        onClick={onNewFarm}
      >
        New farm
      </button>
      <button
        type="button"
        className="text-xs px-2 py-1 rounded border border-border hover:bg-muted"
        onClick={onManageProfiles}
      >
        Manage
      </button>
      <span
        className={`text-[11px] px-2 py-0.5 rounded-full border ${syncColor} hidden md:inline-flex`}
      >
        {syncLabel}
      </span>
    </div>
  );
}
