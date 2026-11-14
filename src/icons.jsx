// Иконки в стиле макета: контурные, цвет берётся из currentColor.

const base = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.4,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
}

export const CloudUploadIcon = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}>
    <path d="M17.5 19H7a5 5 0 1 1 .9-9.92A6 6 0 0 1 19.5 11a4 4 0 0 1-2 8z" />
    <path d="M12 17v-6M9.5 13l2.5-2.5 2.5 2.5" />
  </svg>
)

export const ScanIcon = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}>
    <path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2" />
    <path d="M8 8h8v8H8zM6 12h12" />
  </svg>
)

export const NoteIcon = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}>
    <circle cx="8.5" cy="17.5" r="3" />
    <path d="M11.5 17.5V4l6 3v4" />
  </svg>
)

export const NotesIcon = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}>
    <path d="M9 18V5l12-2v13" />
    <circle cx="6" cy="18" r="3" />
    <circle cx="18" cy="16" r="3" />
  </svg>
)

export const CheckBadge = () => (
  <svg viewBox="0 0 16 16" {...base} strokeWidth={2}>
    <path d="M3.5 8.5l3 3 6-6.5" />
  </svg>
)

export const PlayBadge = () => (
  <svg viewBox="0 0 16 16" aria-hidden="true" fill="currentColor">
    <path d="M5.5 3.5v9l7-4.5z" />
  </svg>
)

export const ClockBadge = () => (
  <svg viewBox="0 0 16 16" {...base} strokeWidth={1.6}>
    <circle cx="8" cy="8" r="6" />
    <path d="M8 4.5V8l2.5 1.5" />
  </svg>
)

export const SpinnerIcon = (p) => (
  <svg viewBox="0 0 50 50" aria-hidden="true" {...p}>
    <circle cx="25" cy="25" r="20" fill="none" stroke="currentColor" strokeOpacity="0.15" strokeWidth="5" />
    <circle
      cx="25" cy="25" r="20" fill="none" stroke="currentColor" strokeWidth="5"
      strokeLinecap="round" strokeDasharray="40 126"
    />
  </svg>
)

export const CrossCircleIcon = (p) => (
  <svg viewBox="0 0 24 24" {...base} strokeWidth={1.5} {...p}>
    <circle cx="12" cy="12" r="9.5" />
    <path d="M9 9l6 6M15 9l-6 6" />
  </svg>
)

export const DownloadIcon = (p) => (
  <svg viewBox="0 0 24 24" {...base} strokeWidth={1.8} {...p}>
    <path d="M12 4v11M7.5 11l4.5 4.5 4.5-4.5M5 20h14" />
  </svg>
)

export const UploadArrowIcon = (p) => (
  <svg viewBox="0 0 24 24" {...base} strokeWidth={1.4} {...p}>
    <path d="M12 16V4M7.5 8.5L12 4l4.5 4.5M4 20h16" />
  </svg>
)
