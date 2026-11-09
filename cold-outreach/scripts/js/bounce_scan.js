// Run on a Gmail search results page (e.g. #search/from%3Amailer-daemon+newer_than%3A1d).
// Opens rows __START__ .. __START__+__COUNT__-1, extracts the undeliverable address(es), goes back.
// Keep __COUNT__ <= 6 so one call stays under the tool timeout. Output strips ?&= so the tool result isn't blocked.
await (async () => {
  const START = __START__, COUNT = __COUNT__;
  const sl = ms => new Promise(r => setTimeout(r, ms));
  const vis = e => e && e.offsetParent !== null;
  const rows0 = [...document.querySelectorAll('tr.zA')].filter(vis);
  const out = [];
  for (let i = START; i < Math.min(rows0.length, START + COUNT); i++) {
    const rows = [...document.querySelectorAll('tr.zA')].filter(vis);
    const r = rows[i]; if (!r) break;
    const when = (r.querySelector('td.xW span') || {}).title || '';
    r.click(); await sl(2600);
    const t = (document.querySelector('div[role=main]') || document.body).innerText;
    const pats = [/delivered to\s+([^\s]+@[^\s]+)/gi, /couldn't be delivered to\s+([^\s]+@[^\s]+)/gi,
                  /address\s+([^\s]+@[^\s]+)\s+(?:couldn't|could not|wasn't)/gi, /Original-Recipient:\s*rfc822;\s*([^\s]+@[^\s]+)/gi,
                  /Final-Recipient:\s*rfc822;\s*([^\s]+@[^\s]+)/gi];
    const addrs = [...new Set(pats.flatMap(p => [...t.matchAll(p)].map(m => m[1].replace(/[.,;:)>\]]+$/, '').toLowerCase())))];
    const why = /blocks outside senders|group/i.test(t) ? 'GROUP_REJECT' : /not found|does not exist|no such user|unknown user|5\.1\.1/i.test(t) ? 'NOT_FOUND' : 'OTHER';
    out.push({ i, when, addrs, why });
    history.back(); await sl(2000);
  }
  return JSON.stringify({ total: rows0.length, out }).replace(/[?&=]/g, ' ');
})()
