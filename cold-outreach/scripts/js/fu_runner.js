// In-thread follow-up runner for Gmail web. mkfu.py prepends:
//   const MODE ('dry'|'send'), ME (sending address), ITEMS [{slug,to,subject,role,text?}], TEXT (body with {role}),
//         SIGN (sign-off block), OWN_COUNT (messages from ME expected already in the thread: 1 for FU1, 2 for FU2)
// MODE 'dry' types the reply then discards it. Runs in the page in the background; poll window.__fu.results.
(() => {
  const sl = ms => new Promise(r => setTimeout(r, ms));
  const vis = el => el && el.offsetParent !== null;
  const waitFor = async (fn, ms = 15000) => {
    const t = Date.now();
    while (Date.now() - t < ms) { const v = fn(); if (v) return v; await sl(300); }
    return null;
  };
  const click = el => ['mousedown', 'mouseup', 'click'].forEach(t =>
    el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true, view: window })));
  const st = window.__fu = window.__fu || { results: [], running: false };
  if (st.running) return 'already running';
  st.running = true; st.stop = false;
  const me = ME.toLowerCase();

  // An item may carry its own `text` (a thread with no named role); otherwise TEXT with {role} filled.
  const body = (greet, role, text) => {
    const r = /\brole\b/i.test(role) ? role : role + ' role';
    return `${greet}\n\n${(text || TEXT).replaceAll('{role}', r)}\n\n${SIGN}`;
  };

  const one = async it => {
    if (!document.title.toLowerCase().includes(me)) return 'WRONG_ACCOUNT';
    // leave any open thread first so stale rows from the previous search can't be clicked
    location.hash = '#sent';
    await sl(1500);
    const stale = new Set(document.querySelectorAll('tr.zA'));
    location.hash = '#search/' + encodeURIComponent(`in:sent to:${it.to}`);
    await sl(2500);
    const key = it.subject.replace(/^Re:\s*/i, '').slice(0, 25).toLowerCase();
    const row = await waitFor(() => [...document.querySelectorAll('tr.zA')]
      .filter(tr => vis(tr) && !stale.has(tr)).find(tr => (tr.innerText || '').toLowerCase().includes(key)));
    if (!row) return 'NO_THREAD';
    click(row);
    const hdr = await waitFor(() => [...document.querySelectorAll('h2.hP')].find(vis));
    if (!hdr) return 'THREAD_NOT_OPEN';
    await sl(800);
    const rcpt = await waitFor(() => [...document.querySelectorAll('span[email]')]
      .find(s => vis(s) && s.getAttribute('email').toLowerCase() === it.to.toLowerCase()), 5000);
    if (!rcpt) return 'WRONG_THREAD';
    // sender spans: gD on expanded messages, zF/yP on collapsed ones
    const senders = [...document.querySelectorAll('span.gD[email], span.zF[email], span.yP[email]')]
      .filter(vis).map(s => s.getAttribute('email').toLowerCase());
    const others = [...new Set(senders)].filter(e => e !== me);
    if (others.length) return 'HAS_REPLY:' + others.join(',');
    const mine = senders.filter(e => e === me).length;
    if (mine > OWN_COUNT) return 'ALREADY_FU(' + mine + ')';
    if (mine < OWN_COUNT) return 'MISSING_EARLIER(' + mine + ')';
    const txt = ([...document.querySelectorAll('div.a3s')].find(vis) || {}).innerText || '';
    const m = txt.match(/^\s*((?:Hi|Hello|Dear|Hey)\b[^,\n]{0,40},)/);
    const greet = m ? m[1] : 'Hi,';
    const rep = await waitFor(() => [...document.querySelectorAll('span.ams.bkH')].find(vis));
    if (!rep) return 'NO_REPLY_BTN';
    click(rep);
    const ed = await waitFor(() => [...document.querySelectorAll('div[aria-label="Message Body"][contenteditable="true"]')].find(vis));
    if (!ed) return 'NO_EDITOR';
    ed.focus();
    await sl(300);
    document.execCommand('insertText', false, body(greet, it.role, it.text));
    await sl(600);
    if ((ed.innerText || '').length < 150) return 'BODY_SHORT';
    if (MODE === 'dry') {
      st.preview = ed.innerText.slice(0, 600);
      const disc = [...document.querySelectorAll('div[role=button][data-tooltip^="Discard"]')].find(vis);
      if (disc) click(disc);
      return 'DRY_OK greet=' + greet;
    }
    const send = [...document.querySelectorAll('div[role=button][data-tooltip^="Send"]')].find(vis);
    if (!send) return 'NO_SEND_BTN';
    click(send);
    const ok = await waitFor(() => [...document.querySelectorAll('span.bAq, div.vh')]
      .some(s => /Message sent/i.test(s.innerText || '')), 12000);
    return ok ? 'SENT greet=' + greet : 'NO_TOAST';
  };

  (async () => {
    for (const it of ITEMS) {
      if (st.stop) break;
      let res;
      try { res = await one(it); } catch (e) { res = 'ERR ' + e.message; }
      st.results.push({ to: it.to, slug: it.slug, res, at: new Date().toTimeString().slice(0, 8) });
      try { localStorage.fu_results = JSON.stringify(st.results); } catch (e) {}
      if (res === 'WRONG_ACCOUNT') break;
      await sl(MODE === 'dry' ? 1500 : 8000 + Math.random() * 7000);
    }
    st.running = false;
  })();
  return 'started ' + ITEMS.length + ' (' + MODE + ')';
})();
