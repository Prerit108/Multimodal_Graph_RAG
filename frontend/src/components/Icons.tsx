/* Minimal stroke icon set — no runtime dependency, inherits currentColor. */
type P = { className?: string; size?: number };

const base = (size = 17) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export const IconUpload = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <path d="m7 9 5-5 5 5" />
    <path d="M12 4v12" />
  </svg>
);

export const IconChat = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 9 9 0 0 1-3.9-.9L3 20.5l1.5-4.1A8.4 8.4 0 0 1 12 3.1a8.4 8.4 0 0 1 9 8.4Z" />
  </svg>
);

export const IconQuiz = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M9 11l2 2 4-4" />
    <path d="M20 12a8 8 0 1 1-4.6-7.2" />
    <path d="M15 4.5 20 4l-.5 5" />
  </svg>
);

export const IconChart = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M3 3v17a1 1 0 0 0 1 1h17" />
    <path d="m7 15 3.5-4 3 2.5L20 7" />
  </svg>
);

export const IconClock = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </svg>
);

export const IconDoc = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" />
    <path d="M14 3v5h5" />
  </svg>
);

export const IconTrash = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M4 7h16" />
    <path d="M10 11v6M14 11v6" />
    <path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12" />
    <path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
  </svg>
);

export const IconWarn = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M12 9v4M12 17h.01" />
    <path d="M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
  </svg>
);

export const IconCheck = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="m4 12 5 5L20 6" />
  </svg>
);

export const IconX = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M18 6 6 18M6 6l12 12" />
  </svg>
);

export const IconSpark = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
    <path d="M5.6 5.6 7.8 7.8M16.2 16.2l2.2 2.2M18.4 5.6l-2.2 2.2M7.8 16.2l-2.2 2.2" />
  </svg>
);

export const IconBook = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v18H6.5A2.5 2.5 0 0 0 4 22Z" />
    <path d="M4 17.5A2.5 2.5 0 0 1 6.5 15H20" />
  </svg>
);

export const IconPin = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11Z" />
    <circle cx="12" cy="10" r="2.5" />
  </svg>
);