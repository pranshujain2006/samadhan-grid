/* SAMADHAN GRID - simple mode
   Same engine underneath. Plain words, big steps, pictures on top. */

import { heroArt, stepIcon, roleArt, emptyArt, ui, helplineArt } from './illus.js';

const S = { cfg: null, view: 'home', sel: {}, cache: {}, evidence: [], rec: null,
            map: null, carry: {}, sortBy: 'recent' };
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = t => String(t ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const num = n => (n ?? 0).toLocaleString('en-IN');
const inr = n => '₹' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
const cap = s => String(s || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
const when = d => d ? new Date(d).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';

const BAND = { critical: 'red', high: 'amber', medium: 'blue', low: 'teal' };
/* Anything filed in the last 6 hours is flagged, so a new report is never "lost". */
const isNew = d => d && (Date.now() - new Date(d).getTime()) < 6 * 3600 * 1000;
const newBadge = d => isNew(d) ? '<span class="tag newtag">JUST ADDED</span>' : '';
const BAND_WORD = { critical: 'Very urgent', high: 'Urgent', medium: 'Important', low: 'Can wait' };
const VERDICT_WORD = {
  likely_duplicate: 'Same problem, different words',
  related: 'Closely related',
  possible_constellation: 'Might share a cause'
};
const VERDICT = { likely_duplicate: 'red', related: 'amber', possible_constellation: 'purple' };
const STATE_COLOR = {
  unresolved: '#b23a34', research: '#5b4b9c', prototype: '#1668c4',
  field_pilot: '#b9740d', deployed: '#2f7a45', rejected: '#9aa7b8'
};

async function api(path, opts = {}) {
  const r = await fetch(path, {
    ...opts,
    headers: opts.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' }
  });
  const txt = await r.text();
  let data; try { data = JSON.parse(txt); } catch { data = { detail: txt }; }
  if (!r.ok) {
    const d = data.detail;
    throw new Error(typeof d === 'string' ? d : (d?.message || JSON.stringify(d)));
  }
  return data;
}
function toast(msg, kind = '') {
  $$('.toast').forEach(t => t.remove());
  const t = document.createElement('div');
  t.className = 'toast ' + kind; t.innerHTML = msg; document.body.appendChild(t);
  setTimeout(() => t.remove(), 5600);
}
const busy = (el, txt) => { el.disabled = true; el._t = el.innerHTML; el.innerHTML = `<span class="spin"></span> ${txt}`; };
const done = el => { el.disabled = false; el.innerHTML = el._t; };
const blank = (kind, title, body) =>
  `<div class="empty">${emptyArt(kind)}<b>${esc(title)}</b>${esc(body)}</div>`;
const say = (text, kind = '', icon = 'eye') =>
  `<div class="explain ${kind}">${ui(icon)}<div>${text}</div></div>`;


/* ---- workflow helpers: always show where you are and what comes next ---- */
const STEPS = [
  ['report', 'Report'], ['review', 'Check'], ['connect', 'Connect'],
  ['team', 'Find team'], ['work', 'Do work'], ['proof', 'See proof'],
];
const NEXT = {
  report: ['review', 'An officer now checks your report', 'They see the AI reasoning and decide if it is real.'],
  review: ['connect', 'Now look for hidden patterns', 'Several approved reports may share one single cause.'],
  connect: ['team', 'Now find who can fix it', 'We rank colleges and partners, and explain every score.'],
  team: ['work', 'Now the work begins', 'Check old answers first, then build and test it in a real village.'],
  work: ['proof', 'Finally, prove it worked', 'Compare with day-one numbers and hear the village verdict.'],
  proof: ['story', 'See one full story', 'Follow a single real problem through all six steps.'],
};

function ribbon(cur) {
  const i = STEPS.findIndex(s => s[0] === cur);
  return `<div class="ribbon">${STEPS.map(([v, t], n) => `
    <a data-v2="${v}" class="${n < i ? 'past' : n === i ? 'now' : ''}">
      <span class="rn">${n < i ? '&#10003;' : n + 1}</span><span class="rt">${esc(t)}</span></a>`).join('')}</div>`;
}
function nextStep(cur) {
  const n = NEXT[cur]; if (!n) return '';
  const [v, title, sub] = n;
  return `<div class="next"><div class="nt"><b>Next: ${esc(title)}</b><span>${esc(sub)}</span></div>
    <button class="btn" data-v2="${v}">Go there ${ui('arrow')}</button></div>`;
}
const bindNav2 = () => $$('[data-v2]').forEach(el => el.onclick = () => go(el.dataset.v2));

/* ============================================================== 0. HOME */
const JOURNEY = [
  ['speak', 'Speak Up', 'A villager tells us what is wrong. By voice, photo or text. In their own language.', 'report'],
  ['check', 'Check It', 'An officer confirms it is real. The AI only suggests — people always decide.', 'review'],
  ['link', 'Connect the Dots', 'Many small reports often share one big cause. We find it.', 'connect'],
  ['team', 'Find the Team', 'AI picks the right college, startup, NGO and funder — and says why.', 'team'],
  ['build', 'Do the Work', 'Check old answers first. Then build it and test it in a real village.', 'work'],
  ['proof', 'Prove It Worked', 'The village says if life improved. We compare with day-one numbers.', 'proof'],
];

const ROLES = [
  ['citizen', 'I have a problem', 'Report what is wrong in your village or ward. Takes two minutes.', 'report'],
  ['officer', 'I am a government officer', 'Check reports, spot patterns and decide what gets solved.', 'review'],
  ['college', 'I am from a college', 'See real problems your students and labs can actually solve.', 'team'],
  ['company', 'I am from a company or NGO', 'Offer sensors, funding, manufacturing, mentors or field reach.', 'team'],
];

async function viewHome() {
  let d = null;
  try { d = await api('/api/dashboard'); } catch { /* fine on a cold start */ }
  const im = d?.impact, c = d?.challenges, pr = d?.projects;
  return `
  <div class="hero">
    <div>
      <span class="eyebrow">${ui('pin')} Government of Jharkhand</span>
      <h1>Your problem.<br>Heard. Solved.<br><em>And proved.</em></h1>
      <p>Tell us what is wrong in your village. We find the people who can actually fix it,
         make sure the fix works in the real world, and then <b>you</b> tell us whether your
         life got better.</p>
      <div class="row">
        <button class="btn big" data-go="report">${ui('mic', '#fff')} &nbsp;Report a problem</button>
        <button class="btn big ghost" data-go="story">${ui('eye')} &nbsp;See one full story</button>
      </div>
      <div style="margin-top:16px;font-size:14px;color:var(--body)">
        ${ui('phone')} &nbsp;No internet or smartphone? Call
        <a href="tel:+918959491068" style="font-weight:800;font-size:16px">8959 491 068</a>
        and we will fill the form for you.</div>
    </div>
    <div>${heroArt()}</div>
  </div>

  <div class="sec"><h2>How it works</h2>
    <p>Most systems stop when a complaint is written down. This one keeps going until the
       village confirms the problem is actually gone. Click any step to open it.</p></div>
  <div class="steps-grid">
    ${JOURNEY.map(([ic, t, p, v], i) => `
      <div class="stepc" data-go="${v}">
        <div class="num">${i + 1}</div>
        ${stepIcon[ic]()}
        <h4>${esc(t)}</h4><p>${esc(p)}</p>
        ${i < JOURNEY.length - 1 ? '<div class="arw">&#8250;</div>' : ''}
      </div>`).join('')}
  </div>
  <div class="next" style="margin-top:16px"><div class="nt"><b>Want to see it actually happen?</b>
    <span>Follow one real report from a villager's voice all the way to proven change - six scenes, real data.</span></div>
    <button class="btn" data-go="story">See one full story ${ui('arrow')}</button></div>

  ${d ? `
  <div class="sec"><h2>Right now on the platform</h2>
    <p>Live numbers from the database — nothing here is a mock-up.</p></div>
  <div class="strip">
    <div><div class="v">${num(c.total)}</div><div class="k">problems reported<br>by people</div></div>
    <div><div class="v">${num(pr.total)}</div><div class="k">turned into real<br>projects</div></div>
    <div><div class="v">${num(pr.deployed)}</div><div class="k">solutions working<br>in villages</div></div>
    <div><div class="v">${num(im.beneficiaries)}</div><div class="k">people whose life<br>improved</div></div>
    <div><div class="v">${im.cost_per_beneficiary ? inr(im.cost_per_beneficiary) : '–'}</div>
      <div class="k">spent per person<br>helped</div></div>
  </div>` : ''}

  <div class="sec"><h2>Who are you?</h2>
    <p>Pick the one that sounds like you and we will take you to the right place.</p></div>
  <div class="roles">
    ${ROLES.map(([k, t, p, v]) => `
      <div class="role" data-go="${v}">${roleArt[k]()}
        <h4>${esc(t)}</h4><p>${esc(p)}</p>
        <div class="go">Open ${ui('arrow')}</div></div>`).join('')}
  </div>

  <div class="sec"><h2>Why this is different</h2></div>
  <div class="grid g3">
    <div class="card">${stepIcon.link()}<h3 style="margin-top:12px">We find the real cause</h3>
      <p class="hint">Ten villages reporting dry handpumps, a failed borewell and a lost crop is not ten
         problems. It is usually one. We join them up and fix the cause, not the symptom.</p></div>
    <div class="card">${stepIcon.book()}<h3 style="margin-top:12px">We never repeat a mistake</h3>
      <p class="hint">Failed projects are kept, not hidden. Before any team builds, we show them what was
         already tried here and exactly why it stopped working.</p></div>
    <div class="card">${stepIcon.proof()}<h3 style="margin-top:12px">The village has the final word</h3>
      <p class="hint">A college or company cannot call a project a success. Only the people who reported
         the problem can, measured against numbers agreed before the work started.</p></div>
  </div>`;
}
const bindHome = () => $$('[data-go]').forEach(el => el.onclick = () => go(el.dataset.go));


/* ======================================================= 0b. FULL STORY */
async function viewStory() {
  const st = await api('/api/story');
  if (!st.found) return blank('build', 'No full story yet', st.message);

  const scene = sc => `
    <div class="scene">
      <div class="sn">${stepIcon[sc.icon] ? stepIcon[sc.icon]() : ''}</div>
      <div class="sbody">
        <div class="step-of">STEP ${sc.n} OF 6</div>
        <h3>${esc(sc.title)}</h3>
        <div class="lead">${esc(sc.lead)}</div>
        ${sc.quote ? `<div class="quote">&ldquo;${esc(sc.quote)}&rdquo;</div>` : ''}
        ${sc.body ? `<div class="body">${esc(sc.body)}</div>` : ''}
        ${(sc.reasons || []).length ? `<div class="body"><b>Why the AI said that:</b><ul style="margin:6px 0 0;padding-left:20px;line-height:1.7">
          ${sc.reasons.map(r => `<li>${esc(r)}</li>`).join('')}</ul></div>` : ''}
        ${(sc.members || []).length ? `<table style="margin:6px 0 4px"><tr><th>Who</th><th>Type</th><th>Their job</th></tr>
          ${sc.members.map(m => `<tr><td><b>${esc(m.name)}</b></td><td><span class="tag">${esc(m.kind)}</span></td>
            <td>${esc(m.role)}</td></tr>`).join('')}</table>` : ''}
        ${(sc.failures || []).map(f => say(
          `<b>Tried before and it failed: ${esc(f.title)}</b><br>What went wrong: ${esc(f.why)}<br>
           <i>So this time: ${esc(f.lesson)}</i>`, 'bad', 'warn')).join('')}
        ${(sc.rows || []).length ? `<table style="margin:6px 0 4px"><tr><th>What was measured</th><th>Before</th><th>After</th><th>Change</th></tr>
          ${sc.rows.map(r => `<tr><td>${esc(r.metric)}</td><td>${r.baseline ?? '-'}</td><td><b>${r.current ?? '-'}</b></td>
            <td><span class="tag ${r.verdict === 'improved' ? 'green' : 'red'}">${r.improvement_pct != null ? r.improvement_pct + '% better' : '-'}</span></td></tr>`).join('')}</table>` : ''}
        ${(sc.village || []).length ? `<div style="margin-top:10px"><div class="mono">What the village said</div>
          ${sc.village.map(v => `<div class="item" style="cursor:default;margin-top:6px">
            <div class="t">${esc(v.who)} <span class="tag ${v.verdict === 'fully_resolved' ? 'green' : v.verdict === 'partially_resolved' ? 'amber' : 'red'}">${esc(cap(v.verdict))}</span>
              <span class="tag">${v.rating}/5</span></div>
            <div class="m">${esc(v.comment || '')}</div></div>`).join('')}</div>` : ''}
        ${(sc.facts || []).length ? `<div class="facts">${sc.facts.map(([k, v]) =>
          `<div><div class="fk">${esc(k)}</div><div class="fv">${esc(v || '-')}</div></div>`).join('')}</div>` : ''}
        ${say(esc(sc.note), '', 'eye')}
      </div>
    </div>`;

  return `
  <div class="hero" style="grid-template-columns:1fr;padding:26px 30px">
    <div>
      <span class="eyebrow">${ui('eye')} A real record, not a script</span>
      <h1 style="font-size:29px">${esc(st.title)}</h1>
      <p style="margin-bottom:0">Everything below was read straight out of the database. This is what
        actually happened to one report from ${esc(st.place || 'a village in Jharkhand')} —
        from the moment someone spoke up, to the day the village said their life had changed.</p>
    </div>
  </div>

  <div style="margin-top:24px">${st.scenes.map(scene).join('')}</div>

  <div class="card"><h3>Every action, permanently recorded</h3>
    <div class="hint">This trail cannot be edited or deleted by anyone. It is how a citizen can check
      what really happened to their report.</div>
    <div class="tl">${st.trail.map(e => `<div class="e ${e.role === 'ai' ? 'ai' : e.role === 'citizen' ? 'cit' : 'gov'}">
      <div class="w">${esc(cap(e.event))}</div>
      <div class="d">${esc(e.who)} &middot; ${esc(e.role)} &middot; ${when(e.at)}</div></div>`).join('')}</div>
  </div>

  <div class="next"><div class="nt"><b>That is the whole system</b>
    <span>Six steps, from a voice note to a proven result. Now try it yourself.</span></div>
    <button class="btn" data-v2="report">Report a problem ${ui('arrow')}</button></div>`;
}

/* ============================================================ 1. REPORT */
function viewReport() {
  const langs = Object.entries(S.cfg.languages).map(([k, v]) => `<option value="${k}">${v}</option>`).join('');
  const dists = S.cfg.districts.map(d => `<option>${d}</option>`).join('');
  return `
  <div class="helpline">
    ${helplineArt()}
    <div class="ht"><b>No internet? No smartphone? Just call us.</b>
      <span>Tell us the problem on the phone and we will fill this whole form for you, free.
        You get the same reference number and the same treatment as anyone reporting online.
        You can also walk into your nearest CSC or Panchayat office.</span></div>
    <a class="callbtn" href="tel:+918959491068">${ui('phone', '#0f7d78')} &nbsp;8959 491 068</a>
  </div>
  ${say(`<b>You do not need to know any department name or official words.</b> Just say what is
    happening, where, and who it hurts. Our AI does the paperwork for you.`, '', 'mic')}
  <div class="split">
    <div>
      <div class="q">
        <div class="qh"><div class="qn">1</div><div class="qt">What is the problem?</div></div>
        <div class="qs">Speak in Hindi, English or your own language — or type it.</div>
        <div class="qb">
          <div class="row" style="margin-bottom:10px">
            <button class="btn ghost" id="btnRec">${ui('mic')} &nbsp;Hold a mic? Record instead</button>
            <span class="mono" id="recInfo"></span>
          </div>
          <textarea id="txt" placeholder="Example: गर्मी में हमारे गाँव के चापाकल सूख जाते हैं, औरतों को तीन किलोमीटर दूर पानी लाने जाना पड़ता है"></textarea>
          <select id="lang" style="margin-top:10px"><option value="auto">Language: detect it for me</option>${langs}</select>
        </div>
      </div>

      <div class="q">
        <div class="qh"><div class="qn">2</div><div class="qt">Where is it happening?</div></div>
        <div class="qs">District is enough. More detail helps us send the right team.</div>
        <div class="qb">
          <select id="dist">${dists}</select>
          <div class="row" style="margin-top:10px">
            <button class="btn ghost" id="btnGps">${ui('pin')} &nbsp;Use my location</button>
            <span class="mono" id="gpsInfo">not captured</span>
          </div>
          <button class="moretog" data-more="loc">+ Add block, panchayat and village</button>
          <div class="more" id="more-loc">
            <div class="grid g2">
              <div><label>Block</label><input id="block" placeholder="e.g. Murhu"></div>
              <div><label>Panchayat / ward</label><input id="pan" placeholder="e.g. Murhu"></div>
            </div>
            <label>Village / ward name</label><input id="vil" placeholder="e.g. Hutar">
          </div>
        </div>
      </div>

      <div class="q">
        <div class="qh"><div class="qn">3</div><div class="qt">Any proof? (optional)</div></div>
        <div class="qs">A photo of the broken handpump helps more than a page of writing.</div>
        <div class="qb">
          <input type="file" id="file" multiple>
          <div id="evList" class="row" style="margin-top:10px"></div>
          <button class="moretog" data-more="who">+ Add your name and how you are reporting</button>
          <div class="more" id="more-who">
            <div class="grid g2">
              <div><label>Your name (optional)</label><input id="who" placeholder="Optional"></div>
              <div><label>Reporting through</label><select id="chan">
                <option value="web">Website or app</option>
                <option value="voice">Voice note</option>
                <option value="helpline">Helpline call (operator filling this in)</option>
                <option value="csc_assisted">Helped at a CSC / Panchayat office</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="ivr">Automated phone call (IVR)</option>
              </select></div>
            </div>
          </div>
        </div>
      </div>

      <button class="btn xl" id="btnSubmit">${ui('send', '#fff')} &nbsp;Send my report</button>
    </div>
    <div id="result"></div>
  </div>`;
}

/* ---- the list of everything already sent, newest first ---- */
const STATUS_TAG = {
  'Sent': '', 'Being checked': 'blue', 'Someone will visit': 'amber',
  'Confirmed on the ground': 'teal', 'Others reported it too': 'purple',
  'Approved': 'green', 'Closed': 'red', 'Joined with a bigger report': 'purple',
  'Sent higher up': 'amber', 'Team assigned': 'green', 'Trying it in a village': 'amber',
  'In use': 'green', 'Finished': 'green',
};

async function reportList(highlight) {
  const r = await api('/api/challenges?sort=recent&limit=40');
  if (!r.count) return blank('inbox', 'No reports sent yet',
    'Fill the form on the left and press Send. Your report will show up here straight away.');
  return `<div class="card"><div class="row" style="justify-content:space-between">
      <div><h3>Reports sent so far (${r.count})</h3>
        <div class="hint">Newest first. Click any one to see exactly where it has reached.</div></div>
      <button class="btn sm ghost" id="btnRefresh">Refresh</button></div>
    <div class="list" style="max-height:none">${r.items.map(c => `
      <div class="item ${c.challenge_id === highlight ? 'on' : ''}" data-track="${c.challenge_id}">
        <div class="t">${esc(c.dna.title)}</div>
        <div class="m">
          <span class="tag ${BAND[c.priority.band]}">${esc(BAND_WORD[c.priority.band] || '')}</span>
          <span>${esc(c.location.district)}</span>
          <span class="mono">${esc(c.challenge_id)}</span>
          <span>${when(c.created_at)}</span>
        </div></div>`).join('')}</div></div>`;
}

async function showList(highlight) {
  $('#result').innerHTML = await reportList(highlight);
  $$('#result [data-track]').forEach(el => el.onclick = () => showTrack(el.dataset.track));
  const rf = $('#btnRefresh'); if (rf) rf.onclick = () => showList();
}

async function showTrack(id) {
  $('#result').innerHTML = '<div class="card"><span class="spin dark"></span> Checking...</div>';
  const t = await api(`/api/challenges/${id}/track`);
  $('#result').innerHTML = `
    <div class="card">
      <button class="btn sm ghost" id="btnBack">&larr; All reports</button>
      <h3 style="margin-top:14px">${esc(t.title)}</h3>
      <div class="hint">Reference ${esc(t.challenge_id)} &middot; sent by ${esc(t.reported_by)}
        ${t.place ? '&middot; ' + esc(t.place) : ''} &middot; ${when(t.reported_at)}</div>

      <div style="margin:16px 0 6px"><div class="row" style="justify-content:space-between">
        <span class="tag ${STATUS_TAG[t.status_label] ?? 'blue'}" style="font-size:12.5px;padding:5px 12px">
          ${esc(t.status_label)}</span>
        <span class="mono">${t.progress_pct}% of the way</span></div>
        <div class="bar" style="height:10px;margin-top:8px">
          <i class="${t.progress_pct >= 90 ? 'g' : t.progress_pct >= 60 ? 't' : ''}"
             style="width:${t.progress_pct}%"></i></div></div>
      ${say(`<b>What that means:</b> ${esc(t.status_detail)}`, t.raw_status === 'rejected' ? 'warn' : 'ok',
            t.raw_status === 'rejected' ? 'warn' : 'ok')}
      ${t.also_reported_by ? say(`<b>${t.also_reported_by} other people</b> reported the same problem.
        That makes your case stronger.`, 'ok', 'ok') : ''}
    </div>

    ${t.village_verdicts.length ? `<div class="card"><h3>What the village said</h3>
      ${t.village_verdicts.map(v => `<div class="item" style="cursor:default">
        <div class="t">${esc(v.who)} <span class="tag ${v.verdict === 'fully_resolved' ? 'green' :
          v.verdict === 'partially_resolved' ? 'amber' : 'red'}">${esc(cap(v.verdict))}</span></div>
        <div class="m">${esc(v.comment || '')}</div></div>`).join('')}</div>` : ''}

    <div class="card"><h3>What has happened so far</h3>
      <div class="hint">Nobody can edit or delete this list. It is your proof.</div>
      <div class="tl">${t.history.map(e => `<div class="e ${e.role === 'ai' ? 'ai' : e.role === 'citizen' ? 'cit' : 'gov'}">
        <div class="w">${esc(e.what)}</div>
        <div class="d">${esc(e.who)} &middot; ${when(e.at)}</div></div>`).join('')}</div>
    </div>`;
  $('#btnBack').onclick = () => showList(id);
}

function bindReport() {
  showList();
  $$('.moretog').forEach(b => b.onclick = () => {
    const el = $('#more-' + b.dataset.more);
    el.classList.toggle('open');
    b.textContent = (el.classList.contains('open') ? '− Hide' : '+ Add') + b.textContent.slice(b.textContent.indexOf(' '));
  });

  $('#btnGps').onclick = () => navigator.geolocation?.getCurrentPosition(
    p => { S.gps = { lat: p.coords.latitude, lon: p.coords.longitude }; $('#gpsInfo').textContent = `saved (${S.gps.lat.toFixed(3)}, ${S.gps.lon.toFixed(3)})`; },
    () => toast('Location blocked. We will use the district centre instead.', 'bad'));

  $('#file').onchange = async e => {
    for (const f of e.target.files) {
      const fd = new FormData(); fd.append('file', f);
      try {
        S.evidence.push(await api('/api/challenges/evidence', { method: 'POST', body: fd }));
        $('#evList').innerHTML = S.evidence.map(v => `<span class="tag green">${ui('cam')} ${esc(v.filename)}</span>`).join('');
      } catch (err) { toast('Upload failed: ' + err.message, 'bad'); }
    }
  };

  $('#btnRec').onclick = async () => {
    const b = $('#btnRec');
    if (S.rec) { S.rec.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream); const chunks = [];
      mr.ondataavailable = e => chunks.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop()); S.rec = null;
        busy(b, 'Writing down what you said');
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const fd = new FormData();
        fd.append('file', blob, 'voice.webm'); fd.append('language', $('#lang').value);
        try {
          const r = await api('/api/challenges/transcribe', { method: 'POST', body: fd });
          $('#txt').value = r.text;
          $('#recInfo').textContent = `heard you in ${r.detected_language || 'your language'}`;
          const ef = new FormData(); ef.append('file', blob, 'voice_note.webm');
          S.evidence.push(await api('/api/challenges/evidence', { method: 'POST', body: ef }));
          $('#evList').innerHTML = S.evidence.map(v => `<span class="tag green">${ui('cam')} ${esc(v.filename)}</span>`).join('');
        } catch (err) { toast(err.message, 'bad'); $('#recInfo').textContent = 'could not hear that'; }
        done(b); b.innerHTML = `${ui('mic')} &nbsp;Hold a mic? Record instead`;
      };
      mr.start(); S.rec = mr;
      b.innerHTML = '<span class="rec"></span> Stop and use this';
      $('#recInfo').textContent = 'listening... speak normally';
    } catch { toast('No microphone found. Please type instead.', 'bad'); }
  };

  $('#btnSubmit').onclick = async () => {
    const text = $('#txt').value.trim();
    if (text.length < 8) return toast('Please tell us a little more about the problem.', 'bad');
    const b = $('#btnSubmit'); busy(b, 'AI is reading your report');
    try {
      const ch = await api('/api/challenges', {
        method: 'POST', body: JSON.stringify({
          text, language: $('#lang').value, channel: $('#chan')?.value || 'web',
          reporter_name: $('#who')?.value || null,
          location: {
            district: $('#dist').value, block: $('#block')?.value || null,
            panchayat_or_ulb: $('#pan')?.value || null, village_or_ward: $('#vil')?.value || null,
            lat: S.gps?.lat ?? null, lon: S.gps?.lon ?? null
          },
          evidence_ids: S.evidence.map(e => e.id)
        })
      });
      $('#result').innerHTML = reportResult(ch) +
        `<div class="row" style="margin-top:14px"><button class="btn ghost" id="btnAll">
          ${ui('eye')} &nbsp;See all reports sent so far</button>
         <button class="btn ghost" id="btnTrackThis">Track this report</button></div>`;
      $('#btnAll').onclick = () => showList(ch.challenge_id);
      $('#btnTrackThis').onclick = () => showTrack(ch.challenge_id);
      S.evidence = []; $('#evList').innerHTML = ''; $('#txt').value = '';
      $('#result').scrollIntoView({ behavior: 'smooth', block: 'start' });
      toast(`Sent. Your reference is ${ch.challenge_id}. It is now in the officer queue.`, 'ok');
    } catch (e) { toast(e.message, 'bad'); }
    done(b);
  };
}

