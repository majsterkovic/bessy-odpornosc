export interface Meta { as_of: string; generated_at: string; version: number; notes: string[] }
export interface IndexRow { indeks: string; ticker: string; data: string; poziom: number | null; ath: number | null; data_ath: string | null; od_ath: number | null; r_3m: number | null; r_12m: number | null }
export interface FactorRow { okres: string; ropa: number | null; tech: number | null; wybory: string; czynniki: number | null; odleglosc: number | null }
export interface Market { summary: string; state_text: string; indices: IndexRow[]; factors: FactorRow[] }
export interface EpisodeRow { episode_id: string; peak_date: string; trough_date: string; depth: number | null; days_to_trough: number | null; days_to_recovery: number | null; kind: 'bessa' | 'korekta'; n_factors: number | null; oil_shock: boolean; tech_hot: boolean; midterm: boolean; in_ranking_a: boolean; twin: boolean }
export interface Episodes { rows: EpisodeRow[]; brief_text: string }
export interface SeasonRow { miesiac: string; mean_wybory: number | null; median_wybory: number | null; mean_inne: number | null; median_inne: number | null }
export interface AfterElection { year: number; election_date: string | null; r3m: number | null; r6m: number | null; r12m: number | null }
export interface Twins { text: string; seasonality_monthly: SeasonRow[]; after_election: AfterElection[]; after_election_text: string }
export interface SectorBehavior { sector: string; ticker: string; n_episodes: number; med_alpha: number | null; win_rate: number | null; med_ret: number | null; med_max_dd: number | null }
export interface SectorPe { sector: string; pe_teraz: number | null; med_5l: number | null; med_10l: number | null; perc_10l: number | null; vs_med_10l: number | null; pe_szczyt: number | null; pe_dolek: number | null; kompresja: number | null; pokrycie: number | null; ocena: string }
export interface Sectors { behavior_a: SectorBehavior[]; behavior_b: SectorBehavior[]; pe: SectorPe[]; pe_text: string }
export interface FunnelStep { key: string; label: string; n: number; note: string }
export interface PeReason { reason: string; n: number }
export interface Funnel { steps: FunnelStep[]; pe_rejected: PeReason[]; pe_passed: PeReason[] }
export interface Quintile { kwintyl: number; n: number; test_med_alpha: number | null; test_win: number | null; test_dd: number | null }
export interface Oos { n: number; spearman: number | null; kwintyle: Quintile[]; top_decile_alpha: number | null; all_alpha: number | null; top_decile_win: number | null; all_win: number | null }
export interface Sensitivity { overlap15: number; overlap30: number; ids7: string[]; both: string[]; only4: string[]; only7: string[] }
export interface Validation { text: string; oos: Oos; sensitivity: Sensitivity }
export interface ListRow {
  rank: number; instrument_id: number; ticker: string; name: string; sector: string | null; exchange: string | null; currency: string | null
  n_valid: number | null; n_bessy: number | null; med_alpha: number | null; downside_beta: number | null; med_max_dd: number | null
  win_rate: number | null; pe: number | null; pe_pct: number | null; note: string | null; alpha_sox: number | null; alpha_63d: number | null
  klass: string | null; corr_spx: number | null; ucits: string | null; why: string; per_episode: { episode_id: string; alpha: number }[]
}
export interface Lists { stocks_a: ListRow[]; stocks_b: ListRow[]; etf_a: ListRow[]; etf_b: ListRow[] }
export interface Series {
  sp500: [string, number][]; sox: [string, number][]
  twins: { episode_id: string; path: [number, number][] }[]
  today: { peak_date: string; path: [number, number][] }
}
export interface AllData {
  meta: Meta; market: Market; episodes: Episodes; twins: Twins; sectors: Sectors; funnel: Funnel
  validation: Validation; lists: Lists; series: Series
}
