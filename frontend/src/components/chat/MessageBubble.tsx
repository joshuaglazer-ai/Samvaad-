import { useTranslation } from "react-i18next";
import { m } from "framer-motion";
import Icon from "../ui/Icon";
import ReadAloud from "../ui/ReadAloud";
import CardView from "../cards/CardView";
import { AVATAR } from "./SpeakerToggle";
import type { Card } from "../../lib/api";
import { useAppState, type Speaker } from "../../lib/state";

export interface ChatItem {
  id: string;
  role: "user" | "assistant" | "counsellor";
  speaker: string;
  text: string;
  cards: Card[];
}

interface Props {
  item: ChatItem;
  speaking: boolean;
  onSpeak: () => void;
  onStop: () => void;
}

export default function MessageBubble({ item, speaking, onSpeak, onStop }: Props) {
  const { t } = useTranslation();
  const { lite } = useAppState();
  const mine = item.role === "user";
  const av = AVATAR[(item.speaker as Speaker)] ?? AVATAR.parent;

  return (
    <m.li
      initial={lite ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex flex-col ${mine ? "items-end" : "items-start"}`}
    >
      <div className={`flex max-w-[92%] items-end gap-2 ${mine ? "flex-row-reverse" : ""}`}>
        <span
          className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${
            mine ? av.bg : item.role === "counsellor" ? "bg-success-600 text-white" : "bg-primary-600 text-white"
          }`}
          aria-hidden="true"
        >
          <Icon name={mine ? av.icon : item.role === "counsellor" ? "chat" : "star"} size={20} />
        </span>
        <div
          className={`rounded-[22px] px-4 py-3 text-[20px] leading-relaxed ${
            mine ? "rounded-br-md bg-primary-600 text-white" : "rounded-bl-md border border-lavender-200 bg-white/90 text-ink-900"
          } ${speaking ? "reading-highlight" : ""}`}
        >
          <p className={`mb-0.5 text-sm font-semibold ${mine ? "text-white/90" : "text-ink-600"}`}>
            {mine ? t(`chat.${item.speaker}`) : item.role === "counsellor" ? t("escalation.counsellorLabel") : "SAMVAAD"}
          </p>
          <p className="whitespace-pre-line">{item.text}</p>
          {!mine && (
            <div className="mt-2">
              <ReadAloud speaking={speaking} onSpeak={onSpeak} onStop={onStop} compact />
            </div>
          )}
        </div>
      </div>
      {item.cards.length > 0 && (
        <div className="mt-3 w-full space-y-3 sm:pl-11">
          {item.cards.map((c, i) => (
            <m.div key={i} initial={lite ? false : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 + i * 0.1 }}>
              <CardView card={c} />
            </m.div>
          ))}
        </div>
      )}
    </m.li>
  );
}
