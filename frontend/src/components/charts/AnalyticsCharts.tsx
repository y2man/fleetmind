import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AnalyticsPoint } from "@/types/analytics";
import { tip } from "./DeliveriesChart";

const GRID = "#8e98c933";
const AXIS = "#8e98c9";

export function DeliveryTrendChart({ data }: { data: AnalyticsPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} /><XAxis dataKey="label" stroke={AXIS} fontSize={12} minTickGap={24} /><YAxis stroke={AXIS} fontSize={12} allowDecimals={false} />
        <Tooltip contentStyle={tip} /><Legend />
        <Line type="monotone" dataKey="created" name="Created" stroke="#9b6bff" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="delivered" name="Completed" stroke="#4d8dff" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="late" name="Late" stroke="#ff6b7d" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function SpendChart({ data }: { data: AnalyticsPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} /><XAxis dataKey="label" stroke={AXIS} fontSize={12} minTickGap={24} /><YAxis stroke={AXIS} fontSize={12} />
        <Tooltip contentStyle={tip} cursor={{ fill: "#4d8dff22" }} /><Legend />
        <Bar dataKey="fuel_cost" name="Fuel" stackId="spend" fill="#9b6bff" />
        <Bar dataKey="maintenance_cost" name="Maintenance" stackId="spend" fill="#2fe0a0" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