function reportResult(ch) {
  const d = ch.dna, p = ch.priority, c = ch.evidence_confidence;
  const dupes = (ch.related || []).filter(r => r.verdict === 'likely_duplicate').length;
  return `
  <div class="result-head">${stepIcon.check()}
    <div><h3>Got it. Here is what we understood.</h3>
      <p>Your reference number is ${esc(ch.challenge_id)} — keep it to check progress.</p></div></div>

  <div class="card">
    <h3>${esc(d.title)}</h3>
    <div class="hint">We rewrote your words into a clear record. Correct us if anything is wrong.</div>
    <div class="row" style="margin-bottom:14px">
      <span class="tag solid">${esc(cap(d.primary_domain))}</span>
      ${(d.secondary_domains || []).map(s => `<span class="tag">${esc(cap(s))}</span>`).join('')}
    </div>
    ${d.summary_local ? say(`<b>In your own language:</b> ${esc(d.summary_local)}`, 'ok', 'ok') : ''}
    <dl class="dna">
      <dt>What is wrong</dt><dd>${esc(d.description)}</dd>
      <dt>Who it hurts</dt><dd>${esc(d.affected_community)}${d.people_affected_estimate ? ` — about ${num(d.people_affected_estimate)} people` : ''}</dd>
      <dt>Hurts most</dt><dd>${(d.vulnerable_groups || []).map(cap).join(', ') || 'not clear yet'}</dd>
      <dt>How often</dt><dd>${esc(cap(d.frequency))}</dd>
      <dt>Likely cause</dt><dd>${(d.suspected_causes || []).join('; ') || 'to be checked'}</dd>
      <dt>Who could fix it</dt><dd>${(d.required_expertise || []).join(', ')}</dd>
      <dt>Which department</dt><dd>${(d.govt_departments || []).join('; ') || '–'}</dd>
    </dl>
  </div>

  <div class="card">
    <h3>How urgent is this? <span class="tag ${BAND[p.band]}">${esc(BAND_WORD[p.band] || p.band)}</span></h3>
    <div class="hint">Score ${p.score} out of 100. Here is exactly how we got there — no hidden maths.</div>
    ${p.factors.map(f => `
      <div class="factor">
        <div class="h"><span>${esc(f.factor)}</span><b>${f.contribution} / ${f.weight}</b></div>
        <div class="bar"><i style="width:${(f.contribution / f.weight * 100).toFixed(0)}%"></i></div>
        <div class="r">${esc(f.reason)}</div>
      </div>`).join('')}
    ${say('<b>An officer decides, not the computer.</b> This score only helps them see which reports need attention first.', 'warn', 'warn')}
  </div>

  <div class="card">
    <h3>How solid is the proof? <span class="tag ${c.level === 'high' ? 'green' : c.level === 'medium' ? 'amber' : 'red'}">${esc(c.level)}</span></h3>
    <div class="hint">${esc(c.guidance)} A low score never means we throw your report away.</div>
    ${c.factors.map(f => `<div class="hbar"><span class="n">${esc(f.factor)}</span>
      <span class="b"><i class="${f.points ? 'g' : 'r'}" style="width:${(f.points / f.max * 100).toFixed(0)}%"></i></span>
      <span class="c">${f.points}</span></div>`).join('')}
  </div>

  ${ch.related?.length ? `<div class="card">
    <h3>${dupes ? `${dupes} other people reported this too` : `${ch.related.length} related report(s) nearby`}</h3>
    <div class="hint">We never delete anyone's report. More people reporting the same thing makes the
      case stronger, not weaker.</div>
    ${ch.related.slice(0, 4).map(r => `
      <div class="item" style="cursor:default">
        <div class="t">${esc(r.title || r.challenge_id)}</div>
        <div class="m"><span class="tag ${VERDICT[r.verdict] || ''}">${esc(VERDICT_WORD[r.verdict] || r.verdict)}</span>
          <span class="mono">${(r.score * 100).toFixed(0)}% alike</span><span>${esc(r.district || '')}</span></div>
      </div>`).join('')}
  </div>` : ''}`;
}

