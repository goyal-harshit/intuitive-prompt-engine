import * as Dialog from '@radix-ui/react-dialog'
import type { ReactNode } from 'react'

interface ModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  children: ReactNode
  maxWidthClassName?: string
}

export function Modal({
  open,
  onOpenChange,
  title,
  children,
  maxWidthClassName = 'max-w-[880px]',
}: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[100] animate-[fadein_0.2s_ease] bg-black/70 backdrop-blur-sm" />
        <Dialog.Content
          className={`fixed left-1/2 top-1/2 z-[100] max-h-[88vh] w-[calc(100%-48px)] ${maxWidthClassName} -translate-x-1/2 -translate-y-1/2 animate-[fadein_0.2s_ease] overflow-hidden rounded-2xl border border-border bg-gradient-to-b from-panel to-app-bg-2 shadow-2xl focus:outline-none`}
        >
          <div className="flex items-center justify-between border-b border-border-soft px-5 py-4">
            <Dialog.Title className="text-base font-bold text-text">{title}</Dialog.Title>
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Close"
                className="rounded-md p-1.5 text-lg leading-none text-muted hover:bg-white/5 hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
              >
                ✕
              </button>
            </Dialog.Close>
          </div>
          <div className="max-h-[calc(88vh-64px)] overflow-y-auto px-5 py-5">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
