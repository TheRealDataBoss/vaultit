import chalk from 'chalk'
import { execSync } from 'child_process'
import { existsSync, readFileSync } from 'fs'
import { resolve, join } from 'path'
import { fileURLToPath } from 'url'
import { dirname } from 'path'
import Ajv from 'ajv'
import addFormats from 'ajv-formats'
import { getToken } from './config.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const PASS = chalk.green('✓')
const FAIL = chalk.red('✗')

function run(cmd) {
  try {
    return execSync(cmd, { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] }).trim()
  } catch {
    return null
  }
}

function loadSchema() {
  const candidates = [
    resolve(__dirname, '..', '..', '..', 'protocol', 'vaultit.schema.json'),
    join(process.env.HOME || process.env.USERPROFILE, '.vaultit', 'src', 'protocol', 'vaultit.schema.json'),
  ]
  for (const p of candidates) {
    if (existsSync(p)) {
      try { return JSON.parse(readFileSync(p, 'utf8')) } catch { /* skip */ }
    }
  }
  return null
}

function findStateVector(cwd) {
  const candidates = [
    join(cwd, 'handoff', 'STATE_VECTOR.json'),
    join(cwd, 'STATE_VECTOR.json'),
    join(cwd, '.vaultit', 'STATE_VECTOR.json'),
  ]
  for (const p of candidates) {
    if (existsSync(p)) return p
  }
  return null
}

export async function runDoctor() {
  const cwd = resolve('.')
  let passed = 0
  let failed = 0

  console.log(chalk.cyan('\n  vaultit doctor\n'))

  // 1. Node version >= 18
  const nodeVer = process.versions.node
  const nodeMajor = parseInt(nodeVer.split('.')[0], 10)
  if (nodeMajor >= 18) {
    console.log(`  ${PASS} Node.js installed (v${nodeVer})`)
    passed++
  } else {
    console.log(`  ${FAIL} Node.js v${nodeVer} — requires >= 18. Update at https://nodejs.org`)
    failed++
  }

  // 2. git installed
  const gitVersion = run('git --version')
  if (gitVersion) {
    const ver = gitVersion.replace('git version ', '').trim()
    console.log(`  ${PASS} git installed (${ver})`)
    passed++
  } else {
    console.log(`  ${FAIL} git not found — install git and add it to PATH`)
    failed++
  }

  // 3. git config user.name
  const gitName = run('git config user.name')
  if (gitName) {
    console.log(`  ${PASS} git user.name set (${gitName})`)
    passed++
  } else {
    console.log(`  ${FAIL} git user.name not set — run: git config --global user.name "Your Name"`)
    failed++
  }

  // 4. git config user.email
  const gitEmail = run('git config user.email')
  if (gitEmail) {
    console.log(`  ${PASS} git user.email set (${gitEmail})`)
    passed++
  } else {
    console.log(`  ${FAIL} git user.email not set — run: git config --global user.email "you@example.com"`)
    failed++
  }

  // 5. GitHub PAT exists
  const token = getToken()
  if (token) {
    console.log(`  ${PASS} GitHub token found in ~/.vaultitrc`)
    passed++
  } else {
    console.log(`  ${FAIL} GitHub token missing — run: vaultit sync to configure`)
    failed++
  }

  // 6. GitHub PAT is valid
  if (token) {
    try {
      const res = await fetch('https://api.github.com/user', {
        headers: {
          'Authorization': `token ${token}`,
          'User-Agent': 'vaultit-ai-cli',
          'Accept': 'application/vnd.github.v3+json',
        },
      })
      if (res.ok) {
        const data = await res.json()
        console.log(`  ${PASS} GitHub token valid (authenticated as ${data.login})`)
        passed++
      } else if (res.status === 401) {
        console.log(`  ${FAIL} GitHub token expired or revoked — run: vaultit sync to reconfigure`)
        failed++
      } else {
        console.log(`  ${FAIL} GitHub token check returned HTTP ${res.status} — verify token scopes`)
        failed++
      }
    } catch (err) {
      console.log(`  ${FAIL} GitHub token check failed — network error: ${err.message}`)
      failed++
    }
  } else {
    console.log(`  ${chalk.gray('-')} GitHub token validation skipped (no token)`)
  }

  // 7. STATE_VECTOR.json exists and is valid JSON
  const svPath = findStateVector(cwd)
  let stateVector = null
  if (svPath) {
    try {
      stateVector = JSON.parse(readFileSync(svPath, 'utf8'))
      console.log(`  ${PASS} STATE_VECTOR.json found and valid JSON (${svPath})`)
      passed++
    } catch (err) {
      console.log(`  ${FAIL} STATE_VECTOR.json found but invalid JSON — ${err.message}`)
      failed++
    }
  } else {
    console.log(`  ${FAIL} STATE_VECTOR.json not found — run: vaultit init`)
    failed++
  }

  // 8. STATE_VECTOR.json validates against schema
  if (stateVector) {
    const schema = loadSchema()
    if (schema) {
      const ajv = new Ajv({ allErrors: true })
      addFormats(ajv)
      const validate = ajv.compile(schema)
      if (validate(stateVector)) {
        console.log(`  ${PASS} STATE_VECTOR.json passes schema validation`)
        passed++
      } else {
        const errors = validate.errors.map(e => `${e.instancePath || '/'}: ${e.message}`).join(', ')
        console.log(`  ${FAIL} STATE_VECTOR.json schema errors — ${errors}`)
        failed++
      }
    } else {
      console.log(`  ${chalk.gray('-')} Schema validation skipped (vaultit.schema.json not found)`)
    }
  } else {
    console.log(`  ${chalk.gray('-')} Schema validation skipped (no STATE_VECTOR.json)`)
  }

  // Summary
  const total = passed + failed
  console.log()
  if (failed === 0) {
    console.log(chalk.green(`  All ${total} checks passed.\n`))
  } else {
    console.log(chalk.yellow(`  ${passed}/${total} checks passed, ${failed} failed.\n`))
  }

  return { passed, failed }
}