/* ============================================================ 2. REVIEW */
async function viewReview() {
  const q = await api('/api/gov/queue?sort=' + S.sortBy);
  return `
  ${say(`<b>Your job: decide what is real and what matters.</b> The AI has read every report, scored it
     and explained why. You approve, send for a field check, or reject.`, '', 'ok')}
  <div class="split">
    <div><div class="card">
      <div class="row" style="justify-content:space-between;align-items:flex-start">
        <div><h3>Waiting for you (${q.count})</h3>
          <div class="hint">${S.sortBy === 'recent' ? 'Newest first - your latest report is at the top.'
            : 'Most urgent first.'}</div></div>
        <div class="row" style="gap:6px">
          <span class="chip ${S.sortBy === 'recent' ? 'on' : ''}" data-sort="recent">Newest</span>
          <span class="chip ${S.sortBy === 'priority' ? 'on' : ''}" data-sort="priority">Most urgent</span>
        </div></div>
      <div class="list" id="qList">${q.items.map(qItem).join('') ||
        blank('inbox', 'Nothing waiting', 'Click "Load demo" in the sidebar to try it with sample reports.')}</div>
    </div></div>
    <div id="detail">${blank('search', 'Pick a report on the left',
      'You will see what the citizen said, what the AI made of it, and three big buttons to decide.')}</div>
  </div>`;
}
const qItem = c => `<div class="item ${isNew(c.created_at) ? 'fresh' : ''}" data-id="${c.challenge_id}">
  <div class="t">${newBadge(c.created_at)} ${esc(c.dna.title)}</div>
  <div class="m"><span class="tag ${BAND[c.priority.band]}">${esc(BAND_WORD[c.priority.band] || '')}</span>
    <span>${esc(cap(c.dna.primary_domain))}</span><span>${esc(c.location.district)}</span>
    ${c.related?.length ? `<span class="tag purple">${c.related.length} linked</span>` : ''}</div></div>`;

function bindReview() {
  $$('[data-sort]').forEach(el => el.onclick = () => { S.sortBy = el.dataset.sort; go('review'); });
  if (S.carry.challenge_id) {
    const hit = $(`#qList .item[data-id="${S.carry.challenge_id}"]`);
    if (hit) setTimeout(() => hit.click(), 60);
  }
  $$('#qList .item').forEach(el => el.onclick = async () => {
    $$('#qList .item').forEach(x => x.classList.remove('on')); el.classList.add('on');
    const ch = await api('/api/challenges/' + el.dataset.id);
    $('#detail').innerHTML = reviewDetail(ch);
    bindReviewActions(ch);
  });
}

function reviewDetail(ch) {
  const p = ch.priority, c = ch.evidence_confidence, d = ch.dna;
  return `
  <div class="card">
    <h3>${esc(d.title)}</h3>
    <div class="hint">${esc(ch.challenge_id)} · from ${esc(ch.raw.reporter_name || 'an anonymous citizen')}
      · ${esc(ch.raw.channel)} · ${when(ch.created_at)} · <span class="tag">${esc(ch.status)}</span></div>
    ${say(`<b>Short version:</b> ${esc(ch.officer_brief)}`, '', 'eye')}
    <div class="grid g2" style="margin-top:6px">
      <div><div class="mono">What the citizen actually said</div>
        <div style="margin-top:6px;padding:13px;background:var(--line-2);border-radius:10px;font-size:14px;line-height:1.6">${esc(ch.raw.text)}</div></div>
      <div><div class="mono">What the AI understood</div>
        <dl class="dna" style="margin-top:6px">
          <dt>Problem type</dt><dd>${esc(cap(d.primary_domain))}</dd>
          <dt>Who it hurts</dt><dd>${esc(d.affected_community)}</dd>
          <dt>Hurts most</dt><dd>${(d.vulnerable_groups || []).map(cap).join(', ') || '–'}</dd>
          <dt>Skills needed</dt><dd>${(d.required_expertise || []).join(', ')}</dd>
          <dt>Where</dt><dd>${esc([ch.location.village_or_ward, ch.location.block, ch.location.district].filter(Boolean).join(', '))}</dd>
        </dl></div>
    </div>
  </div>

  <div class="card"><h3>Why the AI called it "${esc(BAND_WORD[p.band] || p.band)}" (${p.score}/100)</h3>
    <div class="hint">Every point is traceable. You can disagree with any of it.</div>
    ${p.factors.map(f => `<div class="hbar"><span class="n" title="${esc(f.reason)}">${esc(f.factor)}</span>
      <span class="b"><i style="width:${(f.contribution / f.weight * 100).toFixed(0)}%"></i></span>
      <span class="c">${f.contribution}</span></div>`).join('')}
  </div>

  <div class="card"><h3>Proof on file: ${esc(c.level)}</h3>
    <div class="hint">${esc(c.guidance)}</div>
    <div class="row">${c.factors.map(f => `<span class="tag ${f.points > 0 ? 'green' : ''}">${esc(f.factor)} ${f.points}/${f.max}</span>`).join('')}</div>
    ${ch.evidence?.length ? `<div class="row" style="margin-top:12px">${ch.evidence.map(e =>
    `<a class="tag blue" href="${e.url}" target="_blank">${ui('cam')} ${esc(e.filename)}</a>`).join('')}</div>` : ''}
  </div>

  <div class="card"><h3>Your decision</h3>
    <div class="hint">Nothing happens automatically. This is on you.</div>
    <div class="decide">
      <button class="dbtn ok" data-dec="validated"><b>${ui('ok')} Yes, this is real</b>
        <span>Approve it so a college or company can be assigned.</span></button>
      <button class="dbtn warn" data-dec="field_verification_required"><b>${ui('warn')} Send for a field check</b>
        <span>Someone should go and see it before we spend money.</span></button>
      <button class="dbtn bad" data-dec="rejected"><b>${ui('x')} Not for us</b>
        <span>Not genuine, or better handled by a normal service request.</span></button>
    </div>
    <button class="moretog" data-more="opt">+ Change the urgency or add notes</button>
    <div class="more" id="more-opt">
      <div class="grid g2">
        <div><label>Your name</label><input id="rOff" value="Reviewing Officer"></div>
        <div><label>Set the real urgency (overrides the AI)</label><select id="rPri">
          <option value="">Keep AI's answer (${esc(BAND_WORD[p.band] || p.band)})</option>
          <option value="critical">Very urgent</option><option value="high">Urgent</option>
          <option value="medium">Important</option><option value="low">Can wait</option></select></div>
      </div>
      <label>What kind of case is this?</label>
      <select id="rRoute">${S.cfg.routes.map(r => `<option value="${r}"${r === 'innovation_opportunity' ? ' selected' : ''}>${cap(r)}</option>`).join('')}</select>
      <label>Notes for the record</label><textarea id="rNote" style="min-height:70px" placeholder="What did you check?"></textarea>
    </div>
  </div>

  ${ch.related?.length ? `<div class="card"><h3>Same problem reported by others?</h3>
    <div class="hint">Linking keeps both reports and makes the main one stronger.</div>
    ${ch.related.slice(0, 5).map(r => `
      <div class="item" style="cursor:default"><div class="t">${esc(r.title || r.challenge_id)}</div>
        <div class="m"><span class="tag ${VERDICT[r.verdict] || ''}">${esc(VERDICT_WORD[r.verdict] || r.verdict)}</span>
          <span class="mono">${(r.score * 100).toFixed(0)}% alike</span>
          <button class="btn sm ghost" data-merge="${r.challenge_id}">Link to this one</button></div></div>`).join('')}
  </div>` : ''}

  <div class="card"><h3>Full story so far</h3>
    <div class="hint">Every action, who did it, and when. This can never be edited or deleted.</div>
    <div class="tl">${(ch.ledger || []).map(e => `<div class="e ${e.actor_role === 'ai' ? 'ai' : e.actor_role === 'citizen' ? 'cit' : 'gov'}">
      <div class="w">${esc(cap(e.event))}</div>
      <div class="d">${esc(e.actor)} · ${when(e.at)}</div></div>`).join('')}</div>
  </div>`;
}

