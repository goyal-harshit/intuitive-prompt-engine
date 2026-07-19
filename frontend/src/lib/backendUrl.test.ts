import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getBackendUrl, getSavedBackendUrl, getWsUrl, setSavedBackendUrl } from './backendUrl'

describe('backendUrl', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => vi.unstubAllGlobals())

  it('uses same-origin (empty base) when served from localhost', () => {
    // jsdom's default origin is localhost
    expect(getBackendUrl()).toBe('')
    expect(getWsUrl()).toBe(`ws://${location.host}`)
  })

  it('falls back to localhost:8000 on a remote host with nothing saved', () => {
    vi.stubGlobal('location', {
      hostname: 'user.github.io',
      protocol: 'https:',
      host: 'user.github.io',
    })
    expect(getBackendUrl()).toBe('http://localhost:8000')
  })

  it('uses the saved URL on a remote host and strips trailing slashes', () => {
    setSavedBackendUrl('http://my-box:9000/')
    vi.stubGlobal('location', {
      hostname: 'user.github.io',
      protocol: 'https:',
      host: 'user.github.io',
    })
    expect(getBackendUrl()).toBe('http://my-box:9000')
    expect(getWsUrl()).toBe('ws://my-box:9000')
  })

  it('setSavedBackendUrl adds a scheme when missing and clears on empty input', () => {
    setSavedBackendUrl('my-box:9000')
    expect(getSavedBackendUrl()).toBe('http://my-box:9000')
    setSavedBackendUrl('   ')
    expect(getSavedBackendUrl()).toBe('http://localhost:8000') // default after clear
  })
})
