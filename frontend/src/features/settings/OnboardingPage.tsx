import { useNavigate } from "react-router-dom";
import { Button, GlassCard } from "@/components/ui";
import { OrgForm } from "./OrgForm";

export function OnboardingPage() {
  const nav = useNavigate();
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div><h1 className="text-gradient text-3xl font-extrabold">Set up your organization</h1><p className="text-muted">A few details help us tailor FleetMind. You can change them later.</p></div>
      <GlassCard hover={false}><OrgForm submitLabel="Save and continue" onSaved={() => nav("/app/dashboard")} /></GlassCard>
      <Button variant="ghost" onClick={() => nav("/app/dashboard")}>Skip for now</Button>
    </div>
  );
}
