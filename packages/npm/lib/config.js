import { readFileSync, writeFileSync, mkdirSync } from 'fs'
import { homedir } from 'os'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const RC_PATH = join(homedir(), '.vaultitrc')

function readRc() {
  try {
    return JSON.parse(readFileSync(RC_PATH, 'utf8'))
  } catch {
    return {}
  }
}

function writeRc(data) {
  try {
    writeFileSync(RC_PATH, JSON.stringify(data, null, 2) + '\n', 'utf8')
    return true
  } catch {
    return false
  }
}

export function getConfig(key) {
  const rc = readRc()
  if (key === undefined) return rc
  return rc[key] ?? null
}

export function setConfig(key, value) {
  const rc = readRc()
  rc[key] = value
  return writeRc(rc)
}

export function getToken() {
  return getConfig('npm_token') ?? getConfig('token') ?? null
}

export function setToken(token) {
  return setConfig('npm_token', token)
}

// --- Self-test ---
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const assert = (cond, msg) => {
    if (!cond) { console.error(`FAIL: ${msg}`); process.exit(1) }
    console.log(`PASS: ${msg}`)
  }

  // getConfig on missing key returns null
  assert(getConfig('__nonexistent_test_key__') === null, 'missing key returns null')

  // setConfig + getConfig round-trip
  setConfig('__test_key__', 'hello')
  assert(getConfig('__test_key__') === 'hello', 'set/get round-trip')

  // overwrite
  setConfig('__test_key__', 42)
  assert(getConfig('__test_key__') === 42, 'overwrite preserves type')

  // getConfig() with no args returns full object
  const all = getConfig()
  assert(typeof all === 'object' && all.__test_key__ === 42, 'getConfig() returns full rc')

  // setToken + getToken round-trip
  setToken('tok_abc123')
  assert(getToken() === 'tok_abc123', 'setToken/getToken round-trip')

  // cleanup test keys
  const rc = readRc()
  delete rc.__test_key__
  delete rc.npm_token
  writeRc(rc)
  assert(getConfig('__test_key__') === null, 'cleanup verified')

  console.log(`\nAll tests passed. RC path: ${RC_PATH}`)
}
