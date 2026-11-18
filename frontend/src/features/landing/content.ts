export const FEATURES = [
  ["Live fleet tracking", "See every vehicle, route and geofence on one map, updated in real time."],
  ["Route optimization", "Compare multi-stop plans by distance, time and cost, with the assumptions shown."],
  ["Predictive maintenance", "Catch service needs before they become breakdowns."],
  ["Fuel intelligence", "Track consumption per vehicle and flag unusual patterns."],
  ["Delivery management", "Assign drivers, set deadlines and follow every shipment to proof of delivery."],
  ["AI operations assistant", "Ask questions in plain language and get answers from your own data."],
] as const;

export const STEPS = [
  ["Connect your fleet", "Import vehicles and drivers, or start from the demo data."],
  ["Plan and dispatch", "Create deliveries and let FleetMind suggest routes and assignments."],
  ["Monitor in real time", "Follow vehicles, alerts and delays from the command center."],
  ["Improve with insight", "Use analytics and AI recommendations to cut cost and delay."],
] as const;

export const STATS = [
  { label: "Fewer late deliveries", value: 23, suffix: "%" },
  { label: "Fuel cost reduction", value: 14, suffix: "%" },
  { label: "Unplanned downtime cut", value: 31, suffix: "%" },
  { label: "Vehicles per dashboard", value: 500, suffix: "+" },
] as const;

export const TESTIMONIALS = [
  ["“Dispatch used to take us an hour each morning. Now it is a few clicks.”", "Demo user · Operations lead"],
  ["“The maintenance alerts caught a brake issue before it cost us a week.”", "Demo user · Fleet manager"],
  ["“Finally one place to see fuel, drivers and deliveries together.”", "Demo user · Logistics director"],
] as const;

export const PLANS = [
  { name: "Starter", price: "$49", note: "per month · up to 10 vehicles", items: ["Fleet and driver management", "Live tracking", "Basic reports"] },
  { name: "Growth", price: "$199", note: "per month · up to 75 vehicles", items: ["Everything in Starter", "Route optimization", "AI assistant", "Predictive maintenance"], hot: true },
  { name: "Enterprise", price: "Custom", note: "unlimited vehicles", items: ["Everything in Growth", "SSO and audit logs", "Dedicated support"] },
] as const;

export const FAQ = [
  ["Is the data on this site real?", "No. Statistics, testimonials and pricing here are clearly labeled demo content."],
  ["How does FleetMind use AI?", "AI features can help summarize reports and answer questions about your organization’s records."],
  ["Can I use real GPS devices?", "Real GPS integrations are planned. Demo mode uses clearly labeled simulated positions."],
  ["Is my organization’s data isolated?", "Yes. Every record is scoped to an organization and enforced on the server."],
] as const;
