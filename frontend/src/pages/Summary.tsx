import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import QRCode from "qrcode";
import Button from "../components/ui/Button";
import Icon from "../components/ui/Icon";
import CardView from "../components/cards/CardView";
import { AlignmentMessage } from "./Alignment";
import { CONCERN_ICONS } from "./Onboarding";
import { api, type SummaryData } from "../lib/api";
import { useAppState } from "../lib/state";

/** One-page Family Summary Card in the session language. No personal data: no names, no phone. */
export default function Summary() {
  const { sessionId: param } = useParams();
  const { sessionId: current, reset, profile } = useAppState();
  const id = param ?? current;
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [data, setData] = useState<SummaryData | null>(null);
  const [qr, setQr] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const url = id ? `${window.location.origin}/summary/${id}` : "";

  useEffect(() => {
    if (!id) {
      navigate("/");
      return;
    }
    api.summary(id).then((s) => {
      setData(s);
      if (s.language !== i18n.language) i18n.changeLanguage(s.language);
    }).catch(() => setError(t("app.error")));
    QRCode.toDataURL(url, { margin: 1, width: 160, color: { dark: "#241B4B", light: "#FFFFFF" } }).then(setQr).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const download = async () => {
    if (!cardRef.current) return;
    const { toPng } = await import("html-to-image");
    const dataUrl = await toPng(cardRef.current, { pixelRatio: 2, backgroundColor: getComputedStyle(document.body).backgroundColor || "#F8F5FF", filter: (n) => !(n as HTMLElement).dataset?.noexport });
    const a = document.createElement("a");
    a.href = dataUrl;
    a.download = "samvaad-family-summary.png";
    a.click();
    api.event({ session_id: id, event_type: "summary_downloaded" }).catch(() => undefined);
  };

  const share = async () => {
    api.event({ session_id: id, event_type: "summary_shared" }).catch(() => undefined);
    const nav = navigator as Navigator & { share?: (d: ShareData) => Promise<void> };
    if (nav.share) {
      try {
        await nav.share({ title: `SAMVAAD — ${t("summary.title")}`, text: t("summary.closing"), url });
        return;
      } catch {
        /* user cancelled; fall through to copy */
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      /* clipboard blocked */
    }
  };

  if (error) return <p role="alert" className="glass mt-4 p-5 text-danger-600">{error}</p>;
  if (!data) return <p className="p-8 text-center text-ink-600" role="status">{t("app.loading")}</p>;

  return (
    <section className="mt-2 space-y-4">
      <div ref={cardRef} className="glass space-y-5 bg-white/90 p-5">
        <header className="flex items-start justify-between gap-3">
          <div>
            <p className="flex items-center gap-1.5 text-sm font-bold tracking-widest text-primary-700">
              <Icon name="star" size={18} className="text-star-400" /> SAMVAAD
            </p>
            <h1 className="text-2xl font-bold text-ink-900">{t("summary.title")}</h1>
            <p className="text-ink-600">{t(`districts.${data.district}`, data.district)}</p>
          </div>
          {qr && (
            <figure className="text-center">
              <img src={qr} alt={t("summary.scan")} width={104} height={104} className="rounded-xl border border-lavender-200" />
              <figcaption className="mt-1 max-w-[110px] text-xs text-ink-600">{t("summary.scan")}</figcaption>
            </figure>
          )}
        </header>

        {data.has_demo_data && (
          <p className="flex items-center gap-2 rounded-xl bg-info-600 px-3 py-2 font-semibold text-white">
            <Icon name="info" size={18} /> {t("app.demoLabel")}
          </p>
        )}

        {profile.participation_mode === "learner_only" && (
          <p data-noexport="1" className="flex items-start gap-2 rounded-xl bg-lavender-100 px-3 py-2 text-ink-900">
            <Icon name="share" className="mt-0.5 shrink-0 text-primary-700" /> {t("family.learnerOnlyNote")}
          </p>
        )}

        {data.alignment?.complete && (
          <div className="rounded-2xl bg-lavender-100 p-4"><AlignmentMessage result={data.alignment} /></div>
        )}

        <div>
          <h2 className="mb-2 text-lg font-bold text-ink-900">{t("summary.options")}</h2>
          {data.trades_discussed.length ? (
            <ul className="flex flex-wrap gap-2">
              {data.trades_discussed.map((tr) => (
                <li key={tr.slug} className="flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 font-semibold text-ink-900 ring-1 ring-lavender-200">
                  <Icon name="briefcase" size={18} className="text-primary-700" /> {tr.name}
                </li>
              ))}
            </ul>
          ) : <p className="text-ink-600">{t("summary.nothingYet")}</p>}
          {data.concerns.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-2">
              {data.concerns.map((c) => (
                <li key={c} className="flex items-center gap-1.5 rounded-full bg-lavender-100 px-3 py-1 text-sm text-ink-900">
                  <Icon name={CONCERN_ICONS[c] ?? "help"} size={16} /> {t(`concerns.${c}`)}
                </li>
              ))}
            </ul>
          )}
        </div>

        {data.figures.length > 0 && (
          <div>
            <h2 className="mb-2 text-lg font-bold text-ink-900">{t("summary.figures")}</h2>
            <div className="space-y-3">{data.figures.map((c, i) => <CardView key={i} card={c} />)}</div>
          </div>
        )}

        {data.ladder && (
          <div>
            <h2 className="mb-2 text-lg font-bold text-ink-900">{t("summary.ladder")}</h2>
            <CardView card={data.ladder} />
          </div>
        )}

        <div>
          <h2 className="mb-2 text-lg font-bold text-ink-900">{t("summary.openQuestions")}</h2>
          <ul className="space-y-1.5 text-lg text-ink-900">
            {["q1", "q2", "q3"].map((q) => (
              <li key={q} className="flex items-start gap-2"><Icon name="question" className="mt-1 shrink-0 text-primary-700" /> {t(`summary.${q}`)}</li>
            ))}
          </ul>
        </div>

        <footer className="border-t border-lavender-200 pt-3 text-base font-semibold text-ink-900">
          {t("summary.closing")}
        </footer>
      </div>

      <div className="flex flex-wrap gap-3">
        <Button icon="download" onClick={download}>{t("summary.download")}</Button>
        <Button icon="share" variant="secondary" onClick={share}>{copied ? "✓" : t("summary.share")}</Button>
        <Button icon="refresh" variant="ghost" onClick={() => { reset(); navigate("/"); }}>{t("summary.newSession")}</Button>
      </div>
    </section>
  );
}
