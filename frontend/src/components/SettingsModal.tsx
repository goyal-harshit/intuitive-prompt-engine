import { useState } from 'react'
import { Modal } from './Modal'
import { getSavedBackendUrl, setSavedBackendUrl } from '../lib/backendUrl'

interface SettingsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SettingsModal({ open, onOpenChange }: SettingsModalProps) {
  const [value, setValue] = useState('')
  const [prevOpen, setPrevOpen] = useState(open)

  if (open !== prevOpen) {
    setPrevOpen(open)
    if (open) setValue(getSavedBackendUrl())
  }

  const save = () => {
    setSavedBackendUrl(value)
    onOpenChange(false)
  }

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="API Backend Settings"
      maxWidthClassName="max-w-[420px]"
    >
      <p className="mb-4 text-[12.5px] leading-relaxed text-muted">
        Configure the local or remote Python server address. This allows the static frontend hosted
        on GitHub Pages to connect to the backend running on your machine.
      </p>
      <div className="mb-4 flex flex-col gap-2">
        <label htmlFor="input-backend-url" className="text-xs font-medium text-text">
          Backend API URL
        </label>
        <input
          id="input-backend-url"
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="http://localhost:8000"
          className="rounded-lg border border-border bg-panel px-3 py-2 text-[13px] text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        />
      </div>
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="rounded-lg border border-border bg-panel px-3.5 py-2 text-[12.5px] font-semibold text-text hover:bg-panel-2 hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={save}
          className="brand-gradient-bg rounded-lg px-3.5 py-2 text-[12.5px] font-semibold text-app-bg focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          Save
        </button>
      </div>
    </Modal>
  )
}
