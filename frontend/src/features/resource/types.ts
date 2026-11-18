import type { ReactNode } from "react";

export type FieldType = "text" | "email" | "number" | "date" | "datetime" | "select" | "textarea" | "vehicle" | "driver";
export interface Choice { value: string; label: string }

export interface Field {
  name: string;
  label: string;
  type: FieldType;
  required?: boolean;
  /** Required when editing but may be left empty on create (e.g. an auto-generated reference). */
  optionalOnCreate?: boolean;
  options?: Choice[];
  int?: boolean;
  min?: number;
  max?: number;
  maxLength?: number;
  hint?: string;
  full?: boolean; // span both form columns
}

export interface Column<T> { header: string; sort?: string; cell: (row: T) => ReactNode }
export interface FilterDef { name: string; label: string; options: Choice[] }

export interface ResourceConfig<T extends { id: string }> {
  path: string; // API collection, e.g. "vehicles"
  permission: string; // RBAC resource, e.g. "vehicles" -> vehicles:read / vehicles:write
  title: string;
  subtitle: string;
  singular: string;
  searchPlaceholder: string;
  columns: Column<T>[];
  fields: Field[];
  defaults?: Record<string, string>; // initial form values for new records
  filters: FilterDef[];
  defaultSort: string;
  defaultOrder: "asc" | "desc";
  describe: (row: T) => string; // used in the delete confirmation
  deleteNote?: string;
}