function bindReviewActions(ch) {
  $$('.moretog').forEach(b => b.onclick = () => $('#more-' + b.dataset.more).classList.toggle('open'));
  const val = id => $(id)?.value || null;
  $$('#detail [data-dec]').forEach(b => b.onclick = async () => {
    busy(b, 'Saving');
    try {
      await api(`/api/gov/challenges/${ch.challenge_id}/review`, {
        method: 'POST', body: JSON.stringify({
          decision: b.dataset.dec, officer: val('#rOff') || 'Reviewing Officer',
          notes: val('#rNote'), route: val('#rRoute') || 'innovation_opportunity',
          official_priority: val('#rPri')
        })
      });
      toast('Saved. Thank you.', 'ok');
      if (b.dataset.dec === 'validated') {
        S.carry.challenge_id = ch.challenge_id;
        $('#detail').innerHTML = `
          <div class="result-head">${stepIcon.check()}
            <div><h3>Approved. Here is what happens next.</h3>
              <p>"${esc(ch.dna.title)}" is now ready for a team.</p></div></div>
          <div class="card"><h3>Carry this same problem forward</h3>
            <div class="hint">You do not have to go and hunt for it again. These buttons open
              this exact problem at the next step.</div>
            <div class="row">
              <button class="btn big" data-v2="team">Find a team for this one ${ui('arrow', '#fff')}</button>
              <button class="btn ghost" data-v2="connect">Look for a bigger pattern first</button>
              <button class="btn ghost" data-v2="review">Back to the queue</button>
            </div></div>`;
        bindNav2();
      } else {
        go('review');
      }
    } catch (e) { toast(e.message, 'bad'); done(b); }
  });
  $$('#detail [data-merge]').forEach(b => b.onclick = async () => {
    busy(b, '...');
    try {
      await api(`/api/gov/challenges/${ch.challenge_id}/review`, {
        method: 'POST', body: JSON.stringify({
          decision: 'merged', officer: val('#rOff') || 'Reviewing Officer',
          merge_into: b.dataset.merge, notes: 'Linked as extra evidence'
        })
      });
      toast('Linked. The main report is now stronger.', 'ok'); go('review');
    } catch (e) { toast(e.message, 'bad'); done(b); }
  });
}

/* =========================================================== 3. CONNECT */
async function viewConnect() {
  const [cons, miss] = await Promise.all([api('/api/gov/constellations'), api('/api/gov/missions')]);
  return `
  ${say(`<b>Ten villages with dry handpumps is usually not ten problems.</b> It is one problem wearing
     ten masks. This screen finds the single cause behind scattered reports, so the state fixes the
     cause instead of paying for thirty separate patches.`, '', 'eye')}

  <div class="card"><div class="row" style="justify-content:space-between">
    <div><h3>Look for hidden patterns</h3>
      <div class="hint">Compares meaning, distance, timing and problem type across every report.</div></div>
    <button class="btn big" id="btnDetect">Find patterns now</button></div></div>

  <div class="grid g2" style="margin-top:14px">
    <div>${cons.items.length ? cons.items.map(c => `
      <div class="card"><div class="row" style="justify-content:space-between">
        <h3>${esc(c.mission_name || 'Pattern found')}</h3>
        <span class="tag ${c.status === 'mission_created' ? 'green' : 'purple'}">${esc(cap(c.status))}</span></div>
        <div class="hint">${c.report_count} separate reports · ${esc((c.districts || []).join(', '))}
          · AI is ${((c.confidence || 0) * 100).toFixed(0)}% sure</div>
        ${say(`<b>The one real cause:</b> ${esc(c.root_cause_hypothesis)}`, 'warn', 'warn')}
        <div style="margin-top:10px;font-size:13.5px;line-height:1.6">${esc(c.reasoning || '')}</div>
        ${(c.workstreams || []).length ? `<div style="margin-top:14px"><div class="mono">What a fix would need</div>
          ${c.workstreams.map(w => `<div class="item" style="cursor:default"><div class="t">${esc(w.name)}</div>
            <div class="m">${esc(w.why || '')}</div></div>`).join('')}</div>` : ''}
        ${(c.evidence_gaps || []).length ? `<div style="margin-top:12px"><div class="mono">What we still need to measure</div>
          <div class="row" style="margin-top:6px">${c.evidence_gaps.map(g => `<span class="tag amber">${esc(g)}</span>`).join('')}</div></div>` : ''}
        ${c.status !== 'mission_created' ? `<div style="margin-top:14px">
          <label>Name this mission</label><input class="mName" value="${esc(c.mission_name || '')}">
          <label>What must actually change (with a number and a date)</label>
          <textarea class="mOut" style="min-height:64px">${esc(c.mission_outcome || '')}</textarea>
          <div class="row" style="margin-top:12px"><input class="mBud" type="number" placeholder="Budget in ₹" style="width:200px">
            <button class="btn" data-mission="${c.constellation_id}">Start this mission</button></div></div>` : ''}
      </div>`).join('') : blank('search', 'No patterns found yet',
        'A pattern needs at least 3 related reports from nearby places. One new report on its '
        + 'own will not make one - that is correct, not a fault. Add a few more reports from the '
        + 'same area, then press "Find patterns now".')}
    </div>
    <div><div class="card"><h3>Missions running (${miss.count})</h3>
      <div class="hint">A mission funds one measurable result, not thirty disconnected projects.</div>
      ${miss.items.map(m => `<div class="item" style="cursor:default">
        <div class="t">${esc(m.name)}</div>
        <div class="m"><span class="tag green">${esc(m.status)}</span><span>${esc((m.target_districts || []).join(', '))}</span>
          <span class="mono">${m.challenge_ids?.length || 0} reports · ${m.projects?.length || 0} projects</span></div>
        <div style="margin-top:8px;font-size:13.5px;color:var(--ink)"><b>Goal:</b> ${esc(m.outcome_statement)}</div>
        <div class="m" style="margin-top:6px"><span>Budget ${inr(m.budget_envelope)}</span><span>Spent ${inr(m.budget_released)}</span></div>
      </div>`).join('') || blank('build', 'No missions yet', 'Find a pattern first, then turn it into a mission.')}
    </div></div>
  </div>`;
}

function bindConnect() {
  $('#btnDetect').onclick = async () => {
    const btn = $('#btnDetect'); busy(btn, 'AI is looking for the hidden cause');
    try {
      const r = await api('/api/gov/constellations/detect', { method: 'POST' });
      toast(r.detected
        ? `Found ${r.detected} hidden pattern(s).`
        : 'No pattern yet - a pattern needs at least 3 related reports from nearby places.',
        r.detected ? 'ok' : '');
      go('connect');
    } catch (e) { toast(e.message, 'bad'); done(btn); }
  };
  $$('[data-mission]').forEach(b => b.onclick = async () => {
    const card = b.closest('.card'); busy(b, 'Starting');
    try {
      await api('/api/gov/missions', {
        method: 'POST', body: JSON.stringify({
          constellation_id: b.dataset.mission, name: $('.mName', card).value,
          outcome_statement: $('.mOut', card).value,
          budget_envelope: Number($('.mBud', card).value || 0),
          duration_months: 18, created_by: 'District Collector'
        })
      });
      toast('Mission started.', 'ok'); go('connect');
    } catch (e) { toast(e.message, 'bad'); done(b); }
  });
}

/* ============================================================== 4. TEAM */
async function viewTeam() {
  const r = await api('/api/challenges?sort=recent&limit=60');
  const ready = r.items.filter(c => ['validated', 'field_verified', 'community_corroborated'].includes(c.status));
  return `
  ${say(`<b>Who can actually fix this?</b> Not whoever is nearest or shouts loudest. We look at which
     college has the right departments, the right teachers, the right lab, past work on this exact thing,
     and whether they can reach the village. Then we show our reasoning.`, '', 'eye')}
  <div class="split"><div><div class="card"><h3>Approved problems (${ready.length})</h3>
    <div class="hint">Newest first. Only approved problems can be given to a team.</div>
    <div class="list" id="mList">${ready.map(qItem).join('') ||
      blank('inbox', 'Nothing approved yet', 'Go to "Check Reports" and approve one first.')}</div>
  </div></div><div id="mDetail">${blank('search', 'Pick a problem',
    'We will rank the colleges, explain every score, and build the full team.')}</div></div>`;
}

function bindTeam() {
  if (S.carry.challenge_id) {
    const hit = $(`#mList .item[data-id="${S.carry.challenge_id}"]`);
    if (hit) setTimeout(() => hit.click(), 60);
  }
  $$('#mList .item').forEach(el => el.onclick = async () => {
    $$('#mList .item').forEach(x => x.classList.remove('on')); el.classList.add('on');
    $('#mDetail').innerHTML = '<div class="card"><span class="spin dark"></span> Looking through every college, lab and company...</div>';
    const id = el.dataset.id;
    const m = await api(`/api/gov/challenges/${id}/match?explain=true`);
    $('#mDetail').innerHTML = teamDetail(m);
    bindTeamActions(id);
  });
}

function teamDetail(m) {
  const ca = m.consortium_analysis;
  return `
  <div class="card"><h3>Skills this problem needs</h3>
    <div class="row">${m.required_expertise.map(e => `<span class="tag blue">${esc(e)}</span>`).join('')}</div>
    ${say(`<b>Top 3 colleges together cover ${ca.coverage_pct}% of these skills.</b> ${esc(ca.advice)}`,
      ca.still_missing.length ? 'warn' : 'ok', ca.still_missing.length ? 'warn' : 'ok')}
  </div>

  ${m.institutions.map((i, n) => `
  <div class="card">
    <div class="row" style="justify-content:space-between">
      <h3>${n + 1}. ${esc(i.name)}</h3>
      <span class="tag ${i.match_score > 80 ? 'green' : i.match_score > 60 ? 'blue' : ''}">${i.match_score}% fit</span>
    </div>
    <div class="hint">${esc(i.district)}${i.distance_km ? ` · ${i.distance_km} km from the village` : ''}</div>
    ${i.factors.map(f => `<div class="factor"><div class="h"><span>${esc(f.factor)}</span><b>${f.contribution}/${f.weight}</b></div>
      <div class="bar"><i class="${f.contribution / f.weight > .7 ? 'g' : f.contribution / f.weight > .35 ? 'a' : 'r'}" style="width:${(f.contribution / f.weight * 100).toFixed(0)}%"></i></div>
      <div class="r">${esc(f.reason)}</div></div>`).join('')}
    ${i.recommended_faculty?.length ? `<div style="margin-top:12px"><div class="mono">Teachers who could guide it</div>
      <div class="row" style="margin-top:6px">${i.recommended_faculty.map(f =>
      `<span class="tag purple">${esc(f.name)} · ${esc(f.department)}</span>`).join('')}</div></div>` : ''}
    <label style="margin-top:14px"><input type="checkbox" class="pickI" value="${i.institution_id}" style="width:auto"> Pick this college</label>
  </div>`).join('')}

  <div class="card"><h3>Companies, startups, funders and NGOs</h3>
    <div class="hint">Matched to what this project actually needs — not general sponsorship.</div>
    ${m.partners.map(p => `<div class="item" style="cursor:default">
      <div class="t">${esc(p.name)} <span class="tag ${p.fit_score > 60 ? 'green' : ''}">${p.fit_score}% fit</span></div>
      <div class="m"><span class="tag">${esc(p.type)}</span><span>${esc(p.district)}</span></div>
      <div style="margin-top:6px;font-size:13.5px"><b>What they would do:</b> ${esc(p.proposed_role)}</div>
      <div style="margin-top:3px;font-size:12.5px;color:var(--muted)">${esc(p.why)}</div>
      <label style="margin-top:8px"><input type="checkbox" class="pickP" value="${p.partner_id}" style="width:auto"> Include them</label>
    </div>`).join('')}
  </div>

  <div class="card"><h3>Let the AI build the whole team</h3>
    <div class="hint">One college is rarely enough. This adds the startup, the funder, the NGO and the
      Panchayat — with a clear job for each.</div>
    <button class="btn big" id="btnCo">Build the team</button>
    <div id="coOut"></div>
  </div>

  <div class="card"><h3>Hand it over and start work</h3>
    <button class="moretog" data-more="alloc">+ Officer name and how it is being given out</button>
    <div class="more" id="more-alloc">
      <div class="grid g2">
        <div><label>Officer</label><input id="aOff" value="Secretary, Dept."></div>
        <div><label>How</label><select id="aMode">
          <option value="consortium" selected>Several colleges together</option>
          <option value="single">One college</option>
          <option value="invite_proposals">Ask them to send proposals</option>
          <option value="competitive">Let teams compete</option></select></div>
      </div>
      <label>Why this team (goes on the official record)</label><textarea id="aJust" style="min-height:60px"></textarea>
    </div>
    <button class="btn xl ok" id="btnAlloc" style="margin-top:12px">Give this problem to the selected team</button>
  </div>`;
}

