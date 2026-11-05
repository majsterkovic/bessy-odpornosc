import { Fragment } from 'react'

function inline(s: string) {
  return s.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : <Fragment key={i}>{part}</Fragment>)
}

/** Minimalny render tekstów z raportu: akapity, listy z "- " i pogrubienia **x**. */
export function Md({ text }: { text: string }) {
  const blocks: ({ kind: 'p'; text: string } | { kind: 'ul'; items: string[] })[] = []
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    if (line.startsWith('- ')) {
      const last = blocks[blocks.length - 1]
      if (last?.kind === 'ul') last.items.push(line.slice(2))
      else blocks.push({ kind: 'ul', items: [line.slice(2)] })
    } else blocks.push({ kind: 'p', text: line })
  }
  return (
    <>
      {blocks.map((b, i) => b.kind === 'ul'
        ? <ul key={i}>{b.items.map((it, j) => <li key={j}>{inline(it)}</li>)}</ul>
        : <p key={i}>{inline(b.text)}</p>)}
    </>
  )
}
