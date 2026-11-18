import { Modal } from "@/components/ui";
import { GENERAL_SHORTCUTS, GO_SHORTCUTS } from "@/config/shortcuts";
import { NAV } from "@/config/nav";
import { useAuth } from "@/store/auth";
import { useUi } from "@/store/ui";

const Key = ({ children }: { children: string }) => <kbd className="rounded-md border border-line bg-bg/60 px-1.5 py-0.5 font-mono text-xs">{children}</kbd>;

export function ShortcutsModal() {
  const { helpOpen, setHelp } = useUi();
  const can = useAuth((s) => s.can);
  const pages = GO_SHORTCUTS.flatMap((s) => {
    const item = NAV.find((n) => n.to === s.to);
    return item && (!item.permission || can(item.permission)) ? [{ key: s.key, label: item.label }] : [];
  });
  return (
    <Modal open={helpOpen} onClose={() => setHelp(false)} title="Keyboard shortcuts" wide>
      <div className="grid gap-6 sm:grid-cols-2">
        <section>
          <h3 className="mb-2 text-sm font-semibold">General</h3>
          <ul className="space-y-2 text-sm">
            {GENERAL_SHORTCUTS.map((s) => <li key={s.keys} className="flex items-start justify-between gap-3"><span className="text-muted">{s.label}</span><Key>{s.keys}</Key></li>)}
          </ul>
        </section>
        <section>
          <h3 className="mb-2 text-sm font-semibold">Go to page <span className="font-normal text-muted">(press G, then the key)</span></h3>
          <ul className="space-y-2 text-sm">
            {pages.map((p) => <li key={p.key} className="flex items-center justify-between gap-3"><span className="text-muted">{p.label}</span><span className="flex gap-1"><Key>g</Key><Key>{p.key}</Key></span></li>)}
          </ul>
        </section>
      </div>
      <p className="mt-4 text-xs text-muted">Shortcuts are off while you type in a field or while a dialog is open.</p>
    </Modal>
  );
}
