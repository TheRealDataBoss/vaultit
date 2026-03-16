#!/usr/bin/env node

import { Command } from 'commander'
import chalk from 'chalk'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const pkg = JSON.parse(readFileSync(join(__dirname, '..', 'package.json'), 'utf8'))

const program = new Command()

program
  .name('vaultit')
  .description('Zero model drift between AI agents. Universal session continuity protocol and CLI for Claude, GPT, Gemini, and any LLM.')
  .version(pkg.version, '-v, --version')

program
  .command('init')
  .description('Initialize vaultit state files in the current project')
  .option('-p, --project <name>', 'Project slug')
  .option('-t, --type <type>', 'Project type')
  .option('--bridge <repo>', 'Bridge repo URL (e.g. user/vaultit)')
  .action(async (options) => {
    const { initProject } = await import('../lib/init.js')
    await initProject(options)
  })

program
  .command('sync')
  .description('Sync state files to the bridge repo')
  .option('--bridge <repo>', 'Bridge repo URL override')
  .option('--dry-run', 'Show what would be synced without pushing')
  .action(async (options) => {
    const { syncProject } = await import('../lib/sync.js')
    await syncProject(options)
  })

program
  .command('status')
  .description('Show status of all projects in the bridge repo')
  .option('--bridge <repo>', 'Bridge repo URL override')
  .option('--json', 'Output as JSON')
  .action(async (options) => {
    const { showStatus } = await import('../lib/status.js')
    await showStatus(options)
  })

program
  .command('bootstrap')
  .description('Generate a paste-ready bootstrap prompt for any AI')
  .requiredOption('-p, --project <name>', 'Project slug')
  .option('--bridge <repo>', 'Bridge repo URL override')
  .option('--clipboard', 'Copy to clipboard')
  .action(async (options) => {
    const { generateBootstrap } = await import('../lib/bootstrap.js')
    await generateBootstrap(options)
  })

program
  .command('doctor')
  .description('Check environment and configuration health')
  .action(async () => {
    const { runDoctor } = await import('../lib/doctor.js')
    await runDoctor()
  })

program.parse()
