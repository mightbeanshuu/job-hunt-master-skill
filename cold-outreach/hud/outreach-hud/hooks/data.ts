import type { Day, Round, Setting, Snapshot } from '../types'

// Pure parsing of the cold-outreach workspace files; the same numbers scripts/stats.py prints.

export type Files = {
  workspace: string
  profile: string
  sendLog: string
  fuLog: string
  round: { name: string; tsvs: string[]; drafts: number } | null
}

export function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = []
  let row: string[] = []
  let cell = ''
  let quoted = false
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++ }
      else if (ch === '"') quoted = false
      else cell += ch
    } else if (ch === '"') quoted = true
    else if (ch === ',') { row.push(cell); cell = '' }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++
      row.push(cell); cell = ''
      if (row.some(c => c !== '')) rows.push(row)
      row = []
    } else cell += ch
  }
  if (cell !== '' || row.length) { row.push(cell); rows.push(row) }
  const [head, ...body] = rows
  if (!head) return []
  return body.map(r => Object.fromEntries(head.map((h, i) => [h.trim(), r[i] ?? ''])))
}

// A small TOML reader: [sections], key = "string" | number | bool | ["array", ...] (arrays may span lines).
// Triple-quoted strings (follow-up templates) are skipped; the panel doesn't show them.
export type Toml = Record<string, Record<string, string | number | boolean | string[]>>

export function parseToml(text: string): Toml {
  const out: Toml = { '': {} }
  let sec = ''
  const lines = text.split('\n')
  for (let i = 0; i < lines.length; i++) {
    const line = (lines[i] ?? '').replace(/\s+#[^"]*$/, '').trim()
    if (!line || line.startsWith('#')) continue
    const head = line.match(/^\[([^\]]+)\]$/)
    if (head) { sec = head[1] ?? ''; out[sec] ??= {}; continue }
    const kv = line.match(/^([A-Za-z0-9_]+)\s*=\s*(.*)$/)
    if (!kv) continue
    const key = kv[1] ?? ''
    let val = kv[2] ?? ''
    if (val.startsWith('"""')) {
      while (!val.slice(3).includes('"""') && i + 1 < lines.length) val += '\n' + (lines[++i] ?? '')
      continue
    }
    if (val.startsWith('[')) {
      while (!/\]\s*$/.test(val) && i + 1 < lines.length) val += ' ' + (lines[++i] ?? '').replace(/\s+#[^"]*$/, '').trim()
      const items = [...val.matchAll(/"((?:[^"\\]|\\.)*)"/g)].map(m => (m[1] ?? '').replace(/\\"/g, '"'))
      ;(out[sec] ??= {})[key] = items
      continue
    }
    const str = val.match(/^"((?:[^"\\]|\\.)*)"/)
    const v = str ? (str[1] ?? '') : val === 'true' ? true : val === 'false' ? false : Number.isNaN(Number(val)) ? val : Number(val)
    ;(out[sec] ??= {})[key] = v
  }
  return out
}

function get(t: Toml, sec: string, key: string): string | number | boolean | string[] | undefined {
  return t[sec]?.[key]
}