function bindTeamActions(id) {
  $$('.moretog').forEach(b => b.onclick = () => $('#more-' + b.dataset.more).classList.toggle('open'));
  $('#btnCo').onclick = async () => {
    const b = $('#btnCo'); busy(b, 'Choosing the right people');
    try {
      const c = await api(`/api/gov/challenges/${id}/coalition`, { method: 'POST' });
      $('#coOut').innerHTML = `
        ${say(`<b>${esc(c.coalition_name)}</b> — led by ${esc(c.lead.member)}. ${esc(c.lead.why_lead)}`, 'ok', 'ok')}
        <table style="margin-top:10px"><tr><th>Who</th><th>Type</th><th>Their job</th></tr>
        ${c.members.map(m => `<tr><td><b>${esc(m.name)}</b><div class="mono">${esc(m.why || '')}</div></td>
          <td><span class="tag">${esc(m.kind)}</span></td><td>${esc(m.role)}</td></tr>`).join('')}</table>
        <div style="margin-top:14px"><div class="mono">Students who would work on it</div>
          <div class="row" style="margin-top:6px">${(c.student_team || []).map(s =>
        `<span class="tag purple">${esc(s.discipline)} ×${s.count}</span>`).join('')}</div></div>
        ${c.risk_note ? say(`<b>Biggest risk:</b> ${esc(c.risk_note)}`, 'bad', 'warn') : ''}
        ${(c.first_90_days || []).length ? `<div style="margin-top:12px"><div class="mono">First three months</div>
          <ul style="margin:8px 0 0;padding-left:20px;font-size:13.5px;line-height:1.7">
          ${c.first_90_days.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : ''}`;
      toast('Team built. You can change it before approving.', 'ok');
    } catch (e) { toast(e.message, 'bad'); }
    done(b);
  };

  $('#btnAlloc').onclick = async () => {
    const inst = $$('.pickI:checked').map(x => x.value);
    if (!inst.length) return toast('Tick at least one college above.', 'bad');
    const b = $('#btnAlloc'); busy(b, 'Setting up the workspace');
    try {
      const p = await api(`/api/gov/challenges/${id}/allocate`, {
        method: 'POST', body: JSON.stringify({
          institution_ids: inst, partner_ids: $$('.pickP:checked').map(x => x.value),
          officer: $('#aOff')?.value || 'Officer', mode: $('#aMode')?.value || 'consortium',
          justification: $('#aJust')?.value || null
        })
      });
      S.carry.project_id = p.project_id;
      S.carry.challenge_id = null;
      toast(`Work has started. Workspace ${p.project_id} is open.`, 'ok');
      go('work');
    } catch (e) { toast(e.message, 'bad'); done(b); }
  };
}

/* ============================================================== 5. WORK */
async function viewWork() {
  const r = await api('/api/projects');
  return `
  ${say(`<b>This is where a promise becomes a working thing.</b> The rules are strict on purpose:
     check old answers before building, no milestone without proof, and no big money until the
     village has agreed what success means.`, '', 'ok')}
  <div class="split"><div><div class="card"><h3>Work in progress (${r.count})</h3>
    <div class="list" id="pList">${r.items.map(p => `<div class="item" data-id="${p.project_id}">
      <div class="t">${esc(p.title)}</div>
      <div class="m"><span class="tag blue">${esc(cap(p.stage))}</span><span>${esc(p.district)}</span>
        ${p.risk.level !== 'low' ? `<span class="tag ${p.risk.level === 'high' ? 'red' : 'amber'}">needs attention</span>` : ''}
        ${p.readiness_summary.scale_ready ? '<span class="tag green">ready to spread</span>' : ''}</div></div>`).join('')
    || blank('build', 'No work started yet', 'Approve a problem and give it to a team first.')}</div>
  </div></div><div id="pDetail">${blank('build', 'Pick a project', 'You will see every step, every rule and every proof.')}</div></div>`;
}
function bindWork() {
  $$('#pList .item').forEach(el => el.onclick = () => openProject(el.dataset.id));
  if (S.carry.project_id) {
    const hit = $(`#pList .item[data-id="${S.carry.project_id}"]`);
    if (hit) { hit.classList.add('on'); openProject(S.carry.project_id); S.carry.project_id = null; }
  }
}

async function openProject(id) {
  $('#pDetail').innerHTML = '<div class="card"><span class="spin dark"></span> Loading...</div>';
  const p = await api('/api/projects/' + id);
  $('#pDetail').innerHTML = projectDetail(p);
  bindProjectActions(p);
}

function projectDetail(p) {
  const r = p.readiness_summary, sm = p.solution_memory_review, ic = p.impact_contract || {}, im = p.impact || {};
  const stages = S.cfg.project_stages;
  const cur = stages.findIndex(s => s.key === p.stage);
  return `
  <div class="card">
    <h3>${esc(p.title)}</h3>
    <div class="hint">Being done by ${esc(p.institutions.map(i => i.name).join(' + '))}${p.partners.length ? ' with ' + esc(p.partners.map(x => x.name).join(', ')) : ''}</div>
    <div class="steps">${stages.map((s, i) => `<div class="step ${i < cur ? 'done' : i === cur ? 'now' : ''}"><b>${esc(s.label)}</b>${i === cur ? 'we are here' : i < cur ? 'done' : ''}</div>`).join('')}</div>
    <div class="row" style="margin-top:10px">
      <select id="nextStage" style="width:240px">${stages.map(s => `<option value="${s.key}"${s.key === p.stage ? ' selected' : ''}>${s.label}</option>`).join('')}</select>
      <button class="btn" id="btnStage">Move to this step</button>
      <label style="margin:0;font-weight:400;font-size:12.5px"><input type="checkbox" id="ovr" style="width:auto"> skip the rule (recorded)</label>
    </div>
  </div>

  ${p.risk.flags.length ? `<div class="card"><h3>Things going wrong</h3>
    ${p.risk.flags.map(f => say(`<b>${esc(f.risk)}</b> — ${esc(f.detail)}<br>What to do: ${esc(f.action)}`,
      f.severity === 'high' ? 'bad' : 'warn', 'warn')).join('')}</div>` : ''}

  <div class="card"><h3>Three questions, not one</h3>
    <div class="hint">A shiny demo is not a solution. We track all three separately.</div>
    <div class="grid g3">
      <div class="gauge"><div class="v">${r.trl}<span style="font-size:14px;color:var(--muted)">/9</span></div>
        <div class="n">DOES IT WORK?</div><div class="l">${esc(r.trl_label)}</div>
        <div class="bar"><i style="width:${r.trl / 9 * 100}%"></i></div></div>
      <div class="gauge"><div class="v">${r.crl}<span style="font-size:14px;color:var(--muted)">/9</span></div>
        <div class="n">DO PEOPLE USE IT?</div><div class="l">${esc(r.crl_label)}</div>
        <div class="bar"><i class="t" style="width:${r.crl / 9 * 100}%"></i></div></div>
      <div class="gauge"><div class="v">${r.srl}<span style="font-size:14px;color:var(--muted)">/9</span></div>
        <div class="n">CAN IT SPREAD?</div><div class="l">${esc(r.srl_label)}</div>
        <div class="bar"><i class="a" style="width:${r.srl / 9 * 100}%"></i></div></div>
    </div>
    ${say(esc(r.assessment), r.scale_ready ? 'ok' : r.balance_gap >= 3 ? 'warn' : '', r.scale_ready ? 'ok' : 'warn')}
    <div class="row">
      Works <input id="sTrl" type="number" min="1" max="9" value="${r.trl}" style="width:66px">
      Used <input id="sCrl" type="number" min="1" max="9" value="${r.crl}" style="width:66px">
      Spreads <input id="sSrl" type="number" min="1" max="9" value="${r.srl}" style="width:66px">
      <button class="btn sm ghost" id="btnReady">Update</button>
    </div>
  </div>

  <div class="card"><h3>Has someone already solved this?</h3>
    <div class="hint">The team is not allowed to start building until this is checked.</div>
    ${sm ? `
      ${say(`<b>Answer: ${esc(cap(sm.verdict))}.</b> ${esc(sm.headline)}`, 'ok', 'ok')}
      <div style="margin-top:10px;font-size:13.5px;line-height:1.6">${esc(sm.reasoning || '')}</div>
      ${(sm.failure_warnings || []).map(f => say(
        `<b>This was tried before and failed: ${esc(f.title)}</b><br>What went wrong: ${esc(f.what_went_wrong)}<br>
         <i>So this time: ${esc(f.how_to_avoid)}</i>`, 'bad', 'warn')).join('')}
      ${(sm.reuse_candidates || []).length ? `<div style="margin-top:12px"><div class="mono">Use or copy these instead of starting fresh</div>
        <div class="row" style="margin-top:6px">${sm.reuse_candidates.map(c => `<span class="tag green">${esc(c)}</span>`).join('')}</div></div>` : ''}
      <div class="hint" style="margin-top:12px">Looked through ${sm.searched} past items · found ${sm.failures_found} failures
        ${sm.estimated_time_saved_months ? `· saves roughly ${sm.estimated_time_saved_months} months` : ''}</div>
    ` : '<button class="btn big" id="btnSM">Search past solutions and failures</button>'}
  </div>

  <div class="card"><h3>The promise</h3>
    <div class="hint">What "success" means, agreed with the village <b>before</b> any building starts —
      so nobody can move the goalposts later.</div>
    ${ic.metrics?.length ? `
      <table><tr><th>What we will measure</th><th>In</th><th>Should go</th></tr>
      ${ic.metrics.map(m => `<tr><td><b>${esc(m.metric)}</b><div class="mono">${esc(m.baseline_method || '')}</div></td>
        <td>${esc(m.unit)}</td><td><span class="tag ${m.direction === 'increase' ? 'green' : 'blue'}">${m.direction === 'increase' ? 'up' : 'down'}</span></td></tr>`).join('')}</table>
      <div class="row" style="margin-top:12px">${(ic.signed_by || []).map(s => `<span class="tag green">${ui('ok')} ${esc(s)}</span>`).join('')}</div>
      ${ic.fail_condition ? say(`<b>We agree this counts as failure:</b> ${esc(ic.fail_condition)}`, 'warn', 'warn') : ''}
    ` : `<button class="btn big" id="btnSuggest">Draft the promise with AI</button><div id="cOut"></div>`}
  </div>

  <div class="card"><h3>Steps of work — proof required</h3>
    <div class="hint">You cannot tick a step as done without uploading the actual thing you made.</div>
    ${(p.milestones || []).map(m => `<div class="item" style="cursor:default">
      <div class="t">${esc(m.name)} <span class="tag ${m.status === 'approved' ? 'green' : m.status === 'submitted' ? 'amber' : ''}">${esc(cap(m.status))}</span></div>
      <div class="m"><span>due ${when(m.due)}</span>
        ${(m.evidence || []).length ? `<span class="tag blue">${m.evidence.length} file(s) attached</span>` : '<span class="tag red">no proof yet</span>'}</div>
      ${m.status === 'open' ? `<div class="row" style="margin-top:9px"><input type="file" class="mFile" data-m="${m.milestone_id}" style="width:auto">
        <button class="btn sm" data-submitm="${m.milestone_id}">Send with proof</button></div>` : ''}
      ${m.status === 'submitted' ? `<div class="row" style="margin-top:9px">
        <button class="btn sm ok" data-approve="${m.milestone_id}">Accept</button>
        <button class="btn sm bad" data-reject="${m.milestone_id}">Send back</button></div>` : ''}
    </div>`).join('') || blank('build', 'No steps added yet', 'Add the first step below.')}
    <div class="row" style="margin-top:12px"><input id="miName" placeholder="What is the next step?" style="width:260px">
      <select id="miKind" style="width:140px"><option>deliverable</option><option>prototype</option><option>pilot</option><option>report</option></select>
      <button class="btn sm ghost" id="btnAddMi">Add step</button></div>
  </div>

  <div class="card"><h3>Money, released in steps</h3>
    <div class="hint">Money follows proof, never promises. Nothing big is released before the promise is signed.</div>
    <div class="row"><span class="tag green">${ui('money')} Given so far: ${inr(p.funding?.released)}</span></div>
    ${(p.funding?.tranches || []).map(t => `<div class="item" style="cursor:default"><div class="t">${inr(t.amount)}</div>
      <div class="m"><span class="tag">${esc(cap(t.source))}</span><span>for ${esc(cap(t.stage_gate))}</span><span>${when(t.released_at)}</span></div></div>`).join('')}
    <div class="row" style="margin-top:12px"><input id="fAmt" type="number" placeholder="Amount ₹" style="width:150px">
      <select id="fSrc" style="width:150px"><option value="state_fund">Government</option><option value="csr">Company CSR</option>
        <option value="industry">Industry</option><option value="grant">Research grant</option></select>
      <select id="fGate" style="width:180px">${S.cfg.project_stages.map(s => `<option value="${s.key}">${s.label}</option>`).join('')}</select>
      <button class="btn sm" id="btnFund">Release</button></div>
  </div>

  <div class="card"><h3>Did life actually get better?</h3>
    ${im.rows?.length ? `
      <table><tr><th>What we measured</th><th>Before</th><th>Now</th><th>Change</th></tr>
      ${im.rows.map(x => `<tr><td>${esc(x.metric)}</td><td>${x.baseline ?? '–'}</td><td><b>${x.current ?? '–'}</b></td>
        <td><span class="tag ${x.verdict === 'improved' ? 'green' : 'red'}">${x.improvement_pct != null ? x.improvement_pct + '% better' : '–'}</span></td></tr>`).join('')}</table>
      <div class="grid g3" style="margin-top:14px">
        <div class="kpi accent g"><div class="v">${im.success_rate_pct}%</div><div class="k">of promises kept</div></div>
        <div class="kpi accent"><div class="v">${num(im.beneficiaries)}</div><div class="k">people helped</div></div>
        <div class="kpi accent a"><div class="v">${im.cost_per_beneficiary ? inr(im.cost_per_beneficiary) : '–'}</div><div class="k">cost per person</div></div>
      </div>
    ` : ic.metrics?.length ? `<div class="hint">Type what the numbers were before and what they are now.</div>
      ${ic.metrics.map(m => `<div class="row" style="margin-bottom:8px">
        <span style="width:270px;font-size:13.5px">${esc(m.metric)}</span>
        <input class="rBase" data-m="${esc(m.metric)}" type="number" placeholder="before" style="width:120px">
        <input class="rCur" type="number" placeholder="now" style="width:120px"></div>`).join('')}
      <div class="row" style="margin-top:10px"><input id="benef" type="number" placeholder="How many people helped" style="width:200px">
        <button class="btn ok" id="btnImpact">Save the result</button></div>`
      : blank('done', 'Sign the promise first', 'We can only measure against numbers everyone agreed to.')}
  </div>

  <div class="card"><h3>What the village says</h3>
    <div class="hint">The final word belongs to the people who reported the problem. Not the college. Not the company.</div>
    ${(p.feedback || []).map(f => `<div class="item" style="cursor:default">
      <div class="t">${esc(f.reporter_name)} <span class="tag ${f.verdict === 'fully_resolved' ? 'green' : f.verdict === 'partially_resolved' ? 'amber' : 'red'}">${esc(cap(f.verdict))}</span>
        <span class="tag">${f.rating}/5</span></div>
      <div class="m">${esc(f.comment || '')}</div></div>`).join('') ||
      blank('search', 'No one from the village has spoken yet', 'Ask them below.')}
    <div class="row" style="margin-top:12px"><input id="fbWho" placeholder="Your name" style="width:150px">
      <select id="fbV" style="width:190px"><option value="fully_resolved">Fully fixed</option>
        <option value="partially_resolved">Partly fixed</option><option value="not_resolved">Not fixed</option></select>
      <input id="fbR" type="number" min="1" max="5" value="5" style="width:70px">
      <input id="fbC" placeholder="Tell us more" style="width:230px">
      <button class="btn sm" id="btnFb">Send</button></div>
  </div>

  <div class="card"><h3>Full story trail</h3>
    <div class="tl">${(p.ledger || []).map(e => `<div class="e ${e.actor_role === 'ai' ? 'ai' : e.actor_role === 'citizen' ? 'cit' : 'gov'}">
      <div class="w">${esc(cap(e.event))}</div><div class="d">${esc(e.actor)} · ${when(e.at)}</div></div>`).join('')}</div>
  </div>`;
}

function bindProjectActions(p) {
  const id = p.project_id;
  const reload = () => openProject(id);
  const on = (sel, fn) => { const el = $(sel); if (el) el.onclick = fn; };

  on('#btnStage', async () => {
    const b = $('#btnStage'); busy(b, '...');
    try {
      await api(`/api/projects/${id}/stage`, {
        method: 'POST', body: JSON.stringify({
          stage: $('#nextStage').value, by: 'Faculty Mentor', override_gate: $('#ovr').checked
        })
      });
      toast('Moved to the next step.', 'ok'); reload();
    } catch (e) { toast('Blocked: ' + e.message, 'bad'); done(b); }
  });

  on('#btnReady', async () => {
    try {
      await api(`/api/projects/${id}/readiness`, {
        method: 'POST', body: JSON.stringify({
          trl: +$('#sTrl').value, crl: +$('#sCrl').value, srl: +$('#sSrl').value,
          assessed_by: 'Faculty Mentor'
        })
      });
      toast('Updated.', 'ok'); reload();
    } catch (e) { toast(e.message, 'bad'); }
  });

  on('#btnSM', async () => {
    const b = $('#btnSM'); busy(b, 'Searching everything already tried');
    try { await api(`/api/projects/${id}/solution-memory`, { method: 'POST' }); toast('Search done.', 'ok'); reload(); }
    catch (e) { toast(e.message, 'bad'); done(b); }
  });

  on('#btnSuggest', async () => {
    const b = $('#btnSuggest'); busy(b, 'Drafting');
    try {
      const c = await api(`/api/projects/${id}/impact-contract/suggest`, { method: 'POST' });
      S.sel.draft = c;
      $('#cOut').innerHTML = `<table style="margin-top:14px"><tr><th></th><th>What we will measure</th><th>In</th></tr>
        ${c.metrics.map((m, i) => `<tr><td><input type="checkbox" class="pickM" data-i="${i}" checked style="width:auto"></td>
          <td>${esc(m.metric)}<div class="mono">${esc(m.baseline_method || '')}</div></td><td>${esc(m.unit)}</td></tr>`).join('')}</table>
        ${c.fail_condition ? say(`<b>Counts as failure:</b> ${esc(c.fail_condition)}`, 'warn', 'warn') : ''}
        <label>Who is agreeing to this? (the village must be one of them)</label>
        <input id="signers" value="Lead College, Gram Panchayat, District Department">
        <button class="btn ok big" id="btnSign" style="margin-top:12px">Everyone agrees — sign it</button>`;
      $('#btnSign').onclick = async () => {
        try {
          await api(`/api/projects/${id}/impact-contract`, {
            method: 'POST', body: JSON.stringify({
              metrics: $$('.pickM:checked').map(x => S.sel.draft.metrics[+x.dataset.i]),
              review_points: S.sel.draft.review_points || [],
              fail_condition: S.sel.draft.fail_condition,
              sdg_alignment: S.sel.draft.sdg_alignment || [],
              signed_by: $('#signers').value.split(',').map(s => s.trim()).filter(Boolean)
            })
          });
          toast('Promise signed. Now everyone knows what success means.', 'ok'); reload();
        } catch (e) { toast(e.message, 'bad'); }
      };
    } catch (e) { toast(e.message, 'bad'); }
    done(b);
  });

  on('#btnAddMi', async () => {
    if (!$('#miName').value) return toast('Give the step a name.', 'bad');
    await api(`/api/projects/${id}/milestones`, {
      method: 'POST', body: JSON.stringify({
        name: $('#miName').value, kind: $('#miKind').value, due_in_days: 30,
        required_evidence: ['report']
      })
    });
    toast('Step added.', 'ok'); reload();
  });

  $$('[data-submitm]').forEach(b => b.onclick = async () => {
    const mid = b.dataset.submitm;
    const fi = $(`.mFile[data-m="${mid}"]`);
    if (!fi?.files.length) return toast('Attach the file. Proof is compulsory here.', 'bad');
    busy(b, 'Uploading');
    try {
      const ids = [];
      for (const f of fi.files) {
        const fd = new FormData(); fd.append('file', f);
        ids.push((await api('/api/challenges/evidence', { method: 'POST', body: fd })).id);
      }
      await api(`/api/projects/${id}/milestones/${mid}/submit`, {
        method: 'POST', body: JSON.stringify({ evidence_ids: ids, submitted_by: 'Student Team' })
      });
      toast('Sent for checking.', 'ok'); reload();
    } catch (e) { toast(e.message, 'bad'); done(b); }
  });

  $$('[data-approve],[data-reject]').forEach(b => b.onclick = async () => {
    const mid = b.dataset.approve || b.dataset.reject;
    await api(`/api/projects/${id}/milestones/${mid}/review`, {
      method: 'POST', body: JSON.stringify({ approved: !!b.dataset.approve, reviewer: 'Faculty Mentor' })
    });
    toast('Done.', 'ok'); reload();
  });

  on('#btnFund', async () => {
    const b = $('#btnFund'); busy(b, '...');
    try {
      await api(`/api/projects/${id}/funding`, {
        method: 'POST', body: JSON.stringify({
          amount: Number($('#fAmt').value), source: $('#fSrc').value,
          stage_gate: $('#fGate').value, approved_by: 'Funding Committee'
        })
      });
      toast('Money released.', 'ok'); reload();
    } catch (e) { toast('Blocked: ' + e.message, 'bad'); done(b); }
  });

  on('#btnImpact', async () => {
    const readings = $$('.rBase').map((el, i) => ({
      metric: el.dataset.m, baseline: Number(el.value), current: Number($$('.rCur')[i].value)
    })).filter(r => r.baseline || r.current);
    if (!readings.length) return toast('Enter at least one before and now number.', 'bad');
    const b = $('#btnImpact'); busy(b, 'Checking against the promise');
    try {
      await api(`/api/projects/${id}/impact`, {
        method: 'POST', body: JSON.stringify({
          readings, beneficiaries: Number($('#benef').value || 0), recorded_by: 'Field Team'
        })
      });
      toast('Result saved.', 'ok'); reload();
    } catch (e) { toast(e.message, 'bad'); done(b); }
  });

  on('#btnFb', async () => {
    try {
      await api(`/api/challenges/${p.challenge_id}/feedback`, {
        method: 'POST', body: JSON.stringify({
          verdict: $('#fbV').value, rating: Number($('#fbR').value),
          comment: $('#fbC').value || null, reporter_name: $('#fbWho').value || 'a villager'
        })
      });
      toast('Thank you. Your word counts most here.', 'ok'); reload();
    } catch (e) { toast(e.message, 'bad'); }
  });
}

/* ============================================================= 6. PROOF */
async function viewProof() {
  const [d, m, ins, pred] = await Promise.all([
    api('/api/dashboard'), api('/api/map'), api('/api/insights'), api('/api/predictions')]);
  S.cache.map = m;
  const c = d.challenges, pr = d.projects, im = d.impact, ec = d.ecosystem;
  const maxD = Math.max(1, ...c.by_domain.map(x => x.count));
  const maxDist = Math.max(1, ...c.by_district.map(x => x.count));
  return `
  <div class="strip">
    <div><div class="v">${num(c.total)}</div><div class="k">problems reported</div></div>
    <div><div class="v">${num(ec.constellations)}</div><div class="k">hidden patterns found</div></div>
    <div><div class="v">${num(pr.deployed)}</div><div class="k">solutions working now</div></div>
    <div><div class="v">${num(im.beneficiaries)}</div><div class="k">people helped</div></div>
    <div><div class="v">${im.community_resolved_pct}%</div><div class="k">villages say fixed</div></div>
  </div>

  <div class="card" style="margin-top:16px"><h3>Map of Jharkhand</h3>
    <div class="hint">Every dot is a real report. Colour shows how far it has got.
      ${esc(m.privacy_note)}</div>
    <div id="map"></div>
    <div class="legend">${Object.entries(m.legend).map(([k, v]) =>
    `<span><i style="background:${STATE_COLOR[k]}"></i>${esc(v)}</span>`).join('')}</div>
  </div>

  <div class="grid g2" style="margin-top:16px">
    <div class="card"><h3>What people complain about most</h3>
      ${c.by_domain.slice(0, 8).map(x => `<div class="hbar"><span class="n">${esc(x.label)}</span>
        <span class="b"><i style="width:${x.count / maxD * 100}%"></i></span><span class="c">${x.count}</span></div>`).join('')}
      <div class="hint" style="margin-top:16px">Which districts</div>
      ${c.by_district.slice(0, 7).map(x => `<div class="hbar"><span class="n">${esc(x.key)}</span>
        <span class="b"><i class="t" style="width:${x.count / maxDist * 100}%"></i></span><span class="c">${x.count}</span></div>`).join('')}
    </div>
    <div class="card"><h3>How far the work has got</h3>
      ${pr.by_stage.map(x => `<div class="hbar"><span class="n">${esc(x.label)}</span>
        <span class="b"><i class="a" style="width:${x.count / Math.max(1, pr.total) * 100}%"></i></span><span class="c">${x.count}</span></div>`).join('')
      || blank('build', 'No work started yet', '')}
      <div class="grid g2" style="margin-top:16px">
        <div class="kpi"><div class="v">${inr(im.funding_released)}</div><div class="k">money spent</div></div>
        <div class="kpi"><div class="v">${im.cost_per_beneficiary ? inr(im.cost_per_beneficiary) : '–'}</div>
          <div class="k">per person helped</div></div>
      </div>
    </div>
  </div>

  <div class="grid g2" style="margin-top:16px">
    <div class="card"><h3>What the government should notice</h3>
      ${say(`<b>${esc(ins.headline)}</b>`, '', 'eye')}
      ${(ins.systemic_findings || []).map(f => `<div style="margin-top:12px">
        <div style="font-weight:700;color:var(--ink);font-size:13.5px">${esc(f.finding)}
          <span class="tag ${f.confidence === 'high' ? 'green' : f.confidence === 'medium' ? 'amber' : 'red'}">${esc(f.confidence)} confidence</span></div>
        <div class="hint" style="margin:5px 0 0">Because: ${esc(f.evidence)}<br>So: ${esc(f.implication)}</div></div>`).join('')}
      ${(ins.recommended_missions || []).map(mm => say(
        `<b>Worth starting: ${esc(mm.name)}</b> (${esc((mm.districts || []).join(', '))})<br>${esc(mm.outcome)}`, 'ok', 'ok')).join('')}
    </div>
    <div class="card"><h3>What is likely coming next</h3>
      <div class="hint">${esc(pred.disclaimer)}</div>
      ${(pred.predictions || []).map(p => `<div class="item" style="cursor:default">
        <div class="t">${esc(p.district)} · ${esc(cap(p.domain))} ${p.imminent ? '<span class="tag red">soon</span>' : ''}</div>
        <div class="m"><span class="tag amber">${p.risk_pct}% chance</span><span>around ${esc(p.expected_window)}</span></div>
        <div style="margin-top:6px;font-size:13.5px">${esc(p.note)}</div></div>`).join('')
      || blank('search', 'Not enough history yet', 'Come back once more seasons of reports are in.')}
    </div>
  </div>

  <div class="card" style="margin-top:16px"><h3>Is the problem itself getting smaller?</h3>
    <div class="hint">Not "how many projects did we run" — but "did the actual problem shrink,
      across every project and every rupee". Click a topic.</div>
    <div class="row">${S.cfg.domains.slice(0, 10).map(d2 => `<span class="chip" data-twin="${d2.key}">${esc(d2.label)}</span>`).join('')}</div>
    <div id="twin" style="margin-top:14px"></div>
  </div>`;
}

function bindProof() {
  const m = S.cache.map;
  if (S.map) { S.map.remove(); S.map = null; }
  S.map = L.map('map').setView([23.6, 85.3], 7);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    { attribution: '&copy; OpenStreetMap', maxZoom: 18 }).addTo(S.map);
  m.districts.forEach(d => {
    if (!d.count) return;
    L.circle([d.lat, d.lon], {
      radius: 9000 + d.count * 2600, color: '#1668c4', weight: 1,
      fillColor: '#1668c4', fillOpacity: .07
    }).addTo(S.map).bindTooltip(`${d.district}: ${d.count} report(s)`);
  });
  m.points.forEach(p => {
    L.circleMarker([p.lat, p.lon], {
      radius: 6 + (p.priority_score || 0) / 22, color: '#fff', weight: 1.5,
      fillColor: STATE_COLOR[p.progress_state] || '#888', fillOpacity: .92
    }).addTo(S.map).bindPopup(
      `<b>${esc(p.title || '')}</b><br>${esc(p.domain_label)} · ${esc(p.district || '')}` +
      `<br>${esc(BAND_WORD[p.priority] || '')}<br>Now: ${esc(cap(p.progress_state))}`);
  });

  $$('[data-twin]').forEach(el => el.onclick = async () => {
    $$('[data-twin]').forEach(x => x.classList.remove('on')); el.classList.add('on');
    $('#twin').innerHTML = '<span class="spin dark"></span> Building the live picture...';
    const t = await api('/api/digital-twin/' + el.dataset.twin);
    const v = t.community_verdict;
    $('#twin').innerHTML = `
      <div class="grid g4">
        <div class="kpi"><div class="v">${t.open_reports}</div><div class="k">reports about this</div></div>
        <div class="kpi"><div class="v">${t.active_projects}</div><div class="k">projects working on it</div></div>
        <div class="kpi"><div class="v">${inr(t.total_funding_released)}</div><div class="k">money spent</div></div>
        <div class="kpi"><div class="v">${t.avg_measured_improvement_pct}%</div><div class="k">measured improvement</div></div>
      </div>
      ${say(`<b>${esc(cap(t.signal))}</b> — ${esc(t.advice)}`,
        t.signal === 'working' ? 'ok' : t.signal === 'strategy_review_needed' ? 'bad' : 'warn',
        t.signal === 'working' ? 'ok' : 'warn')}
      <div class="row">
        <span class="tag green">Fully fixed: ${v.fully_resolved}</span>
        <span class="tag amber">Partly: ${v.partially_resolved}</span>
        <span class="tag red">Not fixed: ${v.not_resolved}</span>
        <span class="tag">${num(t.beneficiaries)} people helped</span></div>`;
  });
}

