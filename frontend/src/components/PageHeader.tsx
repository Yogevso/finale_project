import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  eyebrow?: string
  actions?: ReactNode
  meta?: ReactNode
  className?: string
}

export default function PageHeader({
  title,
  subtitle,
  eyebrow = 'Internal Portal',
  actions,
  meta,
  className = '',
}: PageHeaderProps) {
  return (
    <section
      className={`surface-card animate-fade-in rounded-2xl border border-sky-100 bg-gradient-to-r from-white via-sky-50/70 to-white px-6 py-5 dark:border-slate-800 dark:from-slate-900 dark:via-slate-900 dark:to-slate-950 ${className}`.trim()}
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-500 dark:text-slate-400">{eyebrow}</div>
          <h1 className="page-title mt-1">{title}</h1>
          {subtitle && <p className="body-copy mt-1 max-w-2xl">{subtitle}</p>}
          {meta && <div className="mt-3">{meta}</div>}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </section>
  )
}
