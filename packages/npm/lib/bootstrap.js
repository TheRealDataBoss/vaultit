import chalk from 'chalk'
import { existsSync, readFileSync } from 'fs'
import { resolve, join } from 'path'
import clipboardy from 'clipboardy'

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

function parseBridgeRepo(cwd) {
  const configPath = join(cwd, '.vaultit')
  if (!existsSync(configPath)) return null
  try {
    const config = JSON.parse(readFileSync(configPath, 'utf8'))
    return config.bridge_repo || null
  } catch {
    return null
  }
}

function extractOwnerRepo(repoUrl) {
  if (!repoUrl || repoUrl === 'local only') return null
  // Handle: https://github.com/owner/repo, https://github.com/owner/repo.git, owner/repo
  const match = repoUrl.match(/(?:github\.com\/)?([^/\s]+\/[^/\s.]+)/)
  return match ? match[1] : null
}

export async function generateBootstrap(options) {
  const cwd = resolve('.')

  console.log(chalk.cyan('\n  vaultit bootstrap\n'))

  // Find and read STATE_VECTOR.json
  const svPath = findStateVector(cwd)
  if (!svPath) {
    console.error(chalk.red('  ✗ bootstrap failed: STATE_VECTOR.json not found'))
    console.error(chalk.gray('    → Run: vaultit init to generate it (looked in handoff/, ./, .vaultit/)'))
    process.exit(1)
  }

  let stateVector
  try {
    stateVector = JSON.parse(readFileSync(svPath, 'utf8'))
  } catch {
    console.error(chalk.red(`  ✗ parse STATE_VECTOR.json failed: file contains invalid JSON`))
    console.error(chalk.gray(`    → Fix syntax errors in ${svPath} and retry`))
    process.exit(1)
  }

  const projectName = options.project || stateVector.project
  if (!projectName) {
    console.error(chalk.red('  ✗ bootstrap failed: no project name found'))
    console.error(chalk.gray('    → Pass --project <name>, or set "project" in STATE_VECTOR.json'))
    process.exit(1)
  }

  // Resolve bridge repo: --bridge flag > .vaultit config > STATE_VECTOR.repo
  const bridgeRepo = options.bridge
    || parseBridgeRepo(cwd)
    || extractOwnerRepo(stateVector.repo)

  if (!bridgeRepo) {
    console.error(chalk.red('  ✗ bootstrap failed: cannot determine bridge repo'))
    console.error(chalk.gray('    → Pass --bridge owner/repo, or set bridge_repo in .vaultit config'))
    process.exit(1)
  }

  // Build the 3 raw URLs
  const base = `https://raw.githubusercontent.com/${bridgeRepo}/main`
  const urls = {
    profile:  `${base}/PROFILE.md`,
    handoff:  `${base}/projects/${projectName}/HANDOFF.md`,
    state:    `${base}/projects/${projectName}/STATE_VECTOR.json`,
  }

  // Build the paste-ready prompt
  const prompt = [
    `Fetch these URLs and bootstrap the ${projectName} project:`,
    urls.profile,
    urls.handoff,
    urls.state,
  ].join('\n')

  // Print formatted block
  console.log(chalk.white('  Paste this into any new AI chat:\n'))
  console.log(chalk.green('  ┌──────────────────────────────────────────────────────────────┐'))
  for (const line of prompt.split('\n')) {
    console.log(chalk.green('  │ ') + chalk.white(line))
  }
  console.log(chalk.green('  └──────────────────────────────────────────────────────────────┘'))
  console.log()

  // Copy to clipboard
  try {
    await clipboardy.write(prompt)
    console.log(chalk.green('  Bootstrap prompt copied to clipboard. Paste it into Claude or ChatGPT.\n'))
  } catch {
    console.log(chalk.yellow('  ✗ clipboard write failed: clipboard not available in this environment'))
    console.log(chalk.gray('    → Copy the text above manually\n'))
  }
}
