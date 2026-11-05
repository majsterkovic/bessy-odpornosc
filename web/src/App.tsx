import { useEffect, useState } from 'react'
import { Shell } from './components/Shell'
import { leadWhere, StepWhere } from './steps/StepWhere'
import { StepEpisodes } from './steps/StepEpisodes'
import { leadFunnel, StepFunnel } from './steps/StepFunnel'
import { StepLists } from './steps/StepLists'
import { StepSectors } from './steps/StepSectors'
import { leadValidation, StepValidation } from './steps/StepValidation'
import { leadTwins, StepTwins } from './steps/StepTwins'
import { ErrorBoundary } from './components/ErrorBoundary'
import { DataError, loadAll } from './data'
import type { AllData } from './types'

type State = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; data: AllData }

export default function App({ loader = () => loadAll() }: { loader?: () => Promise<AllData> }) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  useEffect(() => {
    loader().then(
      (data) => setState({ kind: 'ready', data }),
      (e: unknown) => setState({ kind: 'error', message: e instanceof DataError ? e.message : `Nie udało się załadować danych: ${String(e)}` }),
    )
  }, [loader])
  if (state.kind === 'loading') return <p className="status">Ładowanie danych…</p>
  if (state.kind === 'error') return <p role="alert" className="status error">{state.message}</p>
  return <ErrorBoundary><Shell meta={state.data.meta} bodies={{
    gdzie: { lead: leadWhere(state.data.market), body: <StepWhere market={state.data.market} series={state.data.series} /> },
    bessy: { lead: 'Zygzak na S&P 500: szczyt potwierdza spadek o 15%, dołek wzrost o 30% albo powrót na szczyt.', body: <StepEpisodes episodes={state.data.episodes} series={state.data.series} /> },
    blizniaki: { lead: leadTwins(state.data.series.twins.length), body: <StepTwins twins={state.data.twins} market={state.data.market} series={state.data.series} /> },
    sektory: { lead: 'Które sektory broniły się w bessach i które są dziś drogie lub tanie.', body: <StepSectors sectors={state.data.sectors} /> },
    lejek: { lead: leadFunnel(state.data.funnel), body: <StepFunnel funnel={state.data.funnel} /> },
    walidacja: { lead: leadValidation(state.data.validation), body: <StepValidation validation={state.data.validation} /> },
    listy: { lead: 'Kandydaci do sprawdzenia, nie rekomendacja. Kliknij ticker, aby zobaczyć alfę w każdym okresie.', body: <StepLists lists={state.data.lists} /> },
  }} /></ErrorBoundary>
}
