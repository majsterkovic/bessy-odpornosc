const DASH = '–'
type Num = number | null | undefined

const ok = (x: Num): x is number => typeof x === 'number' && Number.isFinite(x)

function group(intPart: string): string {
  return intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

/** Liczba w formacie polskim: przecinek dziesiętny, spacja jako separator tysięcy. */
export function fmtNum(x: Num, d = 1, signed = false): string {
  if (!ok(x)) return DASH
  let s = Math.abs(x).toFixed(d)
  const zero = Number(s) === 0
  const [i, f] = s.split('.')
  s = group(i) + (f ? ',' + f : '')
  if (zero) return s
  if (x < 0) return '-' + s
  return signed ? '+' + s : s
}

export const fmtInt = (x: Num, signed = false) => fmtNum(x, 0, signed)

/** Ułamek (0,124) jako procent. */
export function fmtPct(x: Num, d = 1, signed = false): string {
  return ok(x) ? fmtNum(x * 100, d, signed) + '%' : DASH
}

/** Różnica ułamków jako punkty procentowe, zawsze ze znakiem. */
export function fmtPp(x: Num, d = 1): string {
  return ok(x) ? fmtNum(x * 100, d, true) + ' pp' : DASH
}

export function fmtDate(iso: string | null | undefined): string {
  return iso ? iso : DASH
}
