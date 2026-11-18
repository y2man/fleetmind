import { Activity, BarChart3, Bell, Fuel, Contact, LayoutDashboard, MapPin, Package, Palette, Route, ScrollText, Sparkles, Truck, UserCircle, Users, Wrench, type LucideIcon } from "lucide-react";

export interface NavItem { to: string; label: string; icon: LucideIcon; permission?: string }
// Only routes that exist are listed; later phases add the rest.
export const NAV: NavItem[] = [
  { to: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/fleet", label: "Fleet", icon: Truck, permission: "vehicles:read" },
  { to: "/app/drivers", label: "Drivers", icon: Contact, permission: "drivers:read" },
  { to: "/app/deliveries", label: "Deliveries", icon: Package, permission: "deliveries:read" },
  { to: "/app/tracking", label: "Live map", icon: MapPin, permission: "vehicles:read" },
  { to: "/app/routes", label: "Routes", icon: Route, permission: "routes:read" },
  { to: "/app/fleet-planner", label: "Fleet planner", icon: Route, permission: "routes:read" },
  { to: "/app/fuel", label: "Fuel", icon: Fuel, permission: "fuel:read" },
  { to: "/app/maintenance", label: "Maintenance", icon: Wrench, permission: "maintenance:read" },
  { to: "/app/analytics", label: "Analytics", icon: BarChart3, permission: "analytics:read" },
  { to: "/app/notifications", label: "Notifications", icon: Bell, permission: "analytics:read" },
  { to: "/app/ai", label: "AI center", icon: Sparkles, permission: "ai:use" },
  { to: "/app/team", label: "Team", icon: Users, permission: "users:read" },
  { to: "/app/audit", label: "Audit log", icon: ScrollText, permission: "audit:read" },
  { to: "/app/profile", label: "Profile", icon: UserCircle },
  { to: "/app/design", label: "Design system", icon: Palette },
  { to: "/status", label: "System status", icon: Activity },
];
