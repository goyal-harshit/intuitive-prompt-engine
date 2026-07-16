import { Modal } from './Modal'

interface HelpModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const GESTURE_ROWS: [string, string][] = [
  ['🖐️ Spread both hands apart / open arms wide', 'Grander, monumental scale · wide shot'],
  ['🤏 Bring hands together', 'Intimate close-up · small, detailed scale'],
  ['⬆️ Raise a hand upward', 'Something soaring upward · low camera angle'],
  ['⬇️ Lower your hands', "Bird's-eye high angle · grounded, heavy mood"],
  ['☝️ Point one finger to the sky', 'A flying object, high in the sky'],
  ['👉 Point forward at the camera', 'Emphasize a focal subject'],
  ['🌙 Draw a slow circle overhead', 'A glowing orb / moon · night · moonlit glow'],
  ['⭕ Circle a hand in front of you', 'A round, orbiting form · swirling motion'],
  ['↔️ Sweep a hand sideways', 'Sweeping open landscape · panorama'],
  ['🫸 Push palms away from you', 'Subject recedes into the distance'],
  ['🤲 Pull hands toward you', 'Subject drawn close, dominant in frame'],
  ['🔲 Make a rectangle with both hands', 'Deliberate, cinematic composition'],
  ['👋 Wave a hand', 'Windswept, dynamic movement · breezy weather'],
  ['✋ Hold completely still (~2s)', 'Commit — locks the scene & triggers rendering'],
]

export function HelpModal({ open, onOpenChange }: HelpModalProps) {
  return (
    <Modal open={open} onOpenChange={onOpenChange} title="How GestureGPT works">
      <p className="mb-4 text-[13.5px] leading-relaxed text-text">
        GestureGPT never asks you to type a prompt. It watches your hands, posture and expression
        through the webcam, infers your <b>creative intention</b>, and continuously compiles an
        evolving <b>Scene Graph</b> of your imagination into an optimized image prompt.
      </p>

      <div className="mb-2 flex items-stretch gap-2">
        {[
          [
            '1',
            'Perception',
            'MediaPipe tracks 21 hand, 33 body and face landmarks — the dots & lines on the feed.',
          ],
          [
            '2',
            'Understanding',
            'Motion becomes semantic features → gesture "primitives" → weighted intent about your scene.',
          ],
          [
            '3',
            'Creation',
            "When the scene is complete & stable, it's compiled to a prompt and rendered.",
          ],
        ].map(([n, title, desc], i, arr) => (
          <div key={n} className="flex flex-1 items-stretch gap-2">
            <div className="flex-1 rounded-lg border border-border-soft bg-panel-2 p-3">
              <span className="brand-gradient-bg mb-1.5 inline-grid h-5 w-5 place-items-center rounded-full text-[11px] font-bold text-app-bg">
                {n}
              </span>
              <b className="block text-[13px]">{title}</b>
              <p className="text-[11.5px] leading-relaxed text-muted">{desc}</p>
            </div>
            {i < arr.length - 1 && (
              <span className="flex items-center text-lg text-muted-2">→</span>
            )}
          </div>
        ))}
      </div>

      <h3 className="mb-1.5 mt-5 text-xs font-semibold uppercase tracking-wider text-accent">
        Gesture dictionary
      </h3>
      <p className="mb-2.5 text-xs leading-relaxed text-muted">
        Nothing is a hotkey — every movement is <i>evidence</i>, fused over time. Use slow,
        deliberate motions.
      </p>
      <table className="w-full border-collapse text-[12.5px]">
        <thead>
          <tr>
            <th className="border-b border-border px-2.5 py-1.5 text-left text-[11px] font-semibold uppercase tracking-wide text-muted">
              Do this
            </th>
            <th className="border-b border-border px-2.5 py-1.5 text-left text-[11px] font-semibold uppercase tracking-wide text-muted">
              It means
            </th>
          </tr>
        </thead>
        <tbody>
          {GESTURE_ROWS.map(([gesture, meaning]) => (
            <tr key={gesture} className="hover:bg-white/[0.02]">
              <td className="w-[46%] border-b border-border-soft px-2.5 py-2 align-top text-text">
                {gesture}
              </td>
              <td className="border-b border-border-soft px-2.5 py-2 align-top text-muted">
                {meaning}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3 className="mb-1.5 mt-5 text-xs font-semibold uppercase tracking-wider text-accent">
        Mood &amp; atmosphere cues (sustained)
      </h3>
      <ul className="flex flex-col gap-1.5">
        {[
          <>
            <b>Fast motion</b> → energetic, dramatic mood · <b>slow motion</b> → calm, serene
          </>,
          <>
            <b>Smooth motion</b> → soft diffuse light
          </>,
          <>
            <b>Smile</b> → warm vibrant palette · <b>frown</b> → moody chiaroscuro, cold palette
          </>,
          <>
            <b>Tilt head up</b> → expansive sky above · <b>raised brows / wide eyes</b> → dramatic
            atmosphere
          </>,
        ].map((item, i) => (
          <li key={i} className="relative pl-4 text-[12.5px] leading-relaxed text-muted">
            <span className="absolute left-0.5 font-bold text-accent">›</span>
            {item}
          </li>
        ))}
      </ul>

      <p className="mt-4 text-xs leading-relaxed text-muted">
        Tip: the image regenerates on its own as the scene changes meaningfully. Use{' '}
        <b>Reset scene</b> to start a fresh imagination, <b>Pause</b> to freeze tracking, and{' '}
        <b>Stop</b> to end the session and turn the camera off.
      </p>
    </Modal>
  )
}
