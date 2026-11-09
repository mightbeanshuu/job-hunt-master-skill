// Guarded send for a Gmail full-page compose opened from a view=cm deeplink.
// Placeholders filled by mkjs.py: __EXPECT__ (recipient), __OWN__ (regex of the user's own domain), __MINBODY__.
// Returns SENT | NO_TOAST | ABORT {bl, uniq}. Never clicks Send unless the body and the single recipient check out.
await (async () => {
  const EXPECT = "__EXPECT__", OWN = new RegExp("__OWN__", "i"), MINBODY = __MINBODY__;
  const sl = ms => new Promise(r => setTimeout(r, ms));
  let btn;
  for (let i = 0; i < 40; i++) { btn = document.querySelector('div[role=button][data-tooltip^="Send"]'); if (btn) break; await sl(400); }
  await sl(1200);
  const body = document.querySelector('div[aria-label="Message Body"][contenteditable=true]');
  const uniq = [...new Set([...document.querySelectorAll('[data-hovercard-id]')]
    .map(e => e.getAttribute('data-hovercard-id')).filter(x => x.includes('@') && !OWN.test(x)))];
  const bl = body ? body.innerText.length : 0;
  if (!btn || bl < MINBODY || uniq.length !== 1 || uniq[0].toLowerCase() !== EXPECT.toLowerCase())
    return JSON.stringify({ res: 'ABORT', btn: !!btn, bl, uniq });
  btn.click();
  let ok = false;
  for (let i = 0; i < 60; i++) {
    await sl(500);
    const sa = [...document.querySelectorAll('button,div[role=button]')].find(b => /^Send anyway$/i.test(b.innerText.trim()));
    if (sa) sa.click();
    if (/Message sent/i.test([...document.querySelectorAll('span.bAq,div.vh')].map(e => e.innerText).join('|'))) { ok = true; break; }
  }
  await sl(1500);
  // Gmail re-opens a compose prefilled from the URL after sending; discard it so navigating away can't raise "Leave site?".
  let disc = false;
  const d = document.querySelector('div[role=button][data-tooltip^="Discard"]');
  if (ok && d) {
    const b2 = document.querySelector('div[aria-label="Message Body"][contenteditable=true]');
    if (b2 && b2.innerText.length > MINBODY / 2) { d.click(); disc = true; }
  }
  return JSON.stringify({ res: ok ? 'SENT' : 'NO_TOAST', to: EXPECT, disc });
})()
