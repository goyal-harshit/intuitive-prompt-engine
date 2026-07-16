import { Panel, PanelNumberBadge } from './Panel'

interface GeneratedImagePanelProps {
  imageUrl: string | null
  generating: boolean
}

export function GeneratedImagePanel({ imageUrl, generating }: GeneratedImagePanelProps) {
  return (
    <Panel
      bodyClassName="flex flex-1 p-2.5"
      title={
        <>
          <PanelNumberBadge n={3} />
          Generated image
        </>
      }
      badge={
        generating && (
          <span
            role="status"
            aria-live="polite"
            className="rounded-full border border-[rgb(110_168_255_/_0.25)] bg-[rgb(110_168_255_/_0.12)] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent"
          >
            generating…
          </span>
        )
      }
    >
      <div
        className="relative flex min-h-0 w-full flex-1 items-center justify-center overflow-hidden rounded-lg border border-border bg-app-bg"
        style={{
          backgroundImage:
            'repeating-linear-gradient(45deg, var(--color-border-soft) 0 2px, transparent 2px 12px)',
        }}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt="Generated scene"
            className="block max-h-full max-w-full animate-[fadein_0.4s_ease] rounded-lg"
          />
        ) : (
          <div className="flex flex-col items-center gap-3.5 p-5 text-center text-[12.5px] text-muted">
            <div
              aria-hidden="true"
              className="h-8 w-8 rounded-full border-[3px] border-border border-t-accent motion-safe:animate-spin"
              hidden={!generating}
            />
            <p>{generating ? 'Rendering your scene…' : 'Waiting for the scene to take shape…'}</p>
          </div>
        )}
      </div>
    </Panel>
  )
}
