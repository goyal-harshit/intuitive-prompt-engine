interface ErrorBannerProps {
  title: string
  message: string
  warn: boolean
  onDismiss: () => void
}

export function ErrorBanner({ title, message, warn, onDismiss }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className={`mx-[22px] mt-3 flex animate-[slidein_0.25s_ease] items-start gap-3 rounded-xl border p-3.5 ${
        warn
          ? 'border-[rgb(255_191_71_/_0.4)] bg-gradient-to-b from-[rgb(255_191_71_/_0.14)] to-[rgb(255_191_71_/_0.05)]'
          : 'border-[rgb(255_107_107_/_0.4)] bg-gradient-to-b from-[rgb(255_107_107_/_0.14)] to-[rgb(255_107_107_/_0.06)]'
      }`}
    >
      <div aria-hidden="true" className={`mt-px flex-shrink-0 ${warn ? 'text-busy' : 'text-err'}`}>
        <svg
          viewBox="0 0 24 24"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 9v4" />
          <path d="M12 17h.01" />
          <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
        </svg>
      </div>
      <div className="flex flex-1 flex-col gap-0.5">
        <strong className="text-[13px] font-semibold">{title}</strong>
        <span className="text-xs leading-relaxed text-muted">{message}</span>
      </div>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss"
        className="flex-shrink-0 rounded-md px-1.5 py-0.5 text-sm leading-none text-muted hover:bg-white/[0.06] hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
      >
        ✕
      </button>
    </div>
  )
}
