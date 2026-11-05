import type { AllData, ListRow } from './types'

export const row = (o: Partial<ListRow> = {}): ListRow => ({
  rank: 1, instrument_id: 1, ticker: 'AAA.US', name: 'Alfa Corp', sector: 'Utilities', exchange: 'US', currency: 'USD', n_valid: 7, n_bessy: 3,
  med_alpha: 0.176, downside_beta: 0.2, med_max_dd: -0.058, win_rate: 1, pe: null, pe_pct: null, note: 'brak danych EPS',
  alpha_sox: null, alpha_63d: null, klass: null, corr_spx: null, ucits: null,
  why: 'pokonał S&P 500 w 7/7 okresach, mediana alfy +18 pp', per_episode: [{ episode_id: '2022-01-03', alpha: 0.2 }, { episode_id: '2018-09-20', alpha: 0.1 }], ...o,
})

export const sample: AllData = {
  meta: { as_of: '2026-10-26', generated_at: '2026-11-03 12:00', version: 1, notes: ['Dostępność w XTB sprawdź przed zakupem.'] },
  market: {
    summary: 'S&P 500 jest 1,8% poniżej szczytu.', state_text: 'Siła relatywna.',
    indices: [
      { indeks: 'S&P 500', ticker: 'GSPC.INDX', data: '2026-10-26', poziom: 7676.77, ath: 7818.9, data_ath: '2026-10-06', od_ath: -0.0182, r_3m: 0.0356, r_12m: 0.1303 },
      { indeks: 'Nasdaq 100', ticker: 'NDX.INDX', data: '2026-10-26', poziom: 29273, ath: 31224, data_ath: '2026-10-06', od_ath: -0.0625, r_3m: 0.044, r_12m: 0.154 },
      { indeks: 'Półprzewodniki (SOX)', ticker: 'SOX.INDX', data: '2026-10-26', poziom: 1, ath: 1, data_ath: '2026-06-22', od_ath: -0.24, r_3m: 0, r_12m: 0 },
      { indeks: 'WIG20', ticker: 'WIG20.INDX', data: '2026-10-26', poziom: 1, ath: 1, data_ath: '2026-10-01', od_ath: -0.016, r_3m: 0, r_12m: 0 },
      { indeks: 'Brent (indeks BCOMCO)', ticker: 'BCOMCO.INDX', data: '2026-10-26', poziom: 1014.9, ath: 1197, data_ath: '2008-07-03', od_ath: -0.152, r_3m: 0.438, r_12m: 1.238 },
      { indeks: 'VIX', ticker: 'VIX.INDX', data: '2026-10-26', poziom: 15, ath: 80, data_ath: '2008-11-20', od_ath: -0.8, r_3m: 0, r_12m: 0 },
    ],
    factors: [{ okres: 'dziś', ropa: 1.238, tech: 0.069, wybory: 'tak', czynniki: 2, odleglosc: null }],
  },
  episodes: {
    brief_text: 'Brak rozbieżności.',
    rows: [
      { episode_id: '1929-09-16', peak_date: '1929-09-16', trough_date: '1929-11-13', depth: -0.45, days_to_trough: 58, days_to_recovery: 9079, kind: 'bessa', n_factors: 0, oil_shock: false, tech_hot: false, midterm: false, in_ranking_a: false, twin: false },
      { episode_id: '1973-01-11', peak_date: '1973-01-11', trough_date: '1974-10-03', depth: -0.48, days_to_trough: 630, days_to_recovery: 2114, kind: 'bessa', n_factors: 2, oil_shock: true, tech_hot: false, midterm: true, in_ranking_a: true, twin: true },
      { episode_id: '2018-09-20', peak_date: '2018-09-20', trough_date: '2018-12-24', depth: -0.198, days_to_trough: 95, days_to_recovery: null, kind: 'korekta', n_factors: 2, oil_shock: true, tech_hot: false, midterm: true, in_ranking_a: true, twin: true },
    ],
  },
  twins: { text: '- **1973-01-11** (bessa)', seasonality_monthly: [{ miesiac: 'sty', mean_wybory: 0.01, median_wybory: 0.01, mean_inne: 0.02, median_inne: 0.02 }], after_election: [{ year: 2022, election_date: '2022-11-08', r3m: 0.1, r6m: 0.12, r12m: 0.15 }], after_election_text: 'Po wyborach.' },
  sectors: {
    behavior_a: [{ sector: 'Utilities', ticker: 'SPLRCU.INDX', n_episodes: 10, med_alpha: 0.12, win_rate: 1, med_ret: 0.0, med_max_dd: -0.1 }, { sector: 'Technology', ticker: 'SPLRCT.INDX', n_episodes: 10, med_alpha: -0.027, win_rate: 0.3, med_ret: -0.28, med_max_dd: -0.28 }],
    behavior_b: [{ sector: 'Utilities', ticker: 'SPLRCU.INDX', n_episodes: 3, med_alpha: 0.1, win_rate: 1, med_ret: 0, med_max_dd: -0.1 }, { sector: 'Technology', ticker: 'SPLRCT.INDX', n_episodes: 3, med_alpha: -0.038, win_rate: 0, med_ret: -0.23, med_max_dd: -0.24 }],
    pe: [{ sector: 'Utilities', pe_teraz: 19.5, med_5l: 20, med_10l: 18, perc_10l: 70, vs_med_10l: 0.08, pe_szczyt: 20, pe_dolek: 17, kompresja: -0.1, pokrycie: 0.9, ocena: 'tani' }, { sector: 'Communication Services', pe_teraz: 13.6, med_5l: 18, med_10l: 19, perc_10l: 17, vs_med_10l: -0.3, pe_szczyt: 19, pe_dolek: 15, kompresja: -0.17, pokrycie: 0.27, ocena: 'tani' }],
    pe_text: 'P/E sektorów USA.',
  },
  funnel: { steps: [{ key: 'kandydaci', label: 'Kupowalni kandydaci', n: 4778, note: 'giełdy XTB' }, { key: 'min4', label: 'Co najmniej 4 ważne okresy', n: 3425, note: '' }, { key: 'win70', label: 'Win ≥ 70%', n: 671, note: '' }, { key: 'top', label: 'Lista Top', n: 15, note: '' }], pe_rejected: [{ reason: 'ujemny zysk (EPS)', n: 3 }, { reason: 'P/E powyżej własnego 80. percentyla', n: 5 }], pe_passed: [{ reason: 'przeszło bez uwag', n: 100 }] },
  validation: {
    text: '**Test poza próbą.**',
    oos: { n: 2310, spearman: 0.48, kwintyle: [{ kwintyl: 1, n: 462, test_med_alpha: -0.0676, test_win: 0.32, test_dd: -0.36 }, { kwintyl: 5, n: 462, test_med_alpha: 0.074, test_win: 0.69, test_dd: -0.2 }], top_decile_alpha: 0.08, all_alpha: 0, top_decile_win: 0.74, all_win: 0.48 },
    sensitivity: { overlap15: 8, overlap30: 16, ids7: ['a', 'b', 'c', 'd', 'e', 'f', 'g'], both: ['BEKN.SW', 'CHT.US'], only4: [], only7: [] },
  },
  lists: { stocks_a: [row(), row({ rank: 2, instrument_id: 2, ticker: 'BBB.SW', name: 'Beta Bank', pe: 18, note: null })], stocks_b: [row({ alpha_sox: 0.1, alpha_63d: 0.02 })], etf_a: [row({ instrument_id: 3, ticker: 'ACWV.US', name: 'Min Vol', klass: 'akcje', corr_spx: 0.63, ucits: 'IQQ0.XETRA (0.92)', note: null })], etf_b: [row({ instrument_id: 4, ticker: 'XYZ.US', name: 'Nic', klass: 'obligacje i inne', ucits: null, note: null })] },
  series: { sp500: [['1929-09-20', 31.9], ['2026-10-23', 7676]], sox: [['1994-05-06', 100], ['2026-10-23', 9000]], twins: [{ episode_id: '1973-01-11', path: [[0, 100], [400, 70]] }], today: { peak_date: '2026-10-06', path: [[0, 100], [20, 98.2]] } },
}
