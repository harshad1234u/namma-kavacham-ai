import { useEffect, useState } from "react";
import { ErrorBox, Loading, PageTitle, card } from "../components/civic/ui";
import { str, useCivic } from "../i18n/civic";
import { getJson } from "../services/civicApi";
import type { LanguageInfo } from "../types/civic";

export function Languages() {
  const { c } = useCivic();
  const [langs, setLangs] = useState<LanguageInfo[] | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState(false);
  useEffect(() => {
    getJson<{ note: string; languages: LanguageInfo[] }>("/v1/meta/languages")
      .then((r) => { setLangs(r.languages); setNote(r.note); })
      .catch(() => setError(true));
  }, []);
  const sup = (s: string) => str(c, `sup_${s}`);
  return (
    <div className="space-y-4">
      <PageTitle title={c.languagesTitle} subtitle={c.languagesBody} />
      {error && <ErrorBox message={c.errorGeneric} />}
      {!langs && !error && <Loading />}
      {langs && (
        <div className={`${card} overflow-x-auto`}>
          <table className="w-full min-w-[36rem] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-navy-soft">
                <th scope="col" className="py-2 pr-3">{c.languageLabel}</th>
                <th scope="col" className="py-2 pr-3">{c.cap_ui}</th>
                <th scope="col" className="py-2 pr-3">{c.cap_query}</th>
                <th scope="col" className="py-2">{c.cap_kb}</th>
              </tr>
            </thead>
            <tbody>
              {langs.map((l) => (
                <tr key={l.code} className="border-b border-line last:border-0">
                  <td className="py-2 pr-3"><span lang={l.code} dir={l.dir} className="font-semibold">{l.native_name}</span> <span className="text-ink-muted">· {l.name}</span></td>
                  <td className="py-2 pr-3">{sup(l.support.ui)}</td>
                  <td className="py-2 pr-3">{sup(l.support.query_understanding)}</td>
                  <td className="py-2">{sup(l.support.kb_text)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-ink-muted">{note}</p>
        </div>
      )}
    </div>
  );
}
