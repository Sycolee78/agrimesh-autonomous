"use client";

import * as React from "react";
import { useFarmStore } from "@/store/farmStore";
import { useFarmProfilesStore } from "@/store/farmProfilesStore";
import type { FarmType } from "@/types/farm";

interface FarmOnboardingWizardProps {
  open: boolean;
  onClose: () => void;
}

type Step = 1 | 2 | 3 | 4;

export function FarmOnboardingWizard({ open, onClose }: FarmOnboardingWizardProps) {
  const [step, setStep] = React.useState<Step>(1);
  const [areaHa, setAreaHa] = React.useState<string>("10");
  const [farmName, setFarmName] = React.useState("My Farm");
  const [farmType, setFarmType] = React.useState<FarmType>("mixed");
  const [description, setDescription] = React.useState("");

  const { selectedLocation, initializeFarm, farmConfig, updateFarmType } = useFarmStore();
  const { createProfile } = useFarmProfilesStore();

  React.useEffect(() => {
    if (!open) {
      setStep(1);
    }
  }, [open]);

  if (!open) return null;

  const nextStep = () => setStep((s) => (s < 4 ? ((s + 1) as Step) : s));
  const prevStep = () => setStep((s) => (s > 1 ? ((s - 1) as Step) : s));

  const handleStart = () => {
    if (!selectedLocation) return;
    const area = Number(areaHa) || 1;
    initializeFarm(selectedLocation, area);
    setStep(2);
  };

  const handleFinish = () => {
    if (!farmConfig) return;
    // ensure farm type and name are updated
    updateFarmType(farmType);
    const updatedConfig = {
      ...farmConfig,
      name: farmName,
    };
    createProfile(updatedConfig, farmName, description);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-xl rounded-lg bg-background p-6 shadow-xl border border-border">
        <h2 className="text-lg font-semibold mb-4">New Farm Setup</h2>

        <div className="mb-4 text-xs text-muted-foreground">Step {step} of 4</div>

        {step === 1 && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Start by selecting your farm location on the map, then set the total farm area.
            </p>
            <div>
              <label className="block text-sm mb-1">Total area (hectares)</label>
              <input
                type="number"
                min={1}
                className="w-full border rounded px-2 py-1 text-sm"
                value={areaHa}
                onChange={(e) => setAreaHa(e.target.value)}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Hint: Click on the map to set your farm location before continuing.
            </p>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3">
            <div>
              <label className="block text-sm mb-1">Farm name</label>
              <input
                className="w-full border rounded px-2 py-1 text-sm"
                value={farmName}
                onChange={(e) => setFarmName(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Farm type</label>
              <select
                className="w-full border rounded px-2 py-1 text-sm"
                value={farmType}
                onChange={(e) => setFarmType(e.target.value as FarmType)}
              >
                <option value="crops">Crops only</option>
                <option value="livestock">Livestock only</option>
                <option value="mixed">Mixed (crops + livestock)</option>
              </select>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Configure your crops, livestock, and zones in the main panel after finishing this wizard.
              For now, we&apos;ll create the shell of your farm profile.
            </p>
            <p className="text-xs text-muted-foreground">
              Tip: Once the farm is created, you can refine enterprises and zoning from the Configure
              tab.
            </p>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Add an optional description so you can recognize this farm later.
            </p>
            <textarea
              className="w-full border rounded px-2 py-1 text-sm min-h-[80px]"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        )}

        <div className="mt-6 flex justify-between">
          <div className="space-x-2">
            <button
              type="button"
              className="text-sm px-3 py-1 rounded border border-border hover:bg-muted"
              onClick={onClose}
            >
              Cancel
            </button>
            {step > 1 && (
              <button
                type="button"
                className="text-sm px-3 py-1 rounded border border-border hover:bg-muted"
                onClick={prevStep}
              >
                Back
              </button>
            )}
          </div>
          <div className="space-x-2">
            {step === 1 && (
              <button
                type="button"
                className="text-sm px-3 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
                onClick={handleStart}
                disabled={!selectedLocation}
              >
                Continue
              </button>
            )}
            {step > 1 && step < 4 && (
              <button
                type="button"
                className="text-sm px-3 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700"
                onClick={nextStep}
              >
                Next
              </button>
            )}
            {step === 4 && (
              <button
                type="button"
                className="text-sm px-3 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
                onClick={handleFinish}
                disabled={!farmConfig}
              >
                Create farm
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
