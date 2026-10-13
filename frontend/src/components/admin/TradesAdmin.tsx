import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Button from "../ui/Button";
import Icon from "../ui/Icon";
import { StatusBadge } from "../cards/EvidenceBadge";
import { api, type DataStatus, type LangText } from "../../lib/api";

// Admin → Trades (Update 3): everything families browse comes from here, in four languages, without code changes.
type Lang = "en" | "kn" | "hi" | "te";
const LANGS: Lang[] = ["en", "kn", "hi", "te"];
const LANG_LABEL: Record<Lang, string> = { en: "English", kn: "ಕನ್ನಡ", hi: "हिन्दी", te: "తెలుగు" };
const TRAITS = ["hands", "people", "machines", "outdoors", "computers"];
const STATUSES: DataStatus[] = ["unavailable", "demo", "historical", "verified"];
const STEP_KINDS = ["job", "upskill", "apprenticeship", "diploma", "degree"];
const ICONS = ["bolt", "car", "bike", "heart", "sun", "gear", "cpu", "building", "hand", "users", "home", "graduation", "briefcase"];

interface Synonym { id: number; language: Lang; term: string; review_status: "needs_native_review" | "reviewed" }
interface Step { kind: string; titles: LangText; nsqf_level: number | null; entry_min_education: string; entry_requirement: LangText; duration_months: number | null }
interface AdminTrade {
  slug: string; sector: string; names: LangText; nsqf_level: number; duration_months: number; entry_min_education: string;
  entry_requirement: LangText; job_roles: Partial<Record<Lang, string[]>>; icon: string; traits: string[];
  data_status: DataStatus; source_id: number | null; missing_languages: Lang[]; outcomes_by_status: Record<string, number>;
  synonyms: Synonym[]; steps: Step[];
}
interface AdminSector { slug: string; names: LangText; icon: string; sort_order: number }
interface Catalogue {
  sectors: AdminSector[]; trades: AdminTrade[]; education_levels: string[];
  sources: { id: number; title: string; reporting_period: string | null }[];
}

const input = "mt-1 block min-h-11 w-full rounded-xl border border-lavender-200 bg-white px-3 text-base text-ink-900";
const label = "block text-sm font-semibold text-ink-900";

function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

function LangFields({ legend, value, onChange, idPrefix }: { legend: string; value: LangText; onChange: (v: LangText) => void; idPrefix: string }) {
  return (
    <fieldset className="grid gap-2 sm:grid-cols-2">
      <legend className="mb-1 text-sm font-semibold text-ink-900">{legend}</legend>
      {LANGS.map((l) => (
        <label key={l} className={label} htmlFor={`${idPrefix}-${l}`}>
          {LANG_LABEL[l]}{l === "en" && " *"}
          <input id={`${idPrefix}-${l}`} lang={l} className={input} value={value[l] ?? ""}
            onChange={(e) => onChange({ ...value, [l]: e.target.value })} />
        </label>
      ))}
    </fieldset>
  );
}

const emptyTrade = (sector: string): AdminTrade => ({
  slug: "", sector, names: {}, nsqf_level: 3, duration_months: 6, entry_min_education: "class_10", entry_requirement: {},
  job_roles: {}, icon: "gear", traits: [], data_status: "unavailable", source_id: null, missing_languages: [],
  outcomes_by_status: {}, synonyms: [], steps: [],
});

