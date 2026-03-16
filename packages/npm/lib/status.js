import chalk from 'chalk'
import ora from 'ora'
import { existsSync, readFileSync, readdirSync } from 'fs'
import { resolve, join } from 'path'
import { simpleGit } from 'simple-git'
import { tmpdir } from 'os'
import { mkdtempSync, rmSync } from 'fs'

function loadConfig(cwd) {
  const configPath = join(cwd, '.vaultit')
  if (!existsSync(configPath)) return null
  try {
    return JSON.parse(readFileSync(configPath, 'utf8'))
  } catch {
    return null
  }
}

function colorStatus(status) {
  switch (status) {
    case 'EXECUTING':        return chalk.yellow.bold(status)
    case 'PROTOCOL_BREACH':  return chalk.red.bold(status)
    case 'IDLE':             return chalk.gray(status)
    case 'VERIFIED':         return chalk.green(status)
    case 'SEALED':           return chalk.green(status)
    case 'AWAITING_REVIEW':  return chalk.blue(status)
    case 'AWAITING_MANUAL_VALIDATION': return chalk.magenta(status)
    default:                 return chalk.white(status)
  }
}

function padRight(str, len) {
  const stripped = str.replace(/\x1b\[[0-9;]*m/g, '')
  return str + ' '.repeat(Math.max(0, len - stripped.length))
}

export async function showStatus(options) {
  const cwd = resolve('.')
  const config = loadConfig(cwd)
  const bridgeRepo = options.bridge || config?.bridge_repo

  console.log(chalk.cyan('\n  vaultit status\n'))

  if (!bridgeRepo) {
    console.error(chalk.red('  ✗ status failed: no bridge repo configured'))
    console.error(chalk.gray('    → Run: vaultit init, or pass --bridge <owner/repo>'))
    process.exit(1)
  }

  const spinner = ora('Fetching project states...').start()
  const tmpDir = mkdtempSync(join(tmpdir(), 'vaultit-'))

  try {
    const bridgeUrl = `https://github.com/${bridgeRepo}.git`
    const git = simpleGit()
    try {
      await git.clone(bridgeUrl, tmpDir, ['--depth', '1'])
    } catch (err) {
      spinner.fail('Fetch failed')
      const msg = err?.message || String(err)
      if (msg.includes('not found') || msg.includes('404')) {
        console.error(chalk.red(`  ✗ git clone failed: repository ${bridgeRepo} not found`))
        console.error(chalk.gray('    → Verify the bridge repo name is correct'))
      } else if (msg.includes('could not resolve host') || msg.includes('unable to access')) {
        console.error(chalk.red('  ✗ git clone failed: network error'))
        console.error(chalk.gray('    → Check your internet connection and try again'))
      } else {
        const cleaned = msg.replace(/https:\/\/[^@\s]+@/g, 'https://***@')
        console.error(chalk.red(`  ✗ git clone failed: ${cleaned}`))
        console.error(chalk.gray('    → Check git configuration and bridge repo access'))
      }
      process.exit(1)
    }
    spinner.succeed('Bridge repo loaded')

    const projectsDir = join(tmpDir, 'projects')
    if (!existsSync(projectsDir)) {
      console.log(chalk.yellow('  No projects directory found in bridge repo.'))
      return
    }

    const projects = readdirSync(projectsDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => d.name)

    if (projects.length === 0) {
      console.log(chalk.yellow('  No projects found.'))
      return
    }

    const rows = []
    for (const name of projects) {
      const svPath = join(projectsDir, name, 'STATE_VECTOR.json')
      if (!existsSync(svPath)) {
        rows.push({ name, type: '?', status: 'NO STATE', task: '-', blocker: '-', updated: '-' })
        continue
      }
      let sv
      try {
        sv = JSON.parse(readFileSync(svPath, 'utf8'))
      } catch {
        rows.push({ name, type: '?', status: 'BAD JSON', task: '-', blocker: '-', updated: '-' })
        continue
      }
      rows.push({
        name,
        type: sv.project_type || '?',
        status: sv.state_machine_status || '?',
        task: sv.active_task_id ? `${sv.active_task_id}: ${sv.active_task_title || ''}`.substring(0, 50) : '-',
        blocker: sv.current_blocker ? sv.current_blocker.substring(0, 40) + (sv.current_blocker.length > 40 ? '...' : '') : '-',
        updated: sv.last_updated || '?',
      })
    }

    if (options.json) {
      console.log(JSON.stringify(rows, null, 2))
      return
    }

    // Table header
    const colWidths = { name: 20, type: 18, status: 30, task: 52, updated: 12 }

    console.log()
    console.log(
      '  ' +
      chalk.bold(padRight('Project', colWidths.name)) +
      chalk.bold(padRight('Type', colWidths.type)) +
      chalk.bold(padRight('Status', colWidths.status)) +
      chalk.bold(padRight('Active Task', colWidths.task)) +
      chalk.bold(padRight('Updated', colWidths.updated))
    )
    console.log('  ' + '─'.repeat(colWidths.name + colWidths.type + 16 + colWidths.task + colWidths.updated))

    for (const row of rows) {
      console.log(
        '  ' +
        padRight(chalk.white(row.name), colWidths.name) +
        padRight(chalk.gray(row.type), colWidths.type) +
        padRight(colorStatus(row.status), colWidths.status) +
        padRight(chalk.white(row.task), colWidths.task) +
        padRight(chalk.gray(row.updated), colWidths.updated)
      )
    }

    // Show blockers if any exist
    const blocked = rows.filter(r => r.blocker !== '-')
    if (blocked.length > 0) {
      console.log(chalk.yellow('\n  Blockers:'))
      for (const row of blocked) {
        console.log(chalk.red(`    ${row.name}: ${row.blocker}`))
      }
    }

    console.log()
  } finally {
    try { rmSync(tmpDir, { recursive: true, force: true }) } catch {}
  }
}
