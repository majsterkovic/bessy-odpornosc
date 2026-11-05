export const STEPS = [
  { id: 'gdzie', title: 'Gdzie jesteśmy' },
  { id: 'bessy', title: 'Wszystkie bessy od 1929' },
  { id: 'blizniaki', title: 'Bliźniacze bessy' },
  { id: 'sektory', title: 'Sektory i P/E' },
  { id: 'lejek', title: 'Lejek selekcji' },
  { id: 'walidacja', title: 'Czy metoda działa' },
  { id: 'listy', title: 'Listy Top' },
] as const
export type StepId = (typeof STEPS)[number]['id']
export const STEP_IDS: string[] = STEPS.map((s) => s.id)
