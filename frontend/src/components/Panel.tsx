import type { ReactNode } from 'react'

interface PanelProps {
  title: ReactNode
  badge?: ReactNode
  flex?: 'flex-1' | 'flex-none'
  bodyClassName?: string
  children: ReactNode
}

export function Panel({ title, badge, flex = 'flex-1', bodyClassName, children }: PanelProps) {
  return (
    <section
      className={`flex min-h-0 ${flex} flex-col overflow-hidden rounded-[13px] border border-border bg-gradient-to-b from-panel to-app-bg-2 shadow-[0_6px_22px_rgb(0_0_0_/_0.32)]`}
    >
      <div className="flex items-center justify-between gap-2 border-b border-border-soft px-3.5 py-2.5">
        <h2 className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-muted">
          {title}
        </h2>
        {badge}
      </div>
      <div className={bodyClassName ?? 'min-h-0 flex-1 overflow-y-auto p-3.5'}>{children}</div>
    </section>
  )
}

export function PanelNumberBadge({ n }: { n: number }) {
  return (
    <span className="brand-gradient-bg inline-grid h-[18px] w-[18px] place-items-center rounded-full text-[11px] font-bold text-app-bg">
      {n}
    </span>
  )
}
