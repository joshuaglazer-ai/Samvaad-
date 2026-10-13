/** Simple line icons (24×24, stroke). Always pair with a visible text label. */
const PATHS: Record<string, string> = {
  star: "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z",
  globe: "M12 3a9 9 0 100 18 9 9 0 000-18zM3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z",
  mic: "M12 3a3 3 0 00-3 3v6a3 3 0 006 0V6a3 3 0 00-3-3zM5 11a7 7 0 0014 0M12 18v3M8 21h8",
  speaker: "M4 9v6h4l5 4V5L8 9H4zM16.5 8.5a5 5 0 010 7M19 6a8.5 8.5 0 010 12",
  stop: "M7 7h10v10H7z",
  learner: "M12 4l9 4-9 4-9-4 9-4zM6 10v5c0 1.7 2.7 3 6 3s6-1.3 6-3v-5M21 8v6",
  parent: "M8 8a3 3 0 100-6 3 3 0 000 6zM16 10a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM2 21v-2a5 5 0 015-5h2a5 5 0 015 5v2M14 21v-1.5a4 4 0 014-4h0a4 4 0 014 4V21",
  helper: "M7 11V7a5 5 0 0110 0v4M5 11h14v4a7 7 0 01-14 0v-4zM12 15v2",
  home: "M3 11l9-7 9 7M5 10v10h5v-6h4v6h5V10",
  bolt: "M13 2L4 14h7l-1 8 9-12h-7l1-8z",
  car: "M5 16h14M3 16v-4l2-5h14l2 5v4h-2M5 16H3M7.5 19a1.5 1.5 0 100-3 1.5 1.5 0 000 3zM16.5 19a1.5 1.5 0 100-3 1.5 1.5 0 000 3zM4 12h16",
  bike: "M5.5 18a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM18.5 18a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM5.5 14.5L9 8h5l4.5 6.5M12 14.5L9 8M14 8l1-3h3",
  heart: "M12 20s-7-4.4-9.2-9C1.4 7.9 3.4 4.5 6.8 4.5c2 0 3.4 1.1 5.2 3 1.8-1.9 3.2-3 5.2-3 3.4 0 5.4 3.4 4 6.5C19 15.6 12 20 12 20z",
  moon: "M20.5 14.5A8.5 8.5 0 019.5 3.5a8.5 8.5 0 1011 11z",
  sun: "M12 7a5 5 0 100 10 5 5 0 000-10zM12 1v3M12 20v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M1 12h3M20 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1",
  cpu: "M7 7h10v10H7zM10 10h4v4h-4zM9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3",
  gear: "M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z",
  rupee: "M6 4h12M6 9h12M6 4h3a5 5 0 010 10H6l8 7",
  shield: "M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3zM9 12l2 2 4-4",
  briefcase: "M3 8h18v12H3zM8 8V5a1 1 0 011-1h6a1 1 0 011 1v3M3 13h18",
  users: "M9 11a4 4 0 100-8 4 4 0 000 8zM2 21v-1a6 6 0 016-6h2a6 6 0 016 6v1M16 3.5a4 4 0 010 7.5M22 21v-1a6 6 0 00-4-5.6",
  wallet: "M3 7h16a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7zM3 7l12-4v4M17 13h.01",
  pin: "M12 21s-7-6.2-7-11.5a7 7 0 0114 0C19 14.8 12 21 12 21zM12 12a2.5 2.5 0 100-5 2.5 2.5 0 000 5z",
  route: "M6 19a2 2 0 100-4 2 2 0 000 4zM18 9a2 2 0 100-4 2 2 0 000 4zM6 15V9a4 4 0 014-4h6M18 9v6a4 4 0 01-4 4H8",
  graduation: "M2 9l10-5 10 5-10 5L2 9zM6 11v5c3 2.5 9 2.5 12 0v-5M22 9v6",
  help: "M12 21a9 9 0 100-18 9 9 0 000 18zM9.5 9a2.5 2.5 0 015 .5c0 1.7-2.5 2-2.5 3.5M12 17h.01",
  chat: "M4 5h16v11H8l-4 4V5zM8 10h8M8 13h5",
  phone: "M5 4h4l2 5-2.5 1.5a11 11 0 005 5L15 13l5 2v4a2 2 0 01-2 2A16 16 0 013 6a2 2 0 012-2z",
  check: "M4 12l5 5L20 6",
  arrowRight: "M5 12h14M13 6l6 6-6 6",
  arrowLeft: "M19 12H5M11 6l-6 6 6 6",
  sparkle: "M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6",
  download: "M12 4v11M7 10l5 5 5-5M4 20h16",
  share: "M18 8a3 3 0 100-6 3 3 0 000 6zM6 15a3 3 0 100-6 3 3 0 000 6zM18 22a3 3 0 100-6 3 3 0 000 6zM8.6 13.5l6.8 4M15.4 6.5l-6.8 4",
  refresh: "M20 11a8 8 0 10-2.3 5.7M20 4v7h-7",
  feather: "M20 4c-6 0-12 4-13 13l-3 3M7 17h7c3-2 5-6 6-13M10 13h6",
  clock: "M12 21a9 9 0 100-18 9 9 0 000 18zM12 7v5l3 2",
  send: "M4 12l16-8-6 16-2.5-6.5L4 12z",
  info: "M12 21a9 9 0 100-18 9 9 0 000 18zM12 11v6M12 7.5h.01",
  alert: "M12 3l10 18H2L12 3zM12 10v5M12 18h.01",
  hourglass: "M6 3h12M6 21h12M7 3c0 4 5 6 5 9s-5 5-5 9M17 3c0 4-5 6-5 9s5 5 5 9",
  ladder: "M7 3v18M17 3v18M7 7h10M7 12h10M7 17h10",
  building: "M4 21V5l8-3 8 3v16M9 21v-4h6v4M8 8h.01M12 8h.01M16 8h.01M8 12h.01M12 12h.01M16 12h.01",
  lock: "M6 11h12v10H6zM8 11V7a4 4 0 018 0v4",
  close: "M6 6l12 12M18 6L6 18",
  chart: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  search: "M11 4a7 7 0 100 14 7 7 0 000-14zM20 20l-4-4",
  question: "M9 9a3 3 0 115 2.2c-1 .7-2 1.3-2 2.8M12 18h.01",
  type: "M4 7V5h16v2M9 19h6M12 5v14",
  hand: "M8 13V5.5a1.5 1.5 0 013 0V12M11 11V4.5a1.5 1.5 0 013 0V12M14 11.5V6a1.5 1.5 0 013 0v7c0 4-2.5 8-7 8-3 0-4.5-1.5-6-4l-2-3.5a1.5 1.5 0 012.6-1.5L8 15",
};

export type IconName = keyof typeof PATHS | string;

export default function Icon({
  name, size = 24, className = "", strokeWidth = 1.8,
}: { name: IconName; size?: number; className?: string; strokeWidth?: number }) {
  const d = PATHS[name] ?? PATHS.star;
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round"
      className={className} aria-hidden="true" focusable="false"
    >
      <path d={d} />
    </svg>
  );
}

export const ICON_NAMES = Object.keys(PATHS);
