import { useEffect, useRef } from 'react'
import { frameUrl } from '../api/client'
import { Panel, PanelNumberBadge } from './Panel'

interface CameraPanelProps {
  sessionId: string | null
}

export function CameraPanel({ sessionId }: CameraPanelProps) {
  const imgRef = useRef<HTMLImageElement | null>(null)
  const activeRef = useRef(false)

  useEffect(() => {
    const img = imgRef.current
    if (!sessionId || !img) {
      activeRef.current = false
      return undefined
    }
    activeRef.current = true

    const pump = () => {
      if (!activeRef.current || !imgRef.current) return
      imgRef.current.src = frameUrl(sessionId)
    }
    img.onload = () => {
      if (activeRef.current) requestAnimationFrame(pump)
    }
    img.onerror = () => {
      if (activeRef.current) setTimeout(pump, 250)
    }
    pump()

    return () => {
      activeRef.current = false
      img.onload = null
      img.onerror = null
      img.removeAttribute('src')
    }
  }, [sessionId])

  return (
    <Panel
      flex="flex-none"
      bodyClassName="p-3"
      title={
        <>
          <PanelNumberBadge n={1} />
          Camera · gesture tracking
        </>
      }
      badge={
        <span
          className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
            sessionId
              ? 'border-[rgb(63_208_122_/_0.3)] bg-[rgb(63_208_122_/_0.12)] text-ok'
              : 'border-[rgb(110_168_255_/_0.25)] bg-[rgb(110_168_255_/_0.12)] text-accent'
          }`}
        >
          {sessionId ? 'live' : 'offline'}
        </span>
      }
    >
      <div className="relative flex aspect-[4/3] w-full items-center justify-center overflow-hidden rounded-lg border border-border bg-[#05070b]">
        <img
          ref={imgRef}
          alt="Live camera with gesture tracking"
          hidden={!sessionId}
          className="block h-full w-full object-cover"
        />
        {!sessionId && (
          <div className="flex flex-col items-center gap-2.5 p-[18px] text-center text-xs text-muted-2">
            <svg
              viewBox="0 0 24 24"
              width="34"
              height="34"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="m22 8-6 4 6 4V8z" />
              <rect x="2" y="6" width="14" height="12" rx="2" />
            </svg>
            <p>
              Camera is off. Click <b className="text-muted">Start session</b> to begin tracking.
            </p>
          </div>
        )}
      </div>
    </Panel>
  )
}
