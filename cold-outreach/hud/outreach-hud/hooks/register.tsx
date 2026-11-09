import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Snapshot } from '../types'
import { snapshot } from './data'
import type { Files } from './data'

// Live side panel for the cold-outreach skill.
// Always: the Today card. On skill load and on /outreach: also the last 7 days and your settings.
// Look: neumorphic cards (raised surface, lit top-left rim, shadowed bottom-right rim, muted colors).
const PANE = 'outreach-hud'
const TITLE = 'Outreach'
const REFRESH_MS = 3000
const DETAILS_MS = 60_000
const FOREVER = 8.64e15

const snap = atom({ plugin: 'outreach-hud', key: 'snap' } as const, null)
const detailsUntil = atom({ plugin: 'outreach-hud', key: 'detailsUntil' } as const, 0)

// Soft palette on a dark slate surface.
const SURFACE = '#2b3040' // the raised card
const RIM_LIGHT = '#3d4458' // top-left highlight
const RIM_DARK = '#1a1d26' // bottom-right shadow
const TRACK = '#20242f' // the pressed-in groove of a bar
const INK = '#d7deef' // main text
const MUTED = '#8590ad' // labels
const ACCENT = '#7fdcd0' // soft teal
const BLUE = '#8fa3ff'
const GOOD = '#8ee0b0'
const WARN = '#f0c674'
const BAD = '#f29b9b'

type Seg = { t: string; c?: string; b?: boolean }

function workspacePath(ws: string | undefined, home: string): string {
  const raw = ws && ws.length ? ws : `${home}/Documents/cold-email`
  return raw.replace(/^~(?=\/|$)/, home)
}

async function readOr($: EngineInterface, path: string): Promise<string> {
  return (await $.fs.exists(path)) ? $.fs.read(path) : ''
}

async function load($: EngineInterface): Promise<Files> {
  const ws = workspacePath(await $.env.get('OUTREACH_WS'), (await $.env.get('HOME')) ?? '')
  let round: Files['round'] = null
  const roundsDir = `${ws}/rounds`
  if (await $.fs.exists(roundsDir)) {
    const dirs = (await $.fs.list(roundsDir)).filter(d => d.kind === 'dir').map(d => d.name).sort()
    const name = dirs[dirs.length - 1]
    if (name) {
      const entries = await $.fs.list(`${roundsDir}/${name}`)
      const tsvs = await Promise.all(
        entries.filter(x => x.kind === 'file' && /^_research_.*\.tsv$/.test(x.name))
          .map(x => $.fs.read(`${roundsDir}/${name}/${x.name}`)),
      )
      let drafts = 0
      for (const d of entries.filter(x => x.kind === 'dir')) {
        if (await $.fs.exists(`${roundsDir}/${name}/${d.name}/email.txt`)) drafts++
      }
      round = { name, tsvs, drafts }
    }
  }
  return {
    workspace: ws,
    profile: await readOr($, `${ws}/profile.toml`),
    sendLog: await readOr($, `${ws}/SEND-LOG.csv`),
    fuLog: await readOr($, `${ws}/FOLLOWUP-LOG.csv`),
    round,
  }
}

async function refresh($: EngineInterface, tick: number): Promise<void> {
  const now = await $.clock.now()
  let next: Snapshot
  try {
    next = snapshot(await load($), now, tick)
  } catch (err) {
    const prev = await read($, snap)
    if (!prev) return
    next = { ...prev, updatedAt: now, tick, error: String(err).slice(0, 80) }
  }
  await update($, snap, () => next)
}

async function showDetails($: EngineInterface, ms: number): Promise<void> {
  const now = await $.clock.now()
  await update($, detailsUntil, () => now + ms)
}