export default function TradesAdmin({ pin }: { pin: string }) {
  const { t } = useTranslation();
  const [cat, setCat] = useState<Catalogue | null>(null);
  const [editing, setEditing] = useState<{ trade: AdminTrade; isNew: boolean } | null>(null);
  const [sectorDraft, setSectorDraft] = useState<{ sector: AdminSector; isNew: boolean } | null>(null);
  const [newWord, setNewWord] = useState<{ language: Lang; term: string }>({ language: "en", term: "" });
  const [steps, setSteps] = useState<Step[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    const c = await api.admin.get<Catalogue>(pin, "catalogue");
    setCat(c);
    return c;
  }, [pin]);
  useEffect(() => {
    load().catch((e) => setErr(errorText(e)));
  }, [load]);

  const open = (tr: AdminTrade, isNew = false) => {
    setEditing({ trade: structuredClone(tr), isNew });
    setSteps(structuredClone(tr.steps));
    setMsg(null);
    setErr(null);
  };
  const refresh = async (slug: string) => {
    const c = await load();
    const fresh = c.trades.find((x) => x.slug === slug);
    if (fresh) open(fresh);
  };
  const run = async (fn: () => Promise<unknown>, after?: () => Promise<void>) => {
    setErr(null);
    setMsg(null);
    try {
      await fn();
      if (after) await after();
      setMsg(t("adminTrades.saved"));
    } catch (e) {
      setErr(errorText(e));
    }
  };

  if (!cat) return <p className="p-6 text-center text-ink-600" role="status">{err ?? t("app.loading")}</p>;
  const sectorName = (slug: string) => cat.sectors.find((s) => s.slug === slug)?.names.en ?? slug;
  const tr = editing?.trade;
  const setTr = (patch: Partial<AdminTrade>) => editing && setEditing({ ...editing, trade: { ...editing.trade, ...patch } });

  const saveTrade = () => tr && run(async () => {
    const body = {
      slug: tr.slug, sector: tr.sector, names: tr.names, nsqf_level: Number(tr.nsqf_level), duration_months: Number(tr.duration_months),
      entry_min_education: tr.entry_min_education, entry_requirement: tr.entry_requirement, job_roles: tr.job_roles,
      icon: tr.icon, traits: tr.traits, data_status: tr.data_status, source_id: tr.source_id,
    };
    if (editing!.isNew) await api.admin.send(pin, "POST", "trades", body);
    else await api.admin.send(pin, "PUT", `trades/${tr.slug}`, body);
  }, () => refresh(tr.slug));

  return (
    <section className="space-y-4" data-testid="trades-admin">
      <div className="glass p-4">
        <h2 className="flex items-center gap-2 text-xl font-bold text-ink-900"><Icon name="gear" className="text-primary-700" />{t("adminTrades.title")}</h2>
        <p className="mt-1 text-ink-600">{t("adminTrades.intro")}</p>
        <p className="mt-1 font-mono text-xs text-ink-600">{t("adminTrades.importHint")}</p>
      </div>

      {msg && <p role="status" className="rounded-xl bg-success-600/10 px-3 py-2 font-semibold text-success-600">{msg}</p>}
      {err && <p role="alert" className="rounded-xl bg-danger-600/10 px-3 py-2 text-danger-600">{err}</p>}

      {/* Sectors */}
      <section className="glass p-4" aria-labelledby="sectors-h">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 id="sectors-h" className="text-lg font-bold text-ink-900">{t("adminTrades.sectors")}</h3>
          <Button variant="secondary" icon="sparkle" onClick={() => setSectorDraft({ sector: { slug: "", names: {}, icon: "gear", sort_order: cat.sectors.length + 1 }, isNew: true })}>
            {t("adminTrades.addSector")}
          </Button>
        </div>
        <ul className="mt-2 flex flex-wrap gap-2">
          {cat.sectors.map((s) => (
            <li key={s.slug}>
              <button type="button" onClick={() => setSectorDraft({ sector: structuredClone(s), isNew: false })}
                className="flex min-h-11 items-center gap-2 rounded-full border border-lavender-200 bg-white px-3 text-ink-900">
                <Icon name={s.icon} size={18} className="text-primary-700" />{s.names.en}
                <span className="text-xs text-ink-600">({cat.trades.filter((x) => x.sector === s.slug).length})</span>
              </button>
            </li>
          ))}
        </ul>
        {sectorDraft && (
          <form className="mt-3 space-y-3 rounded-2xl bg-white/80 p-3" onSubmit={(e) => {
            e.preventDefault();
            const sd = sectorDraft;
            run(() => sd.isNew ? api.admin.send(pin, "POST", "sectors", sd.sector) : api.admin.send(pin, "PUT", `sectors/${sd.sector.slug}`, sd.sector),
              async () => { await load(); setSectorDraft(null); });
          }}>
            {sectorDraft.isNew && (
              <label className={label}>{t("adminTrades.slug")}
                <input className={input} required pattern="[a-z0-9]+(-[a-z0-9]+)*" value={sectorDraft.sector.slug}
                  onChange={(e) => setSectorDraft({ ...sectorDraft, sector: { ...sectorDraft.sector, slug: e.target.value } })} />
              </label>
            )}
            <LangFields legend={t("adminTrades.names")} idPrefix="sector-name" value={sectorDraft.sector.names}
              onChange={(names) => setSectorDraft({ ...sectorDraft, sector: { ...sectorDraft.sector, names } })} />
            <div className="grid gap-2 sm:grid-cols-2">
              <label className={label}>{t("adminTrades.icon")}
                <select className={input} value={sectorDraft.sector.icon} onChange={(e) => setSectorDraft({ ...sectorDraft, sector: { ...sectorDraft.sector, icon: e.target.value } })}>
                  {ICONS.map((i) => <option key={i} value={i}>{i}</option>)}
                </select>
              </label>
              <label className={label}>{t("adminTrades.order")}
                <input type="number" min={0} max={999} className={input} value={sectorDraft.sector.sort_order}
                  onChange={(e) => setSectorDraft({ ...sectorDraft, sector: { ...sectorDraft.sector, sort_order: Number(e.target.value) } })} />
              </label>
            </div>
            <div className="flex gap-2">
              <Button type="submit" icon="check">{t("adminTrades.save")}</Button>
              <Button variant="ghost" onClick={() => setSectorDraft(null)}>{t("adminTrades.cancel")}</Button>
            </div>
          </form>
        )}
      </section>

      {/* Trades list */}
      <section className="glass p-4" aria-labelledby="trades-h">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 id="trades-h" className="text-lg font-bold text-ink-900">{t("admin.tabTrades")} ({cat.trades.length})</h3>
          <Button icon="sparkle" onClick={() => open(emptyTrade(cat.sectors[0]?.slug ?? ""), true)}>{t("adminTrades.addTrade")}</Button>
        </div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm text-ink-900">
            <thead>
              <tr className="border-b border-lavender-200">
                {["Trade", t("adminTrades.sector"), t("adminTrades.status"), t("adminTrades.synonyms"), t("adminTrades.missingLangs"), ""].map((h, i) => (
                  <th key={i} scope="col" className="px-2 py-1.5 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cat.trades.map((x) => (
                <tr key={x.slug} className={`border-b border-lavender-100 ${tr?.slug === x.slug ? "bg-lavender-100" : ""}`}>
                  <td className="px-2 py-1.5 font-semibold">{x.names.en}<span className="block text-xs font-normal text-ink-600">{x.slug}</span></td>
                  <td className="px-2 py-1.5">{sectorName(x.sector)}</td>
                  <td className="px-2 py-1.5"><StatusBadge status={x.data_status} /></td>
                  <td className="px-2 py-1.5 tabular-nums">{x.synonyms.length}</td>
                  <td className="px-2 py-1.5">{x.missing_languages.map((l) => LANG_LABEL[l]).join(", ") || "—"}</td>
                  <td className="px-2 py-1.5"><Button variant="ghost" icon="feather" onClick={() => open(x)}>{t("adminTrades.edit")}</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Trade editor */}
      {tr && editing && (
        <section className="glass space-y-4 p-4" aria-labelledby="trade-editor-h" data-testid="trade-editor">
          <h3 id="trade-editor-h" className="text-lg font-bold text-ink-900">
            {editing.isNew ? t("adminTrades.addTrade") : `${t("adminTrades.edit")}: ${tr.names.en}`}
          </h3>
          <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); saveTrade(); }}>
            {editing.isNew && (
              <label className={label}>{t("adminTrades.slug")}
                <input className={input} required pattern="[a-z0-9]+(-[a-z0-9]+)*" value={tr.slug} onChange={(e) => setTr({ slug: e.target.value })} />
              </label>
            )}
            <LangFields legend={t("adminTrades.names")} idPrefix="trade-name" value={tr.names} onChange={(names) => setTr({ names })} />
            <div className="grid gap-2 sm:grid-cols-3">
              <label className={label}>{t("adminTrades.sector")}
                <select className={input} value={tr.sector} onChange={(e) => setTr({ sector: e.target.value })}>
                  {cat.sectors.map((s) => <option key={s.slug} value={s.slug}>{s.names.en}</option>)}
                </select>
              </label>
              <label className={label}>{t("adminTrades.nsqf")}
                <input type="number" min={1} max={10} className={input} value={tr.nsqf_level} onChange={(e) => setTr({ nsqf_level: Number(e.target.value) })} />
              </label>
              <label className={label}>{t("adminTrades.months")}
                <input type="number" min={1} max={60} className={input} value={tr.duration_months} onChange={(e) => setTr({ duration_months: Number(e.target.value) })} />
              </label>
              <label className={label}>{t("adminTrades.minEducation")}
                <select className={input} value={tr.entry_min_education} onChange={(e) => setTr({ entry_min_education: e.target.value })}>
                  {cat.education_levels.map((l) => <option key={l} value={l}>{t(`education.${l}`, l)}</option>)}
                </select>
              </label>
              <label className={label}>{t("adminTrades.icon")}
                <select className={input} value={tr.icon} onChange={(e) => setTr({ icon: e.target.value })}>
                  {ICONS.map((i) => <option key={i} value={i}>{i}</option>)}
                </select>
              </label>
            </div>
            <fieldset>
              <legend className="text-sm font-semibold text-ink-900">{t("adminTrades.traits")}</legend>
              <div className="mt-1 flex flex-wrap gap-3">
                {TRAITS.map((x) => (
                  <label key={x} className="flex min-h-11 items-center gap-2 text-ink-900">
                    <input type="checkbox" checked={tr.traits.includes(x)} className="h-5 w-5"
                      onChange={(e) => setTr({ traits: e.target.checked ? [...tr.traits, x] : tr.traits.filter((y) => y !== x) })} />
                    {x}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="grid gap-2 sm:grid-cols-2">
              <label className={label}>{t("adminTrades.status")}
                <select className={input} value={tr.data_status} onChange={(e) => setTr({ data_status: e.target.value as DataStatus })}>
                  {STATUSES.map((s) => <option key={s} value={s} disabled={(s === "verified" || s === "historical") && !tr.source_id}>{s}</option>)}
                </select>
              </label>
              <label className={label}>{t("adminTrades.source")}
                <select className={input} value={tr.source_id ?? ""} onChange={(e) => setTr({ source_id: e.target.value ? Number(e.target.value) : null })}>
                  <option value="">{t("adminTrades.noSource")}</option>
                  {cat.sources.map((s) => <option key={s.id} value={s.id}>{s.title}{s.reporting_period ? ` (${s.reporting_period})` : ""}</option>)}
                </select>
              </label>
            </div>
            {!tr.source_id && <p className="text-sm text-ink-600">{t("adminTrades.needSource")}</p>}
            {!editing.isNew && (
              <p className="flex flex-wrap items-center gap-2 text-sm text-ink-900">
                {t("adminTrades.outcomes")}:
                {Object.entries(tr.outcomes_by_status).map(([s, n]) => <span key={s} className="flex items-center gap-1"><StatusBadge status={s as DataStatus} /> {n}</span>)}
                {Object.keys(tr.outcomes_by_status).length === 0 && "—"}
              </p>
            )}
            <div className="flex gap-2">
              <Button type="submit" icon="check">{t("adminTrades.save")}</Button>
              <Button variant="ghost" onClick={() => setEditing(null)}>{t("adminTrades.cancel")}</Button>
            </div>
          </form>

          {!editing.isNew && (
            <>
              {/* Everyday words */}
              <section aria-labelledby="syn-h" className="rounded-2xl bg-white/80 p-3">
                <h4 id="syn-h" className="font-bold text-ink-900">{t("adminTrades.synonyms")} ({tr.synonyms.length})</h4>
                <ul className="mt-2 space-y-1">
                  {tr.synonyms.map((s) => (
                    <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-lavender-100 py-1">
                      <span className="text-ink-900" lang={s.language}><span className="text-xs text-ink-600">{LANG_LABEL[s.language]} · </span>{s.term}</span>
                      <span className="flex items-center gap-1">
                        {s.review_status === "reviewed"
                          ? <span className="flex items-center gap-1 text-sm text-success-600"><Icon name="check" size={16} />{t("adminTrades.reviewed")}</span>
                          : <Button variant="ghost" onClick={() => run(() => api.admin.send(pin, "PUT", `synonyms/${s.id}`, { ...s, review_status: "reviewed" }), () => refresh(tr.slug))}>
                              {t("adminTrades.markReviewed")}
                            </Button>}
                        <Button variant="ghost" icon="close" onClick={() => run(() => api.admin.send(pin, "DELETE", `synonyms/${s.id}`), () => refresh(tr.slug))}>
                          {t("adminTrades.remove")}
                        </Button>
                      </span>
                    </li>
                  ))}
                </ul>
                <form className="mt-2 flex flex-wrap items-end gap-2" onSubmit={(e) => {
                  e.preventDefault();
                  run(() => api.admin.send(pin, "POST", `trades/${tr.slug}/synonyms`, newWord),
                    async () => { setNewWord({ ...newWord, term: "" }); await refresh(tr.slug); });
                }}>
                  <label className={label}>{t("adminTrades.language")}
                    <select className={input} value={newWord.language} onChange={(e) => setNewWord({ ...newWord, language: e.target.value as Lang })}>
                      {LANGS.map((l) => <option key={l} value={l}>{LANG_LABEL[l]}</option>)}
                    </select>
                  </label>
                  <label className={`${label} min-w-48 flex-1`}>{t("adminTrades.word")}
                    <input className={input} required maxLength={120} value={newWord.term} onChange={(e) => setNewWord({ ...newWord, term: e.target.value })} />
                  </label>
                  <Button type="submit" icon="sparkle">{t("adminTrades.addWord")}</Button>
                </form>
              </section>

              {/* Career steps */}
              <section aria-labelledby="steps-h" className="rounded-2xl bg-white/80 p-3">
                <h4 id="steps-h" className="font-bold text-ink-900">{t("adminTrades.steps")}</h4>
                <ol className="mt-2 space-y-3">
                  {steps.map((s, i) => (
                    <li key={i} className="space-y-2 border-b border-lavender-100 pb-3">
                      <div className="flex flex-wrap items-end gap-2">
                        <span className="font-semibold tabular-nums text-ink-900">{i + 1}.</span>
                        <label className={label}>{t("adminTrades.kind")}
                          <select className={input} value={s.kind} onChange={(e) => setSteps(steps.map((x, j) => j === i ? { ...x, kind: e.target.value } : x))}>
                            {STEP_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
                          </select>
                        </label>
                        <label className={label}>{t("adminTrades.nsqf")}
                          <input type="number" min={1} max={10} className={input} value={s.nsqf_level ?? ""}
                            onChange={(e) => setSteps(steps.map((x, j) => j === i ? { ...x, nsqf_level: e.target.value ? Number(e.target.value) : null } : x))} />
                        </label>
                        <Button variant="ghost" icon="close" onClick={() => setSteps(steps.filter((_, j) => j !== i))}>{t("adminTrades.remove")}</Button>
                      </div>
                      <LangFields legend={t("adminTrades.stepTitle")} idPrefix={`step-${i}`} value={s.titles}
                        onChange={(titles) => setSteps(steps.map((x, j) => j === i ? { ...x, titles } : x))} />
                    </li>
                  ))}
                </ol>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button variant="secondary" icon="sparkle" onClick={() => setSteps([...steps, { kind: "job", titles: {}, nsqf_level: null, entry_min_education: tr.entry_min_education, entry_requirement: {}, duration_months: null }])}>
                    {t("adminTrades.addStep")}
                  </Button>
                  <Button icon="check" onClick={() => run(() => api.admin.send(pin, "PUT", `trades/${tr.slug}/steps`, steps), () => refresh(tr.slug))}>
                    {t("adminTrades.saveSteps")}
                  </Button>
                </div>
              </section>
            </>
          )}
        </section>
      )}
    </section>
  );
}