/* =========================================================== 7. LESSONS */
async function viewLessons() {
  const [sm, inst, part] = await Promise.all([
    api('/api/solution-memory'), api('/api/institutions'), api('/api/partners')]);
  return `
  ${say(`<b>Most systems hide their failures. We do the opposite.</b> ${sm.failures} of the ${sm.count}
     things in this library are projects that did <b>not</b> work — kept on purpose, and shown to every
     new team before they start. One failure written down saves the next team a whole year.`, 'bad', 'warn')}

  <div class="card"><h3>Everything already tried — including what failed</h3>
    ${sm.items.map(i => `<div class="item" style="cursor:default">
      <div class="t">${esc(i.title)}
        <span class="tag ${i.kind === 'failure' ? 'red' : i.kind === 'patent' ? 'amber' : i.kind === 'paper' ? 'purple' : 'green'}">${i.kind === 'failure' ? 'FAILED' : esc(cap(i.kind))}</span></div>
      <div class="m"><span>${esc(i.source || '')}</span><span>${i.year || ''}</span><span>${esc(cap(i.domain || ''))}</span></div>
      <div style="margin-top:6px;font-size:13.5px;line-height:1.6">${esc(i.summary || '')}</div>
      ${i.failure_reason ? say(`<b>Why it failed:</b> ${esc(i.failure_reason)}<br>
        <b>The lesson:</b> ${esc(i.lesson || '')}`, 'bad', 'warn') : ''}
      ${i.cost_note ? `<div class="hint" style="margin-top:6px">${esc(i.cost_note)}</div>` : ''}
    </div>`).join('')}
  </div>

  <div class="grid g2" style="margin-top:16px">
    <div class="card"><h3>Colleges and what they are good at (${inst.count})</h3>
      <div class="hint">Demo profiles. Teacher names are made-up placeholders, not real people.</div>
      ${inst.items.map(i => `<div class="item" style="cursor:default">
        <div class="t">${esc(i.name)}</div>
        <div class="m"><span>${esc(i.district)}</span>
          <span class="mono">${i.faculty?.length || 0} teachers · ${i.laboratories?.length || 0} labs</span></div>
        <div class="row" style="margin-top:7px">${(i.research_areas || []).slice(0, 5).map(a => `<span class="tag">${esc(a)}</span>`).join('')}</div>
        <div class="hint" style="margin-top:7px">Took on ${i.impact_profile.challenges_accepted} problem(s) ·
          ${num(i.impact_profile.citizens_impacted)} people helped</div></div>`).join('')}
    </div>
    <div class="card"><h3>Companies, startups and NGOs (${part.count})</h3>
      <div class="hint">What each one is actually willing to give.</div>
      ${part.items.map(p => `<div class="item" style="cursor:default">
        <div class="t">${esc(p.name)} <span class="tag">${esc(p.type)}</span></div>
        <div style="margin-top:6px;font-size:13.5px">${esc(p.description)}</div>
        <div class="row" style="margin-top:7px">${(p.offers || []).map(o => `<span class="tag teal">${esc(cap(o))}</span>`).join('')}</div>
      </div>`).join('')}
    </div>
  </div>

  <div class="card" style="margin-top:16px"><h3>A student's record of real work</h3>
    <div class="hint">Not a certificate anyone can print. Every line is backed by proof in the story trail.</div>
    <div class="row"><input id="ppName" placeholder="Student name, e.g. Priya Kumari" style="width:300px">
      <button class="btn" id="btnPp">Show their record</button></div>
    <div id="ppOut"></div>
  </div>`;
}

