import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SeriesPoint } from "@/types/fleet";
import { tip } from "./DeliveriesChart";

export function FuelChart({ data }: { data: SeriesPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#8e98c933" /><XAxis dataKey="label" stroke="#8e98c9" fontSize={12} /><YAxis stroke="#8e98c9" fontSize={12} />
        <Tooltip contentStyle={tip} cursor={{ fill: "#4d8dff22" }} /><Bar dataKey="cost" name="Fuel cost" fill="#9b6bff" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
