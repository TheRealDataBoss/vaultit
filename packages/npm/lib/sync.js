import chalk from 'chalk'
import ora from 'ora'
import { password } from '@inquirer/prompts'
import { existsSync, readFileSync, mkdirSync, copyFileSync } from 'fs'
import { resolve, join } from 'path'
import { simpleGit } from 'simple-git'
import { tmpdir } from 'os'
import { mkdtempSync, rmSync } from 'fs'
import Ajv from 'ajv'
import addFormats from 'ajv-formats'
import { fileURLToPath } from 'url'
import { dirname } from 'path'
import { getToken, setToken } from './config.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

function loadProjectConfig(cwd) {
  const configPath = join(cwd, '.vaultit')
  if (!existsSync(configPath)) return null
  try {
    return JSON.parse(readFileSync(configPath, 'utf8'))
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

function friendlyGitError(err, phase) {
  const msg = err?.message || String(err)

  if (msg.includes('Authentication failed') || msg.includes('403') || msg.includes('401')) {
    return {
      what: `authentication denied — token may be expired or lack repo scope`,
      next: `Run: vaultit sync (you will be prompted for a new token)`,
    }
  }
  if (msg.includes('not found') || msg.includes('404') || msg.includes('Repository not found')) {
    return {
      what: `repository not found`,
      next: `Verify the bridge repo name is correct and the token has access`,
    }
  }
  if (msg.includes('could not resolve host') || msg.includes('unable to access')) {
    return {
      what: `network error — could not reach GitHub`,
      next: `Check your internet connection and try again`,
    }
  }
  if (msg.includes('non-fast-forward') || msg.includes('rejected')) {
    return {
      what: `remote has newer commits than local`,
      next: `Pull the bridge repo manually and retry`,
    }
  }
  // Generic fallback — strip any token from error message
  const cleaned = msg.replace(/https:\/\/[^@\s]+@/g, 'https://***@')
  return {
    what: cleaned,
    next: `Check git configuration and retry`,
  }
}

function printGitError(phase, err) {
  const { what, next } = friendlyGitError(err, phase)
  console.error(chalk.red(`  ✗ git ${phase} failed: ${what}`))
  console.error(chalk.gray(`    → ${next}`))
}

async function resolveToken() {
  let token = getToken()
  if (token) return token

  console.log(chalk.yellow('  No GitHub token found in ~/.vaultitrc'))
  console.log(chalk.gray('  Create a token at: https://github.com/settings/tokens'))
  console.log(chalk.gray('  Required scope: repo (full control of private repositories)\n'))

  token = await password({
    message: 'GitHub Personal Access Token:',
    mask: '*',
  })

  if (!token) {
    console.error(chalk.red('  ✗ token prompt failed: no token provided'))
    console.error(chalk.gray('    → Create a token at https://github.com/settings/tokens and retry'))
    process.exit(1)
  }

  setToken(token)
  console.log(chalk.green('  Token saved to ~/.vaultitrc\n'))
  return token
}

function buildAuthUrl(bridgeRepo, token) {
  return `https://${token}@github.com/${bridgeRepo}.git`
}

export async function syncProject(options) {
  const cwd = resolve('.')
  const config = loadProjectConfig(cwd)

  console.log(chalk.cyan('\n  vaultit sync\n'))

  if (!config && !options.bridge) {
    console.error(chalk.red('  ✗ sync failed: no .vaultit config found'))
    console.error(chalk.gray('    → Run: vaultit init, or pass --bridge <owner/repo>'))
    process.exit(1)
  }

  const bridgeRepo = options.bridge || config?.bridge_repo
  const projectName = config?.project_name || ''
  const stateVectorRel = config?.state_vector_path || 'handoff/STATE_VECTOR.json'
  const handoffRel = config?.handoff_path || 'docs/HANDOFF.md'

  if (!bridgeRepo) {
    console.error(chalk.red('  ✗ sync failed: no bridge repo configured'))
    console.error(chalk.gray('    → Run: vaultit init, or pass --bridge <owner/repo>'))
    process.exit(1)
  }

  if (!projectName) {
    console.error(chalk.red('  ✗ sync failed: no project_name in .vaultit config'))
    console.error(chalk.gray('    → Run: vaultit init to regenerate the config'))
    process.exit(1)
  }

  // Validate STATE_VECTOR.json
  const stateVectorPath = join(cwd, stateVectorRel)
  if (!existsSync(stateVectorPath)) {
    console.error(chalk.red(`  ✗ sync failed: STATE_VECTOR.json not found at ${stateVectorRel}`))
    console.error(chalk.gray('    → Run: vaultit init to generate it'))
    process.exit(1)
  }

  const spinner = ora('Validating STATE_VECTOR.json...').start()

  let stateVector
  try {
    stateVector = JSON.parse(readFileSync(stateVectorPath, 'utf8'))
  } catch (err) {
    spinner.fail('Validation failed')
    console.error(chalk.red(`  ✗ parse STATE_VECTOR.json failed: invalid JSON`))
    console.error(chalk.gray(`    → Fix syntax errors in ${stateVectorRel} and retry`))
    process.exit(1)
  }

  const schema = loadSchema()
  if (schema) {
    const ajv = new Ajv({ allErrors: true })
    addFormats(ajv)
    const validate = ajv.compile(schema)
    if (!validate(stateVector)) {
      spinner.fail('Validation failed')
      const errors = validate.errors.map(e => `${e.instancePath || '/'}: ${e.message}`).join(', ')
      console.error(chalk.red(`  ✗ validate STATE_VECTOR.json failed: ${errors}`))
      console.error(chalk.gray(`    → Fix the listed fields in ${stateVectorRel} and retry`))
      process.exit(1)
    }
  }
  spinner.succeed('STATE_VECTOR.json is valid')

  // Dry run
  if (options.dryRun) {
    console.log(chalk.yellow('\n  Dry run — would sync:'))
    console.log(chalk.white(`    ${stateVectorRel} → projects/${projectName}/STATE_VECTOR.json`))
    if (existsSync(join(cwd, handoffRel))) {
      console.log(chalk.white(`    ${handoffRel} → projects/${projectName}/HANDOFF.md`))
    }
    console.log()
    return
  }

  // Resolve GitHub token
  const token = await resolveToken()
  const authUrl = buildAuthUrl(bridgeRepo, token)

  // Clone bridge repo
  const cloneSpinner = ora(`Cloning ${bridgeRepo}...`).start()
  const tmpDir = mkdtempSync(join(tmpdir(), 'vaultit-'))

  try {
    const git = simpleGit()
    try {
      await git.clone(authUrl, tmpDir, ['--depth', '1'])
    } catch (err) {
      cloneSpinner.fail('Clone failed')
      printGitError('clone', err)
      process.exit(1)
    }
    cloneSpinner.succeed(`Cloned ${bridgeRepo}`)

    // Copy state files into bridge repo
    const targetDir = join(tmpDir, 'projects', projectName)
    try {
      mkdirSync(targetDir, { recursive: true })
    } catch (err) {
      console.error(chalk.red(`  ✗ create project directory failed: ${err.message}`))
      console.error(chalk.gray(`    → Check disk space and permissions on temp directory`))
      process.exit(1)
    }

    copyFileSync(stateVectorPath, join(targetDir, 'STATE_VECTOR.json'))
    console.log(chalk.green('  Copied: STATE_VECTOR.json'))

    const handoffPath = join(cwd, handoffRel)
    if (existsSync(handoffPath)) {
      copyFileSync(handoffPath, join(targetDir, 'HANDOFF.md'))
      console.log(chalk.green('  Copied: HANDOFF.md'))
    }

    const nextTaskPath = join(cwd, 'docs', 'NEXT_TASK.md')
    if (existsSync(nextTaskPath)) {
      copyFileSync(nextTaskPath, join(targetDir, 'NEXT_TASK.md'))
      console.log(chalk.green('  Copied: NEXT_TASK.md'))
    }

    // Commit
    const bridgeGit = simpleGit(tmpDir)
    await bridgeGit.addConfig('user.name', 'vaultit-ai')
    await bridgeGit.addConfig('user.email', 'vaultit-ai@users.noreply.github.com')

    try {
      await bridgeGit.add('-A')
    } catch (err) {
      printGitError('add', err)
      process.exit(1)
    }

    const status = await bridgeGit.status()
    if (status.files.length === 0) {
      console.log(chalk.yellow('\n  No changes to push — bridge repo is already up to date.\n'))
      return
    }

    const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 16) + ' UTC'
    const commitMsg = `vaultit sync: ${projectName} -- ${timestamp}`

    try {
      await bridgeGit.commit(commitMsg)
    } catch (err) {
      printGitError('commit', err)
      process.exit(1)
    }

    // Push
    const pushSpinner = ora('Pushing to bridge repo...').start()
    try {
      await bridgeGit.push('origin', 'main')
    } catch (err) {
      pushSpinner.fail('Push failed')
      printGitError('push', err)
      process.exit(1)
    }

    const log = await bridgeGit.log({ maxCount: 1 })
    const sha = log.latest.hash.substring(0, 7)

    pushSpinner.succeed(`Pushed: ${chalk.bold(sha)}`)
    console.log(chalk.green(`\n  Sync complete for ${chalk.bold(projectName)}`))
    console.log(chalk.gray(`  ${commitMsg}\n`))
  } finally {
    try { rmSync(tmpDir, { recursive: true, force: true }) } catch {}
  }
}