function bindLessons() {
  $('#btnPp').onclick = async () => {
    const n = $('#ppName').value.trim(); if (!n) return;
    const p = await api('/api/passport/' + encodeURIComponent(n));
    const s = p.summary;
    $('#ppOut').innerHTML = `
      <div class="strip" style="margin-top:16px">
        <div><div class="v">${s.challenges_worked_on}</div><div class="k">problems worked on</div></div>
        <div><div class="v">${s.prototypes}</div><div class="k">things built</div></div>
        <div><div class="v">${s.pilots_supported}</div><div class="k">village tests</div></div>
        <div><div class="v">${s.deployed_solutions}</div><div class="k">actually deployed</div></div>
        <div><div class="v">${num(s.citizens_impacted)}</div><div class="k">people helped</div></div>
      </div>
      ${p.projects.length ? `<table style="margin-top:16px"><tr><th>Project</th><th>What they did</th><th>Result</th><th>Village said</th></tr>
        ${p.projects.map(e => `<tr><td><b>${esc(e.title)}</b><div class="mono">${esc(e.district || '')}</div></td>
          <td>${esc(cap(e.role || ''))}<div class="mono">${esc(e.discipline || '')}</div></td>
          <td>${e.measured_improvement_pct != null ? e.measured_improvement_pct + '% better' : '–'}</td>
          <td>${e.community_validated ? '<span class="tag green">confirmed</span>' : '<span class="tag">waiting</span>'}</td></tr>`).join('')}</table>`
      : blank('search', 'No record found for that name', 'Try "Priya Kumari" from the demo data.')}`;
  };
}


/* ================================================== 8. SATISFACTION / SAY */
const STAR_WORD = ['', 'Very unhappy', 'Unhappy', 'It was okay', 'Happy', 'Very happy'];
const stars = n => '★'.repeat(n) + '☆'.repeat(5 - n);

function starRow(name, size = '') {
  return `<div class="stars" data-star-group="${name}">
    ${[1, 2, 3, 4, 5].map(i => `<button type="button" class="star ${size}" data-star="${i}"
      aria-label="${i} out of 5">★</button>`).join('')}</div>`;
}

