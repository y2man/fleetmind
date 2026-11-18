import { Navigate, Route, Routes } from "react-router-dom";
import { LandingPage } from "@/features/landing/LandingPage";
import { StatusPage } from "@/features/dashboard/StatusPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { DesignShowcase } from "@/features/dashboard/DesignShowcase";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/features/auth/ProtectedRoute";
import { SignInPage } from "@/features/auth/SignInPage";
import { SignUpPage } from "@/features/auth/SignUpPage";
import { ForgotPasswordPage } from "@/features/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "@/features/auth/ResetPasswordPage";
import { VerifyEmailPage } from "@/features/auth/VerifyEmailPage";
import { ProfilePage } from "@/features/settings/ProfilePage";
import { OnboardingPage } from "@/features/settings/OnboardingPage";
import { TeamPage } from "@/features/team/TeamPage";
import { AuditPage } from "@/features/audit/AuditPage";
import { VehiclesPage } from "@/features/fleet/VehiclesPage";
import { DriversPage } from "@/features/drivers/DriversPage";
import { DeliveriesPage } from "@/features/deliveries/DeliveriesPage";
import { ProofOfDeliveryPage } from "@/features/deliveries/ProofOfDeliveryPage";
import { CustomerTrackingPage } from "@/features/deliveries/CustomerTrackingPage";
import { DeliverySMSPage } from "@/features/deliveries/DeliverySMSPage";
import { PublicTrackingPage } from "@/features/tracking/PublicTrackingPage";
import { FuelPage } from "@/features/fuel/FuelPage";
import { TrackingPage } from "@/features/tracking/TrackingPage";
import { RoutesPage } from "@/features/routes/RoutesPage";
import { FleetPlannerPage } from "@/features/routes/FleetPlannerPage";
import { MaintenancePage } from "@/features/maintenance/MaintenancePage";
import { AIPage } from "@/features/ai/AIPage";
import { AnalyticsPage } from "@/features/analytics/AnalyticsPage";
import { NotificationsPage } from "@/features/notifications/NotificationsPage";
import { ScrollProgress } from "@/components/animations/ScrollProgress";

export default function App() {
  return (
    <>
      <ScrollProgress />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/status" element={<StatusPage />} />
        <Route path="/signin" element={<SignInPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/track" element={<PublicTrackingPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/app" element={<AppShell />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="onboarding" element={<OnboardingPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="design" element={<DesignShowcase />} />
            <Route element={<ProtectedRoute permission="vehicles:read" />}><Route path="fleet" element={<VehiclesPage />} /></Route>
            <Route element={<ProtectedRoute permission="drivers:read" />}><Route path="drivers" element={<DriversPage />} /></Route>
            <Route element={<ProtectedRoute permission="deliveries:read" />}>
              <Route path="deliveries" element={<DeliveriesPage />} />
              <Route path="deliveries/:deliveryId/proof" element={<ProofOfDeliveryPage />} />
              <Route path="deliveries/:deliveryId/tracking" element={<CustomerTrackingPage />} />
              <Route element={<ProtectedRoute permission="deliveries:write" />}>
                <Route path="deliveries/:deliveryId/sms" element={<DeliverySMSPage />} />
              </Route>
            </Route>
            <Route element={<ProtectedRoute permission="vehicles:read" />}><Route path="tracking" element={<TrackingPage />} /></Route>
            <Route element={<ProtectedRoute permission="routes:read" />}><Route path="routes" element={<RoutesPage />} /></Route>
            <Route element={<ProtectedRoute permission="routes:read" />}><Route path="fleet-planner" element={<FleetPlannerPage />} /></Route>
            <Route element={<ProtectedRoute permission="fuel:read" />}><Route path="fuel" element={<FuelPage />} /></Route>
            <Route element={<ProtectedRoute permission="maintenance:read" />}><Route path="maintenance" element={<MaintenancePage />} /></Route>
            <Route element={<ProtectedRoute permission="analytics:read" />}>
              <Route path="analytics" element={<AnalyticsPage />} />
              <Route path="notifications" element={<NotificationsPage />} />
            </Route>
            <Route element={<ProtectedRoute permission="ai:use" />}><Route path="ai" element={<AIPage />} /></Route>
            <Route element={<ProtectedRoute permission="users:read" />}><Route path="team" element={<TeamPage />} /></Route>
            <Route element={<ProtectedRoute permission="audit:read" />}><Route path="audit" element={<AuditPage />} /></Route>
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
