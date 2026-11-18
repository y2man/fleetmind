import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SeriesPoint } from "@/types/fleet";

export const tip = { background: "rgb(var(--surface))", border: "1px solid rgb(var(--line))", borderRadius: 12, color: "rgb(var(--ink))" };
export function DeliveriesChart({ data }: { data: SeriesPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data}>
        <defs><linearGradient id="gc" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4d8dff" stopOpacity={0.5} /><stop offset="100%" stopColor="#4d8dff" stopOpacity={0} /></linearGradient></defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#8e98c933" /><XAxis dataKey="label" stroke="#8e98c9" fontSize={12} /><YAxis stroke="#8e98c9" fontSize={12} />
        <Tooltip contentStyle={tip} />
        <Area type="monotone" dataKey="completed" name="Completed" stroke="#4d8dff" fill="url(#gc)" />
        <Area type="monotone" dataKey="delayed" name="Delayed" stroke="#ff6b7d" fill="#ff6b7d22" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
