"use client";

import * as React from "react";
import { useFarmProfilesStore } from "@/store/farmProfilesStore";

interface FarmProfileSelectorProps {
  onNewFarm: () => void;
}

export function FarmProfileSelector({ onNewFarm }: FarmProfileSelectorProps) {
  const { profiles, activeProfileId, loadProfileIntoSession, setActiveProfile } =
    useFarmProfilesStore();

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const profileId = event.target.value || null;
    if (!profileId) {
      setActiveProfile(null);
      return;
    }
    setActiveProfile(profileId);
    loadProfileIntoSession(profileId);
  };

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
    </div>
  );
}
