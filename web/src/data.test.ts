import { afterEach, describe, expect, it, vi } from 'vitest'
import { DataError, loadAll } from './data'
import { sample } from './testData'

const FILES = ['meta', 'market', 'episodes', 'twins', 'sectors', 'funnel', 'validation', 'lists', 'series']

function mockFetch(meta: object, missing?: string) {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    const name = url.split('/').pop()!.replace('.json', '')
    if (name === missing) return { ok: false, status: 404, json: async () => ({}) }
    return { ok: true, status: 200, json: async () => (name === 'meta' ? meta : (sample as unknown as Record<string, unknown>)[name]) }
  }))
}

afterEach(() => vi.unstubAllGlobals())

describe('loadAll', () => {
  it('loads all nine files', async () => {
    mockFetch(sample.meta)
    const d = await loadAll('./data')
    expect(Object.keys(d).sort()).toEqual([...FILES].sort())
  })
  it('throws DataError mentioning the exporter when a file is missing', async () => {
    mockFetch(sample.meta, 'lists')
    await expect(loadAll('./data')).rejects.toThrow(/bessy\.export_web/)
    await expect(loadAll('./data')).rejects.toBeInstanceOf(DataError)
  })
  it('throws DataError for an unsupported version', async () => {
    mockFetch({ ...sample.meta, version: 2 })
    await expect(loadAll('./data')).rejects.toThrow(/bessy\.export_web/)
  })
})

describe('loadAll robustness', () => {
  it('turns an HTML fallback response into a DataError with the exporter hint', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, headers: new Headers({ 'content-type': 'text/html' }), json: async () => { throw new SyntaxError('Unexpected token <') } })))
    await expect(loadAll('./data')).rejects.toThrow(/bessy\.export_web/)
  })
  it('rejects a file with the wrong shape', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      const name = url.split('/').pop()!.replace('.json', '')
      return { ok: true, status: 200, headers: new Headers({ 'content-type': 'application/json' }), json: async () => (name === 'meta' ? sample.meta : {}) }
    }))
    await expect(loadAll('./data')).rejects.toThrow(/lists\.json.*stocks_a|stocks_a.*lists\.json|bessy\.export_web/)
  })
})
