import chalk from 'chalk'
import ora from 'ora'
import { input, confirm } from '@inquirer/prompts'
import { existsSync, mkdirSync, readdirSync, writeFileSync } from 'fs'
import { basename, resolve, join } from 'path'

const PROJECT_TYPE_SIGNALS = [
  { file: 'manage.py',        type: 'web_app',           label: 'Django web app' },
  { file: 'next.config.js',   type: 'web_app',           label: 'Next.js web app' },
  { file: 'next.config.mjs',  type: 'web_app',           label: 'Next.js web app' },
  { file: 'vite.config.ts',   type: 'web_app',           label: 'Vite web app' },
  { file: 'vite.config.js',   type: 'web_app',           label: 'Vite web app' },
  { file: 'Cargo.toml',       type: 'cli_tool',          label: 'Rust project' },
  { file: 'setup.py',         type: 'library',           label: 'Python library' },
  { file: 'pyproject.toml',   type: 'library',           label: 'Python project' },
  { file: 'requirements.txt', type: 'ml_pipeline',       label: 'Python ML pipeline' },
  { file: 'package.json',     type: 'web_app',           label: 'Node.js project' },
]

function detectProjectType(dir) {
  for (const signal of PROJECT_TYPE_SIGNALS) {
    if (existsSync(join(dir, signal.file))) {
      return { type: signal.type, label: signal.label, file: signal.file }
    }
  }
  // Check for notebooks
  try {
    const files = readdirSync(dir)
    if (files.some(f => f.endsWith('.ipynb'))) {
      return { type: 'research_notebook', label: 'Research notebook', file: '*.ipynb' }
    }
  } catch {}
  return { type: 'other', label: 'unknown project type', file: null }
}

function detectGates(projectType) {
  const gates = {
    web_app:           ['npm test', 'npm run build', 'git status'],
    ml_pipeline:       ['python -m pytest', 'git status'],
    research_notebook: ['jupyter nbconvert --execute --to notebook', 'git status'],
    data_pipeline:     ['python -m pytest', 'git status'],
    mobile_app:        ['npm test', 'npm run build', 'git status'],
    cli_tool:          ['npm test', 'npm run build', 'git status'],
    library:           ['npm test', 'npm run build', 'git status'],
    course_module:     ['jupyter nbconvert --execute --to notebook', 'git status'],
    other:             ['git status'],
  }
  return gates[projectType] || ['git status']
}

function safeWriteFile(filePath, content, label) {
  try {
    writeFileSync(filePath, content, 'utf8')
    return true
  } catch (err) {
    console.error(chalk.red(`  ✗ write ${label} failed: ${err.code === 'EACCES' ? 'permission denied' : err.code === 'ENOSPC' ? 'disk full' : err.message}`))
    console.error(chalk.gray(`    → Check permissions on ${filePath}`))
    return false
  }
}

export async function initProject(options) {
  const cwd = resolve('.')
  const dirName = basename(cwd)

  console.log(chalk.cyan('\n  vaultit init\n'))

  // Detect project type
  const spinner = ora('Detecting project type...').start()
  const detected = detectProjectType(cwd)
  spinner.succeed(`Detected: ${chalk.bold(detected.label)}${detected.file ? ` (found ${detected.file})` : ''}`)

  const projectType = options.type || detected.type

  // Interactive prompts for missing fields
  const projectName = options.project || await input({
    message: 'Project name (slug):',
    default: dirName,
  })

  const description = await input({
    message: 'Project description (one line):',
    default: '',
  })

  let bridgeRepo = options.bridge || await input({
    message: 'Bridge repo (e.g. yourname/vaultit):',
    default: '',
  }) || null

  // Check for existing STATE_VECTOR.json
  const handoffDir = join(cwd, 'handoff')
  const stateVectorPath = join(handoffDir, 'STATE_VECTOR.json')
  if (existsSync(stateVectorPath)) {
    const overwrite = await confirm({
      message: 'STATE_VECTOR.json already exists. Overwrite?',
      default: false,
    })
    if (!overwrite) {
      console.log(chalk.yellow('\n  Aborted. Existing files unchanged.\n'))
      return
    }
  }

  // Create directories
  const docsDir = join(cwd, 'docs')
  try {
    mkdirSync(handoffDir, { recursive: true })
    mkdirSync(docsDir, { recursive: true })
  } catch (err) {
    console.error(chalk.red(`  ✗ create directories failed: ${err.code === 'EACCES' ? 'permission denied' : err.message}`))
    console.error(chalk.gray(`    → Check write permissions on ${cwd}`))
    process.exit(1)
  }

  // Generate STATE_VECTOR.json
  const stateVector = {
    schema_version: 'vaultit-v1.0',
    project: projectName,
    project_type: projectType,
    local_path: cwd,
    state_machine_status: 'IDLE',
    active_task_id: null,
    active_task_title: null,
    current_blocker: null,
    last_verified_state: 'Initial project setup',
    gates: detectGates(projectType),
    last_updated: new Date().toISOString().split('T')[0],
    repo: bridgeRepo ? `https://github.com/${bridgeRepo}` : 'local only',
    branch: 'main',
    repo_head_sha: null,
    effective_verified_sha: null,
  }

  if (!safeWriteFile(stateVectorPath, JSON.stringify(stateVector, null, 2) + '\n', 'STATE_VECTOR.json')) {
    process.exit(1)
  }
  console.log(chalk.green(`  Created: ${stateVectorPath}`))

  // Generate HANDOFF.md
  const descLine = description || '[FILL IN: Describe this project in one paragraph.]'
  const handoff = `# ${projectName} — Project Handoff
schema_version: vaultit-v1.0

## What It Is
${descLine}

## Where It Is
- Local: ${cwd}
- GitHub: ${stateVector.repo}
- Branch: main

## Current Status
State machine: IDLE. No active task.

## Active Blocker
None

## Non-Negotiables
- [FILL IN: List project invariants]

## Gates
${stateVector.gates.map(g => `- ${g}`).join('\n')}

## Environment Setup
[FILL IN: Steps to run from a clean clone]

## Next Action
[FILL IN: First task to work on]
`

  const handoffPath = join(docsDir, 'HANDOFF.md')
  if (!safeWriteFile(handoffPath, handoff, 'HANDOFF.md')) {
    process.exit(1)
  }
  console.log(chalk.green(`  Created: ${handoffPath}`))

  // Write .vaultit config
  const config = {
    bridge_repo: bridgeRepo,
    project_name: projectName,
    state_vector_path: 'handoff/STATE_VECTOR.json',
    handoff_path: 'docs/HANDOFF.md',
  }
  const configPath = join(cwd, '.vaultit')
  if (!safeWriteFile(configPath, JSON.stringify(config, null, 2) + '\n', '.vaultit config')) {
    process.exit(1)
  }
  console.log(chalk.green(`  Created: ${configPath}`))

  console.log(chalk.cyan('\n  Next steps:'))
  console.log(chalk.white('  1. Fill in the [FILL IN] sections in docs/HANDOFF.md'))
  console.log(chalk.white('  2. Review handoff/STATE_VECTOR.json'))
  console.log(chalk.white(`  3. Run: ${chalk.bold('vaultit sync')} to push to your bridge repo`))
  console.log()
}
