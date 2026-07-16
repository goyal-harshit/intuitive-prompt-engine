import type { StatusTone } from '../hooks/useSession'

interface TopBarProps {
  statusText: string
  statusTone: StatusTone
  starting: boolean
  sessionActive: boolean
  paused: boolean
  onStart: () => void
  onStop: () => void
  onTogglePause: () => void
  onReset: () => void
  onOpenSettings: () => void
  onOpenHelp: () => void
}

const TONE_CLASSES: Record<StatusTone, string> = {
  ok: 'bg-ok shadow-[0_0_10px_var(--color-ok)] animate-[pulse-dot_2s_infinite]',
  busy: 'bg-busy shadow-[0_0_8px_var(--color-busy)] animate-[pulse-dot_1.1s_infinite]',
  err: 'bg-err shadow-[0_0_8px_var(--color-err)]',
  idle: 'bg-muted-2',
}

function Logo() {
  return (
    <div
      aria-hidden="true"
      className="brand-gradient-bg grid h-[38px] w-[38px] place-items-center rounded-xl text-app-bg shadow-[0_6px_18px_rgb(110_168_255_/_0.35)]"
    >
      <svg
        viewBox="0 0 24 24"
        width="22"
        height="22"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M6 11V6.5a1.5 1.5 0 0 1 3 0V10" />
        <path d="M9 10V4.5a1.5 1.5 0 0 1 3 0V10" />
        <path d="M12 10V5.5a1.5 1.5 0 0 1 3 0V11" />
        <path d="M15 11V7.5a1.5 1.5 0 0 1 3 0V15a5 5 0 0 1-5 5h-1.5a5 5 0 0 1-4.2-2.3L6 15c-.8-1.2.9-2.6 2-1.6L9 15" />
      </svg>
    </div>
  )
}

export function TopBar({
  statusText,
  statusTone,
  starting,
  sessionActive,
  paused,
  onStart,
  onStop,
  onTogglePause,
  onReset,
  onOpenSettings,
  onOpenHelp,
}: TopBarProps) {
  return (
    <header className="flex flex-none items-center gap-[18px] border-b border-border-soft bg-app-bg/70 px-[22px] py-[11px] backdrop-blur-md">
      <div className="flex items-center gap-3">
        <Logo />
        <div>
          <h1 className="text-lg font-bold tracking-tight">
            Gesture<span className="brand-gradient-text">GPT</span>
          </h1>
          <p className="mt-px text-[11.5px] text-muted">Intent-driven creative interface</p>
        </div>
      </div>

      <div className="flex items-center gap-2 rounded-full border border-border bg-panel px-3 py-1.5">
        <span
          className={`h-2 w-2 rounded-full transition-all ${TONE_CLASSES[statusTone]}`}
          aria-hidden="true"
        />
        <span role="status" aria-live="polite" className="text-xs font-medium text-muted">
          {statusText}
        </span>
      </div>

      <div className="ml-auto flex flex-wrap justify-end gap-2">
        <button
          type="button"
          onClick={onOpenSettings}
          title="Backend Settings"
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-panel px-3.5 py-2 text-[12.5px] font-semibold text-text hover:border-accent hover:bg-panel-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          ⚙️ Settings
        </button>
        <button
          type="button"
          onClick={onOpenHelp}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-panel px-3.5 py-2 text-[12.5px] font-semibold text-text hover:border-accent hover:bg-panel-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          How it works
        </button>
        <button
          type="button"
          onClick={onStart}
          disabled={starting || sessionActive}
          className="brand-gradient-bg inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[12.5px] font-semibold text-app-bg shadow-[0_6px_16px_rgb(110_168_255_/_0.25)] hover:brightness-[1.07] disabled:cursor-default disabled:opacity-40 disabled:hover:brightness-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          <span aria-hidden="true" className="text-[9px]">
            ●
          </span>{' '}
          Start session
        </button>
        <button
          type="button"
          onClick={onStop}
          disabled={!sessionActive}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[rgb(255_107_107_/_0.4)] bg-[rgb(255_107_107_/_0.14)] px-3.5 py-2 text-[12.5px] font-semibold text-[#ff8f8f] hover:border-err hover:bg-[rgb(255_107_107_/_0.22)] disabled:cursor-default disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          <span aria-hidden="true" className="text-[9px]">
            ■
          </span>{' '}
          Stop
        </button>
        <button
          type="button"
          onClick={onTogglePause}
          disabled={!sessionActive}
          className="rounded-lg border border-border bg-panel px-3.5 py-2 text-[12.5px] font-semibold text-text hover:border-accent hover:bg-panel-2 disabled:cursor-default disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          {paused ? 'Resume' : 'Pause'}
        </button>
        <button
          type="button"
          onClick={onReset}
          disabled={!sessionActive}
          className="rounded-lg border border-border bg-panel px-3.5 py-2 text-[12.5px] font-semibold text-text hover:border-accent hover:bg-panel-2 disabled:cursor-default disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          Reset scene
        </button>
      </div>
    </header>
  )
}
