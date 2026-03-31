"use client";

import * as React from "react";
import { useFarmProfilesStore } from "@/store/farmProfilesStore";

interface FarmProfilesManagerProps {
  open: boolean;
  onClose: () => void;
}

export function FarmProfilesManager({ open, onClose }: FarmProfilesManagerProps) {
  const {
    profiles,
    activeProfileId,
    setActiveProfile,
    loadProfileIntoSession,
    updateProfile,
    deleteProfile,
  } = useFarmProfilesStore();

  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [draftName, setDraftName] = React.useState("");
  const [draftDescription, setDraftDescription] = React.useState("");

  React.useEffect(() => {
    if (!open) {
      setEditingId(null);
    }
  }, [open]);

  if (!open) return null;

  const startEdit = (id: string) => {
    const profile = profiles.find((p) => p.profileId === id);
    if (!profile) return;
    setEditingId(id);
    setDraftName(profile.profileName);
    setDraftDescription(profile.description ?? "");
  };

  const saveEdit = async () => {
    if (!editingId) return;
    await updateProfile(editingId, {
      profileName: draftName,
      description: draftDescription,
    });
    setEditingId(null);
  };

  const handleDelete = async (id: string) => {
    const profile = profiles.find((p) => p.profileId === id);
    const label = profile?.profileName || id;
    if (!window.confirm(`Delete farm profile "${label}"? This cannot be undone.`)) {
      return;
    }
    await deleteProfile(id);
  };

  const handleActivate = (id: string) => {
    setActiveProfile(id);
    loadProfileIntoSession(id);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-lg bg-background p-6 shadow-xl border border-border max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Manage Farm Profiles</h2>
          <button
            type="button"
            className="text-sm px-2 py-1 rounded border border-border hover:bg-muted"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        {profiles.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No farm profiles yet. Use the <strong>New farm</strong> button in the header to create one.
          </p>
        ) : (
          <ul className="space-y-3">
            {profiles.map((profile) => {
              const isActive = profile.profileId === activeProfileId;
              const isEditing = profile.profileId === editingId;
              return (
                <li
                  key={profile.profileId}
                  className="border rounded p-3 flex flex-col gap-2 bg-muted/40"
                >
                  <div className="flex items-center justify-between gap-2">
                    {isEditing ? (
                      <input
                        className="flex-1 border rounded px-2 py-1 text-sm"
                        value={draftName}
                        onChange={(e) => setDraftName(e.target.value)}
                      />
                    ) : (
                      <div className="flex-1 flex items-center gap-2">
                        <span className="font-medium text-sm">
                          {profile.profileName || "Untitled farm"}
                        </span>
                        {isActive && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                            Active
                          </span>
                        )}
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      {isEditing ? (
                        <>
                          <button
                            type="button"
                            className="text-xs px-2 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700"
                            onClick={saveEdit}
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            className="text-xs px-2 py-1 rounded border border-border hover:bg-muted"
                            onClick={() => setEditingId(null)}
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            type="button"
                            className="text-xs px-2 py-1 rounded border border-border hover:bg-muted"
                            onClick={() => handleActivate(profile.profileId)}
                          >
                            Load
                          </button>
                          <button
                            type="button"
                            className="text-xs px-2 py-1 rounded border border-border hover:bg-muted"
                            onClick={() => startEdit(profile.profileId)}
                          >
                            Rename
                          </button>
                          <button
                            type="button"
                            className="text-xs px-2 py-1 rounded border border-destructive text-destructive hover:bg-destructive/10"
                            onClick={() => handleDelete(profile.profileId)}
                          >
                            Delete
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="text-xs text-muted-foreground">
                    {isEditing ? (
                      <textarea
                        className="w-full border rounded px-2 py-1 text-xs mt-1"
                        rows={2}
                        value={draftDescription}
                        onChange={(e) => setDraftDescription(e.target.value)}
                      />
                    ) : (
                      <p className="mt-1">
                        {profile.description || "No description"}
                      </p>
                    )}
                    <p className="mt-1 opacity-75">
                      Area: {profile.farmConfig.areaHa} ha · Type: {profile.farmConfig.farmType}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
