import { useMemo, useState } from 'react'
import { RowDetail } from '../lists/RowDetail'
import { ListTable } from '../lists/ListTable'
import { filterRows } from '../lists/listLogic'
import type { Lists } from '../types'

const TABS = [
  { id: 'stocks_a', label: 'Spółki: na każdą bessę', etf: false },
  { id: 'stocks_b', label: 'Spółki: obecny układ', etf: false },
  { id: 'etf_a', label: 'ETF: na każdą bessę', etf: true },
  { id: 'etf_b', label: 'ETF: obecny układ', etf: true },
] as const
type TabId = (typeof TABS)[number]['id']

export function StepLists({ lists }: { lists: Lists }) {
  const [tab, setTab] = useState<TabId>('stocks_a')
  const [query, setQuery] = useState('')
  const [klass, setKlass] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const cur = TABS.find((t) => t.id === tab)!
  const all = lists[tab]
  const klasses = useMemo(() => [...new Set(all.map((r) => r.klass).filter((k): k is string => !!k))], [all])
  const rows = filterRows(all, { query, klass })
  const sel = rows.find((r) => r.ticker === selected) ?? null
  return (
    <>
      <div role="tablist" aria-label="Listy" className="tabs">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={t.id === tab} onClick={() => { setTab(t.id); setSelected(null); setKlass(null) }}>{t.label}</button>
        ))}
      </div>
      <div className="filters">
        <input type="search" role="searchbox" placeholder="Szukaj po tickerze lub nazwie" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Szukaj" />
        {cur.etf && (
          <select value={klass ?? ''} onChange={(e) => setKlass(e.target.value || null)} aria-label="Klasa ETF">
            <option value="">wszystkie klasy</option>
            {klasses.map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
        )}
      </div>
      <ListTable key={tab} rows={rows} etf={cur.etf} trend={tab === 'stocks_b' || tab === 'etf_b'} selected={selected} onSelect={setSelected} />
      {sel && <RowDetail row={sel} onClose={() => setSelected(null)} />}
    </>
  )
}