async function viewSay() {
  const st = await api('/api/satisfaction');
  const districts = S.cfg.districts;
  return `
  ${say(`<b>This page is about us, not about your problem.</b> Tell us honestly how this service
     treated you. Every officer and every college on this platform can see the score below.`, '', 'chat')}

  <div class="split form">
    <div>
      <div class="q">
        <div class="qh"><div class="qn">1</div><div class="qt">Overall, how happy are you with this service?</div></div>
        <div class="qb">
          ${starRow('overall', 'big')}
          <div class="starlabel" id="overallWord">Tap a star</div>
        </div>
      </div>

      <div class="q">
        <div class="qh"><div class="qn">2</div><div class="qt">A few quick questions</div></div>
        <div class="qs">Leave any blank if it does not apply to you.</div>
        <div class="qb">
          ${st.questions.map(q => `<div class="qrow">
            <div class="qq">${esc(q.q)}</div>
            ${starRow(q.key)}
            <div class="qends"><span>${esc(q.low)}</span><span>${esc(q.high)}</span></div>
          </div>`).join('')}
        </div>
      </div>

      <div class="q">
        <div class="qh"><div class="qn">3</div><div class="qt">Anything you want to tell us?</div></div>
        <div class="qs">Good or bad. We publish the bad ones too.</div>
        <div class="qb">
          <textarea id="rvComment" style="min-height:110px"
            placeholder="e.g. Reporting was easy but nobody told me what happened for two months"></textarea>
          <div class="row" style="margin-top:12px">
            <label style="margin:0;font-weight:400;font-size:14px">
              <input type="checkbox" id="rvRec" style="width:auto"> I would tell a friend to use this</label>
          </div>
          <button class="moretog" data-more="rv">+ Add your name, district and who you are</button>
          <div class="more" id="more-rv">
            <div class="grid g2">
              <div><label>Your name (optional)</label><input id="rvName" placeholder="Optional"></div>
              <div><label>District</label><select id="rvDist"><option value="">Not saying</option>
                ${districts.map(d => `<option>${d}</option>`).join('')}</select></div>
            </div>
            <div class="grid g2">
              <div><label>Who are you?</label><select id="rvWho">
                <option value="citizen">A citizen</option><option value="student">A student</option>
                <option value="teacher">A teacher</option>
                <option value="government officer">A government officer</option>
                <option value="company or NGO">From a company or NGO</option>
                <option value="other">Someone else</option></select></div>
              <div><label>Report reference (optional)</label>
                <input id="rvRef" placeholder="e.g. CH-XXXXXXXX"></div>
            </div>
          </div>
        </div>
      </div>

      <button class="btn xl" id="btnReview">${ui('send', '#fff')} &nbsp;Send my review</button>
    </div>

    <div id="sayOut">${satisfactionPanel(st)}</div>
  </div>`;
}

function satisfactionPanel(st) {
  if (!st.count) return blank('search', 'Nobody has reviewed the service yet',
    'Be the first. Your honest opinion decides what gets fixed next.');
  const a = st.average;
  return `
  <div class="card">
    <h3>What everyone thinks</h3>
    <div class="hint">Live and unfiltered. Low scores are shown exactly like high ones.</div>
    <div class="bigscore">
      <div class="n">${a}<small>/5</small></div>
      <div class="meta">
        <div class="sline">${stars(Math.round(a))}</div>
        <div class="sub"><b>${st.count}</b> people have reviewed this service.
          ${st.happy_pct}% are happy with it${st.unhappy_pct > 0 ? `, ${st.unhappy_pct}% are not` : ''}.
          ${st.recommend_pct != null ? `<br><b>${st.recommend_pct}%</b> would tell a friend to use it.` : ''}</div>
      </div>
    </div>
    <div style="margin-top:18px">${st.distribution.map(d => `<div class="distrow">
      <span class="s">${'★'.repeat(d.stars)}</span>
      <span class="b"><i style="width:${d.pct}%"></i></span>
      <span class="c">${d.count} &middot; ${d.pct}%</span></div>`).join('')}</div>
  </div>

  <div class="card"><h3>How we do on each thing</h3>
    ${st.questions.filter(q => q.average != null).map(q => `<div class="hbar">
      <span class="n" title="${esc(q.q)}">${esc(q.q.replace(/\?$/, ''))}</span>
      <span class="b"><i class="${q.average >= 4 ? 'g' : q.average >= 3 ? 'a' : 'r'}"
        style="width:${q.average / 5 * 100}%"></i></span>
      <span class="c">${q.average}</span></div>`).join('') ||
      '<div class="hint">No detailed answers yet.</div>'}
    <div class="row" style="margin-top:14px">
      <button class="btn sm ghost" id="btnThemes">${ui('eye')} &nbsp;What are people telling us?</button></div>
    <div id="themesOut"></div>
  </div>

  ${st.by_district.length ? `<div class="card"><h3>Happiness by district</h3>
    <div class="hint">Where the service is working, and where it is not.</div>
    ${st.by_district.map(d => `<div class="hbar"><span class="n">${esc(d.district)}</span>
      <span class="b"><i class="${d.average >= 4 ? 'g' : d.average >= 3 ? 'a' : 'r'}"
        style="width:${(d.average || 0) / 5 * 100}%"></i></span>
      <span class="c">${d.average}</span></div>`).join('')}</div>` : ''}

  <div class="card"><h3>What people said</h3>
    <div class="hint">Newest first. Nothing is hidden or edited.</div>
    ${st.recent.filter(r => r.comment).map(r => `
      <div class="rev ${r.overall <= 2 ? 'low' : r.overall >= 4 ? 'high' : ''}">
        <div class="rh"><span class="rs">${stars(r.overall)}</span>
          <span class="rn">${esc(r.name)}</span>
          <span class="tag">${esc(r.who)}</span>
          ${r.district ? `<span class="tag blue">${esc(r.district)}</span>` : ''}
          ${r.would_recommend ? '<span class="tag green">would recommend</span>' : ''}
          <span class="mono" style="margin-left:auto">${when(r.at)}</span></div>
        <div class="rc">${esc(r.comment)}</div></div>`).join('') ||
      '<div class="hint">Ratings given, but nobody has written a comment yet.</div>'}
  </div>`;
}

function bindSay() {
  const picked = {};
  const wire = () => {
    $$('[data-star-group]').forEach(grp => {
      const key = grp.dataset.starGroup;
      $$('.star', grp).forEach(b => b.onclick = () => {
        picked[key] = +b.dataset.star;
        $$('.star', grp).forEach(x => x.classList.toggle('lit', +x.dataset.star <= picked[key]));
        if (key === 'overall') $('#overallWord').textContent = STAR_WORD[picked[key]];
      });
    });
    $$('.moretog').forEach(b => b.onclick = () => $('#more-' + b.dataset.more).classList.toggle('open'));
    const bt = $('#btnThemes'); if (bt) bt.onclick = loadThemes;
  };

  async function loadThemes() {
    const b = $('#btnThemes'); busy(b, 'Reading every comment');
    try {
      const t = await api('/api/satisfaction/themes');
      $('#themesOut').innerHTML = !t.enough_data
        ? say(esc(t.message), 'warn', 'warn')
        : `${say(`<b>${esc(t.headline)}</b>`, '', 'eye')}
           ${(t.working_well || []).length ? `<div style="margin-top:12px"><div class="mono">WORKING WELL</div>
             ${t.working_well.map(w => `<div class="item" style="cursor:default;margin-top:6px">
               <div class="t">${esc(w.theme)} <span class="tag green">${w.mentions} mention(s)</span></div>
               <div class="m">${esc(w.evidence || '')}</div></div>`).join('')}</div>` : ''}
           ${(t.needs_fixing || []).length ? `<div style="margin-top:12px"><div class="mono">NEEDS FIXING</div>
             ${t.needs_fixing.map(w => `<div class="item" style="cursor:default;margin-top:6px">
               <div class="t">${esc(w.theme)} <span class="tag red">${w.mentions} mention(s)</span></div>
               <div class="m">${esc(w.evidence || '')}</div>
               ${w.suggested_action ? `<div style="margin-top:6px;font-size:13px"><b>Do this:</b> ${esc(w.suggested_action)}</div>` : ''}
               </div>`).join('')}</div>` : ''}
           ${t.most_urgent_fix ? say(`<b>The one thing to fix first:</b> ${esc(t.most_urgent_fix)}`, 'warn', 'warn') : ''}
           <div class="hint" style="margin-top:10px">Read ${t.comments_read} written comment(s)
             &middot; confidence ${esc(t.confidence || '-')}</div>`;
    } catch (e) { toast(e.message, 'bad'); }
    done(b);
  }

  wire();

  $('#btnReview').onclick = async () => {
    if (!picked.overall) return toast('Please tap a star for the first question.', 'bad');
    const b = $('#btnReview'); busy(b, 'Sending');
    try {
      await api('/api/satisfaction', {
        method: 'POST', body: JSON.stringify({
          overall: picked.overall,
          easy_to_report: picked.easy_to_report ?? null,
          got_updates: picked.got_updates ?? null,
          problem_solved: picked.problem_solved ?? null,
          treated_fairly: picked.treated_fairly ?? null,
          would_recommend: $('#rvRec').checked,
          comment: $('#rvComment').value || null,
          name: $('#rvName') ? $('#rvName').value || null : null,
          district: $('#rvDist') ? $('#rvDist').value || null : null,
          who: $('#rvWho') ? $('#rvWho').value : 'citizen',
          challenge_id: $('#rvRef') && $('#rvRef').value.trim() ? $('#rvRef').value.trim() : null,
        })
      });
      toast('Thank you. Your honest opinion is now on the public page.', 'ok');
      const st = await api('/api/satisfaction');
      $('#sayOut').innerHTML = satisfactionPanel(st);
      $('#rvComment').value = '';
      $$('.star').forEach(x => x.classList.remove('lit'));
      $('#overallWord').textContent = 'Tap a star';
      for (const k in picked) delete picked[k];
      wire();
      $('#sayOut').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (e) { toast(e.message, 'bad'); }
    done(b);
  };
}

/* ============================================================== router */
const VIEWS = {
  home: ['Welcome', '', viewHome, bindHome],
  story: ['One full story', 'Follow a single real problem through all six steps.', viewStory, bindNav2],
  report: ['Report a problem', 'Tell us what is wrong. Two minutes, your own words.', viewReport, bindReport],
  review: ['Check reports', 'Decide what is real and what matters most.', viewReview, bindReview],
  connect: ['Connect the dots', 'Find the one cause hiding behind many reports.', viewConnect, bindConnect],
  team: ['Find the team', 'Who can actually fix this, and why them.', viewTeam, bindTeam],
  work: ['Do the work', 'Build it, test it in a real village, prove it.', viewWork, bindWork],
  proof: ['See the proof', 'Did life actually get better? Here are the numbers.', viewProof, bindProof],
  say: ['Rate this service', 'Tell us honestly how this service treated you.', viewSay, bindSay],
  lessons: ['Learn from the past', 'What worked, what failed, and who can help.', viewLessons, bindLessons],
};

async function go(v, push = true) {
  if (!VIEWS[v]) v = 'home';
  S.view = v;
  if (push && location.hash.slice(1) !== v) location.hash = v;
  $$('#nav a').forEach(a => a.classList.toggle('on', a.dataset.v === v));
  const [title, desc, render, bind] = VIEWS[v] || VIEWS.home;
  $('#vTitle').textContent = title; $('#vDesc').textContent = desc;
  $('#view').innerHTML = '<div class="card"><span class="spin dark"></span> Loading...</div>';
  window.scrollTo({ top: 0, behavior: 'smooth' });
  try {
    const html = await render();
    const isStep = STEPS.some(x => x[0] === v);
    $('#view').innerHTML = (isStep ? ribbon(v) : '') + html + (isStep ? nextStep(v) : '');
    bind?.();
    bindNav2();
  } catch (e) {
    $('#view').innerHTML = blank('search', 'Could not load this page', e.message);
  }
}
window.go = go;
window.addEventListener('hashchange', () => {
  const v = location.hash.slice(1);
  if (v && v !== S.view) go(v, false);
});

(async function init() {
  $$('#nav a').forEach(a => a.onclick = () => go(a.dataset.v));
  S.cfg = await api('/api/config');
  const ai = S.cfg.ai;
  $('#aiStatus').innerHTML = ai.groq_configured
    ? `AI is on <b style="color:#7ee0a0">●</b>`
    : `AI key missing <b style="color:#f0c27f">●</b><br><span style="font-size:9.5px">basic mode — add GROQ_API_KEY to .env</span>`;
  $('#btnDemo').onclick = async () => {
    if (!confirm('Load 8 sample reports? This clears the current ones.')) return;
    $('#btnDemo').innerHTML = '<span class="spin"></span> Loading';
    try {
      const r = await api('/api/demo/bootstrap?reset=true', { method: 'POST' });
      toast(`Loaded ${r.created} sample reports through the real AI.`, 'ok');
      go('review');
    } catch (e) { toast(e.message, 'bad'); }
    $('#btnDemo').textContent = 'Load demo';
  };
  go(location.hash.slice(1) || 'home', false);
})();
