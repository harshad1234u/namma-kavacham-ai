import type { ReactNode } from "react";

export function Section({ icon, title, children, id }: { icon: ReactNode; title: string; children: ReactNode; id: string }) {
  return (
    <section aria-labelledby={id} className="rounded-lg border border-line bg-white p-4 shadow-card sm:p-6">
      <h3 id={id} className="flex items-center gap-2 text-lg font-semibold text-navy">
        {icon}
        {title}
      </h3>
      <div className="mt-4">{children}</div>
    </section>
  );
}