function hhmm(ms: number): string {
  const d = new Date(ms)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function pct(n: number, of: number): string {
  return of ? `${((100 * n) / of).toFixed(1)}%` : '0%'
}

// Split text into lines of at most n characters, breaking at spaces.
function wrapText(t: string, n: number): string[] {
  const out: string[] = []
  let cur = ''
  for (const word of t.split(' ')) {
    const next = cur ? `${cur} ${word}` : word
    if (next.length <= n) cur = next
    else {
      if (cur) out.push(cur)
      cur = word.length > n ? word.slice(0, n - 1) + '…' : word
    }
  }
  if (cur) out.push(cur)
  return out.length ? out : ['']
}

function fit(t: string, n: number): string {
  return t.length <= n ? t : t.slice(0, Math.max(0, n - 1)) + '…'
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'outreach', description: 'Show the outreach panel with progress and settings' })
    let tick = 0
    void refresh($, tick)
    $.clock.every(REFRESH_MS, () => {
      tick += 1
      void refresh($, tick)
    })
    return next(e)
  })

  on('command.run', { command: 'outreach' }, async $ => {
    await showDetails($, DETAILS_MS)
    await $.ui.open({ id: PANE, title: TITLE })
    await refresh($, 0)
    return { text: 'Outreach panel: today, the last 7 days and your settings.' }
  })

  on('skill.prompt', { skill: 'cold-outreach' }, async ($, e, next) => {
    await showDetails($, DETAILS_MS)
    void $.ui.open({ id: PANE, title: TITLE })
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const s = await read($, snap)
    const until = await read($, detailsUntil)
    const w = Math.max(30, e.props.bodyColumns)
    const inner = w - 4 // rim + space on each side

    // One raised card: lit rim on top and left, shadow rim on the right and bottom.
    const line = (segs: Seg[]) => {
      const used = segs.reduce((n, g) => n + g.t.length, 0)
      return (
        <Text>
          <Text color={RIM_LIGHT} backgroundColor={SURFACE}>▌ </Text>
          {segs.map(g => (
            <Text color={g.c ?? INK} bold={g.b} backgroundColor={SURFACE}>{g.t}</Text>
          ))}
          <Text backgroundColor={SURFACE}>{' '.repeat(Math.max(0, inner - used))}</Text>
          <Text color={RIM_DARK} backgroundColor={SURFACE}> ▐</Text>
        </Text>
      )
    }
    const card = (key: string, rows: Seg[][]) => (
      <Box key={key} flexDirection="column" marginBottom={1}>
        <Text color={RIM_LIGHT}>{' ' + '▄'.repeat(w - 2) + ' '}</Text>
        {rows.map(r => line(r))}
        <Text color={RIM_DARK}>{' ' + '▀'.repeat(w - 2) + ' '}</Text>
      </Box>
    )
    const label = (t: string): Seg => ({ t: t.padEnd(12), c: MUTED })

    if (!s) {
      return card('wait', [[{ t: 'Outreach', c: ACCENT, b: true }], [{ t: 'Reading your logs…', c: MUTED }]])
    }

    // Today
    const killed = s.todaySent > 0 && (100 * s.todayBounced) / s.todaySent > s.stopPct
    const tone = killed ? BAD : s.todaySent >= s.hi ? WARN : s.todaySent >= s.lo ? GOOD : ACCENT
    const barW = Math.max(8, inner - 12 - 10)
    const filled = Math.min(barW, Math.round((barW * s.todaySent) / Math.max(1, s.hi)))
    const tickAt = Math.min(barW - 1, Math.round((barW * s.lo) / Math.max(1, s.hi)))
    const groove = Array.from({ length: barW - filled }, (_, i) => (filled + i === tickAt ? '┃' : '━')).join('')
    const status = killed
      ? `Pause: over ${s.stopPct}% bounced`
      : s.todaySent >= s.hi
        ? 'Done for today'
        : s.todaySent >= s.lo
          ? `On target · ${s.hi - s.todaySent} left`
          : `${s.lo - s.todaySent} to go today`
    const allPct = s.allSent ? (100 * s.allBounced) / s.allSent : 0
    const dot = s.tick % 2 === 0 ? GOOD : '#5fae84'

    const today: Seg[][] = [
      [{ t: 'Today', c: ACCENT, b: true }, { t: ' '.repeat(Math.max(1, inner - 12)) }, { t: '● ', c: dot }, { t: hhmm(s.updatedAt), c: MUTED }],
      [{ t: fit(s.sender, inner), c: MUTED }],
      [],
      [label('New emails'), { t: '━'.repeat(filled), c: tone }, { t: groove, c: TRACK }, { t: ` ${s.todaySent}`, b: true }, { t: ` / ${s.lo}-${s.hi}`, c: MUTED }],
      [{ t: ' '.repeat(12) }, { t: fit(status, inner - 12), c: tone }],
      [label('Bounces'), { t: `${s.todayBounced} of ${s.todaySent} today`, c: killed ? BAD : s.todayBounced ? WARN : INK }, { t: fit(` · limit ${s.stopPct}%`, inner - 30), c: MUTED }],
      [label('Follow-ups'), { t: `${s.todayFu} sent today`, c: INK }, { t: ' · ', c: MUTED }, { t: `${s.dueFu1 + s.dueFu2} due`, c: s.dueFu1 + s.dueFu2 ? WARN : GOOD }],
      [label('Replies'), { t: `${s.replies}`, c: ACCENT, b: true }, { t: ` (${pct(s.replies, s.allSent)} of emails)`, c: MUTED }],
      [label('All time'), { t: `${s.allSent} sent`, c: INK }, { t: ' · ', c: MUTED }, { t: `${s.allBounced} bounced (${allPct.toFixed(1)}%)`, c: allPct > s.stopPct ? BAD : GOOD }],
      [{ t: ' '.repeat(12) }, { t: `${s.allFu} follow-ups`, c: INK }],
    ]
    if (s.error) today.push([{ t: fit(`Couldn't read a file: ${s.error}`, inner), c: WARN }])

    const showing = until > s.updatedAt
    const toggle = (
      <Box key="toggle" justifyContent="flex-end" marginBottom={1}>
        {showing ? (
          <Button key="hide" label="Hide details" onPress={() => update($, detailsUntil, () => 0)} />
        ) : (
          <Button key="show" label="Progress & settings" onPress={() => update($, detailsUntil, () => FOREVER)} />
        )}
      </Box>
    )

    if (!showing) {
      return <Box flexDirection="column" width={w}>{card('today', today)}{toggle}</Box>
    }

    // Last 7 days
    const peak = Math.max(s.hi, ...s.days.map(d => d.sent + d.fu))
    const dayW = Math.max(6, inner - 7 - 13)
    const week: Seg[][] = [
      [{ t: 'Last 7 days', c: ACCENT, b: true }, { t: '   ━ new  ', c: BLUE }, { t: '━ follow-ups', c: ACCENT }],
      [],
      ...s.days.map(d => {
        const n = Math.round((dayW * d.sent) / peak)
        const f = Math.min(dayW - n, Math.round((dayW * d.fu) / peak))
        const segs: Seg[] = [
          { t: d.label.padEnd(7), c: MUTED },
          { t: '━'.repeat(n), c: BLUE },
          { t: '━'.repeat(f), c: ACCENT },
          { t: '·'.repeat(Math.max(0, dayW - n - f)), c: TRACK },
          { t: String(d.sent).padStart(4), c: d.sent ? INK : MUTED },
          { t: String(d.fu).padStart(4), c: d.fu ? ACCENT : MUTED },
        ]
        segs.push(d.bounced ? { t: ` ✗${d.bounced}`.padEnd(5), c: BAD } : { t: '     ' })
        return segs
      }),
      [{ t: ' '.repeat(7 + dayW), c: MUTED }, { t: ' new', c: MUTED }, { t: '  fu', c: MUTED }, { t: ' bnc', c: MUTED }],
    ]
    if (s.round) {
      const r = s.round
      week.push([], [{ t: 'This round  ', c: MUTED }, { t: `${r.pass} found`, c: GOOD }, { t: ' · ', c: MUTED }, { t: `${r.fail} skipped`, c: INK }, { t: ' · ', c: MUTED }, { t: `${r.reveal} need a contact`, c: WARN }])
    }

    // Settings
    const settings: Seg[][] = [
      [{ t: 'Your settings', c: ACCENT, b: true }],
      [],
      ...s.settings.flatMap(x =>
        wrapText(x.value, inner - 12).map((part, i): Seg[] => [
          i === 0 ? label(x.label) : { t: ' '.repeat(12) },
          { t: part, c: INK },
        ])),
    ]

    return (
      <Box flexDirection="column" width={w}>
        {card('today', today)}
        {card('week', week)}
        {card('settings', settings)}
        {toggle}
      </Box>
    )
  })
}
