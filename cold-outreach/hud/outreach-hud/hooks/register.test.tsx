import { expect, test } from 'claude-code/testing'

// 2026-10-22 12:00 local; the fake workspace below is dated around it.
const NOW = new Date(2026, 9, 22, 12, 0, 0).getTime()
const WS = '/home/u/Documents/cold-email'

const FILES: Record<string, string> = {
  [`${WS}/profile.toml`]: '[sending]\ngmail_address = "me@college.ac.in"\ndaily_min = 30\ndaily_cap = 40\nbounce_stop_pct = 3\n',
  [`${WS}/SEND-LOG.csv`]:
    'date_sent,company,person,email,subject,followup1_due,followup2_due,reply,outcome\n' +
    '2026-10-22,acme,A,a@acme.ai,"Hi, there",2026-10-26,2026-11-02,,SENT\n' +
    '2026-10-22,beta,B,b@beta.io,S,2026-10-26,2026-11-02,,BOUNCED 550\n' +
    '2026-10-15,gamma,C,c@gamma.io,S,2026-10-19,2026-10-26,,SENT\n' +
    '2026-10-15,delta,D,d@delta.io,S,2026-10-19,2026-10-26,yes call,SENT\n',
  [`${WS}/FOLLOWUP-LOG.csv`]:
    'date,time,stage,company,email,subject,result,detail,sender\n' +
    '2026-10-22,09:00:00,FU1,zeta,z@zeta.io,S,SENT,,me@college.ac.in\n',
  [`${WS}/rounds/2026-10-22-yc/_research_a.tsv`]:
    'acme\tAcme\tYC-W25\tGREEN\tpay\tto\tPASS\n' +
    'bad\tBad\t-\t-\t-\t-\tFAIL G2 RED registry hold\n' +
    'who\tWho\t-\t-\t-\t-\tNEED-REVEAL\tJane\tCTO\n',
  [`${WS}/rounds/2026-10-22-yc/acme/email.txt`]: 'TO: a@acme.ai\nBODY:\nHi',
}
const DIRS: Record<string, { name: string; kind: 'file' | 'dir' }[]> = {
  [`${WS}/rounds`]: [{ name: '2026-10-21-old', kind: 'dir' }, { name: '2026-10-22-yc', kind: 'dir' }],
  [`${WS}/rounds/2026-10-22-yc`]: [
    { name: '_research_a.tsv', kind: 'file' },
    { name: 'acme', kind: 'dir' },
    { name: 'SPEC.md', kind: 'file' },
  ],
}

const PANE = {
  plugin: 'outreach-hud',
  component: 'Pane',
  requestId: 'outreach-hud',
  surface: 'terminal',
  props: {
    title: 'Outreach',
    isFocused: false,
    bodyColumns: 48,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
} as const

test('the panel shows today, follow-ups, the latest round and all-time numbers', async ($, on) => {
  on('command.register', () => ({ value: { command: 'outreach' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('env.get', (_, e) => ({ value: e.name === 'HOME' ? '/home/u' : undefined }))
  on('clock.now', () => ({ value: NOW }))
  on('clock.every', () => ({ value: undefined }))
  on('fs.exists', (_, e) => ({ value: e.path in FILES || e.path in DIRS }))
  on('fs.read', (_, e) => ({ value: FILES[e.path] ?? '' }))
  on('fs.list', (_, e) =>
    ({ value: (DIRS[e.path] ?? []).map(d => ({ ...d, size: 0, mtimeMs: 0, isLink: false })) }))

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await new Promise(r => (globalThis as unknown as { setTimeout: (f: () => void, ms: number) => void }).setTimeout(() => r(undefined), 50))

  const ui = await $.ui.mount(PANE)
  const text = async (re: RegExp) => (await ui.find({ type: 'Text', text: re }))?.text

  // details are hidden until the skill loads or /outreach runs: only the Today card
  expect(await text(/me@college/)).toContain('me@college.ac.in')
  expect(await text(/New emails/)).toContain('2 / 30-40')           // 2 new emails today
  expect(await text(/Pause:/)).toContain('Pause: over 3% bounced')    // 1 of 2 bounced
  expect(await text(/Follow-ups/)).toContain('1 sent today')          // one follow-up today
  expect(await text(/All time/)).toContain('1 bounced (25.0%)')       // 1 of 4 all time
  expect(await text(/Replies/)).toContain('1 (25.0% of emails)')
  expect(await text(/Last 7 days/)).toBeUndefined()
  await ui.unmount()

  // /outreach shows progress and settings too
  await $.command.run({
    command: 'outreach', args: '', origin: { kind: 'composer' },
    presentation: { isFullscreen: true, columns: 120 },
  })
  const full = await $.ui.mount(PANE)
  const ftext = async (re: RegExp) => (await full.find({ type: 'Text', text: re }))?.text
  expect(await ftext(/Last 7 days/)).toContain('Last 7 days')
  expect(await ftext(/This round/)).toContain('1 found · 1 skipped · 1 need a contact')
  expect(await ftext(/Your settings/)).toContain('Your settings')
  expect(await ftext(/Per day/)).toContain('30-40 new emails · pause at 3%')
  expect(await ftext(/Thu 22/)).toContain('Thu 22')
  await full.unmount()
})