function tomlValue(text: string, key: string): string | undefined {
  const m = text.match(new RegExp(`^\\s*${key}\\s*=\\s*("([^"]*)"|[^#\\n]+)`, 'm'))
  if (!m) return undefined
  return (m[2] ?? m[1] ?? '').trim()
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function month(v: unknown): string {
  const m = String(v ?? '').match(/^(\d{4})-(\d{2})/)
  if (!m) return String(v ?? '?')
  return `${MONTHS[Number(m[2]) - 1] ?? m[2]} ${m[1]}`
}

function money(n: unknown, currency: unknown): string {
  const v = Number(n ?? 0)
  if (String(currency ?? 'INR') === 'INR') return v >= 1000 ? `₹${Math.round(v / 1000)}k` : `₹${v}`
  return `${v} ${currency}`
}

const FUNDING: Record<string, string> = {
  yc: 'YC', vc: 'VC-funded', angel: 'angel-funded', bootstrapped: 'bootstrapped', 'govt/grant': 'grant-funded',
}
const TOOL: Record<string, string> = { contactout: 'ContactOut', signalhire: 'SignalHire' }

// Plain-language summary of profile.toml, one line per setting.
export function settings(text: string): Setting[] {
  if (!text.trim()) return [{ label: 'Setup', value: 'not done yet: load the skill to set it up' }]
  const t = parseToml(text)
  const arr = (sec: string, key: string) => {
    const v = get(t, sec, key)
    return Array.isArray(v) ? v : []
  }
  const resumes = t.resumes ?? {}
  const links = Object.values(resumes).filter(v => typeof v === 'string' && v.startsWith('http')).length
  const tools = arr('tools', 'paid_contact_tools').map(x => TOOL[x] ?? x)
  const intern = String(get(t, 'eligibility', 'intern_available_from') ?? 'now')
  return [
    { label: 'Graduating', value: `${get(t, 'identity', 'grad_year') ?? '?'} · ${get(t, 'identity', 'degree') ?? ''} · ${get(t, 'identity', 'college_short') ?? get(t, 'identity', 'college') ?? ''}` },
    { label: 'Resume', value: `${links} saved link${links === 1 ? '' : 's'}${resumes.source_html ? ' · tailored per company' : ''}` },
    { label: 'Experience', value: `${get(t, 'eligibility', 'exp_min_years') ?? 0}-${get(t, 'eligibility', 'exp_max_years') ?? 3} yrs · intern ${intern === 'now' ? 'now' : 'from ' + month(intern)} · full-time ${month(get(t, 'eligibility', 'fulltime_join_from'))}` },
    { label: 'Roles', value: arr('targets', 'role_types').join(', ') },
    { label: 'Where', value: arr('targets', 'locations').join(', ') },
    { label: 'Companies', value: arr('targets', 'funding_filter').map(f => FUNDING[f] ?? f).join(', ') || 'any real startup' },
    { label: 'Min pay', value: `${money(get(t, 'pay', 'intern_stipend_min'), get(t, 'pay', 'currency'))}/month intern · ${get(t, 'pay', 'fulltime_min_lpa') ?? '?'} LPA full-time` },
    { label: 'Contacts', value: ['website', 'GitHub', ...tools].join(' → ') + (tools.length ? ` · ${get(t, 'tools', 'reveal_budget_per_round') ?? 10} lookups/round` : '') },
    { label: 'Per day', value: `${get(t, 'sending', 'daily_min') ?? '?'}-${get(t, 'sending', 'daily_cap') ?? '?'} new emails · pause at ${get(t, 'sending', 'bounce_stop_pct') ?? 3}% bounces` },
    { label: 'About you', value: `${arr('pitch', 'hr_bullets').length} achievements · ${arr('pitch', 'eng_facts').length} projects` },
    { label: 'Skipping', value: `${arr('targets', 'never_contact').length} never contact · ${arr('targets', 'live_threads').length} already talking` },
  ]
}

export function localDay(ms: number, offsetDays = 0): string {
  const d = new Date(ms + offsetDays * 86400000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function isBounced(r: Record<string, string>): boolean {
  const o = (r.outcome ?? '').toUpperCase()
  return o.includes('BOUNCE') || o.includes('REJECT')
}

export function parseRound(name: string, tsvs: string[], drafts: number): Round {
  let pass = 0, fail = 0, reveal = 0, apply = 0
  const reasons = new Map<string, number>()
  for (const t of tsvs) {
    for (const line of t.split('\n')) {
      const cells = line.split('\t').map(c => c.trim()).filter(Boolean)
      if (!cells.length) continue
      const last = cells[cells.length - 1] ?? ''
      if (cells.includes('NEED-REVEAL')) reveal++
      else if (last.startsWith('PASS')) pass++
      else if (last.startsWith('APPLY-LINK')) apply++
      else if (last.startsWith('FAIL')) {
        fail++
        const why = last.replace(/^FAIL\s*/, '').slice(0, 40)
        reasons.set(why, (reasons.get(why) ?? 0) + 1)
      }
    }
  }
  const top = [...reasons.entries()].sort((a, b) => b[1] - a[1])[0]
  return { name, pass, fail, reveal, apply, drafts, topFail: top ? `${top[0]} ×${top[1]}` : '' }
}

// Same rules as followups_due() in the skill's scripts/common.py, so the panel's "due" is what would go out.
const GENERIC = new RegExp('^(careers?|jobs?|hr|hiring|hire|hireme|talent\\w*|recruit\\w*|ta|ta[-_.]?team|hello|hi|hey|info|' +
  'contact\\w*|connect|intouch|reach\\w*|team|work|people\\w*|human\\w*|makers?|founders?|ceo|' +
  'support|admin|joinus|namaste|corp|engineering|tech|apply|resumes?|cv|internships?|' +
  'freshers?|opportunit\\w*|office|mail|enquir\\w*|inquir\\w*)(\\+.*)?$', 'i')

export function dueCount(rows: Record<string, string>[], stage: 'FU1' | 'FU2', today: string,
  skip: string[], skipGeneric: boolean, windowDays = 10): number {
  const col = stage === 'FU1' ? 'followup1_due' : 'followup2_due'
  const floor = localDay(new Date(`${today}T12:00:00`).getTime(), -windowDays)
  const seen = new Set<string>()
  let n = 0
  for (const r of rows) {
    const o = (r.outcome ?? '').toUpperCase()
    const em = (r.email ?? '').trim().toLowerCase()
    const at = r[col] ?? ''
    if (!at || at > today || !em || at < floor || seen.has(em)) continue
    if (isBounced(r) || (r.reply ?? '').trim()) continue
    if (skip.some(x => (r.company ?? '').toLowerCase().startsWith(x))) continue
    if (o.includes(stage) || (stage === 'FU2' && !o.includes('FU1'))) continue
    if (skipGeneric && GENERIC.test(em.split('@')[0] ?? '')) continue
    seen.add(em)
    n++
  }
  return n
}

export function snapshot(f: Files, now: number, tick: number): Snapshot {
  const rows = parseCsv(f.sendLog)
  const fus = parseCsv(f.fuLog)
  const hi = Number(tomlValue(f.profile, 'daily_cap') ?? 40)
  const lo = Math.min(hi, Number(tomlValue(f.profile, 'daily_min') ?? Math.round(hi * 0.75)))
  const today = localDay(now)
  const day = rows.filter(r => r.date_sent === today)
  const prof = parseToml(f.profile)
  const listOf = (sec: string, key: string) => {
    const v = prof[sec]?.[key]
    return Array.isArray(v) ? v.map(x => x.toLowerCase()) : []
  }
  const skip = [...listOf('targets', 'live_threads'), ...listOf('targets', 'never_contact')]
  const skipGeneric = prof.followup?.skip_generic_inboxes !== false
  const due = (stage: 'FU1' | 'FU2') => dueCount(rows, stage, today, skip, skipGeneric)
  const days: Day[] = []
  for (let i = 6; i >= 0; i--) {
    const d = localDay(now, -i)
    const dt = new Date(now - i * 86400000)
    days.push({
      label: `${DOW[dt.getDay()]} ${String(dt.getDate()).padStart(2, '0')}`,
      sent: rows.filter(r => r.date_sent === d).length,
      fu: fus.filter(r => r.date === d && r.result === 'SENT').length,
      bounced: rows.filter(r => r.date_sent === d && isBounced(r)).length,
    })
  }
  return {
    updatedAt: now,
    tick,
    workspace: f.workspace,
    sender: tomlValue(f.profile, 'gmail_address') ?? '(no sender set)',
    lo,
    hi,
    stopPct: Number(tomlValue(f.profile, 'bounce_stop_pct') ?? 3),
    todaySent: day.length,
    todayBounced: day.filter(isBounced).length,
    todayFu: fus.filter(r => r.date === today && r.result === 'SENT').length,
    dueFu1: due('FU1'),
    dueFu2: due('FU2'),
    replies: rows.filter(r => (r.reply ?? '').trim()).length,
    allSent: rows.length,
    allBounced: rows.filter(isBounced).length,
    allFu: fus.filter(r => r.result === 'SENT').length,
    days,
    round: f.round ? parseRound(f.round.name, f.round.tsvs, f.round.drafts) : null,
    settings: settings(f.profile),
    error: null,
  }
}
