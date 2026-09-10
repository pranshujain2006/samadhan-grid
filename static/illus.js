/* Hand-built inline SVG art. No CDN, no image files, works offline, scales cleanly. */

const C = {
  sky: '#e8f1fc', ink: '#0d2340', blue: '#1668c4', lblue: '#8bbcec', teal: '#0f7d78',
  green: '#2f7a45', lgreen: '#a8d5b5', amber: '#d99518', sand: '#f0dcb8',
  red: '#c9534c', purple: '#6b59ab', white: '#ffffff', grey: '#c8d6e5', dark: '#15335c'
};

/* ---------------------------------------------------------------- HERO
   Left: a village with a dry handpump and a woman carrying water a long way.
   Right: college + industry + community turning that into a working solution. */
export const heroArt = () => `
<svg viewBox="0 0 760 300" class="art" role="img" aria-label="A village problem becomes a tested solution">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f4f9ff"/><stop offset="1" stop-color="#e3eefb"/>
    </linearGradient>
    <linearGradient id="win" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffd88a"/><stop offset="1" stop-color="#f5b942"/>
    </linearGradient>
  </defs>
  <rect width="760" height="300" rx="18" fill="url(#sky)"/>
  <circle cx="86" cy="52" r="22" fill="#ffd88a"/>
  <path d="M0 236 Q120 214 250 232 T520 226 T760 236 V300 H0Z" fill="${C.lgreen}" opacity=".55"/>
  <path d="M0 252 Q180 236 380 250 T760 246 V300 H0Z" fill="${C.green}" opacity=".28"/>

  <!-- village huts -->
  <g>
    <path d="M40 196 L74 166 L108 196 Z" fill="${C.red}" opacity=".85"/>
    <rect x="52" y="196" width="44" height="40" fill="${C.sand}"/>
    <rect x="66" y="212" width="16" height="24" fill="${C.dark}" opacity=".65"/>
    <path d="M112 202 L140 178 L168 202 Z" fill="${C.amber}" opacity=".85"/>
    <rect x="122" y="202" width="36" height="34" fill="${C.sand}"/>
    <rect x="134" y="216" width="13" height="20" fill="${C.dark}" opacity=".65"/>
  </g>

  <!-- dry handpump, with a "no water" mark -->
  <g>
    <rect x="196" y="186" width="9" height="50" rx="3" fill="${C.dark}"/>
    <rect x="182" y="204" width="38" height="7" rx="3" fill="${C.dark}"/>
    <path d="M205 190 q22 -6 26 10" stroke="${C.dark}" stroke-width="7" fill="none" stroke-linecap="round"/>
    <circle cx="240" cy="176" r="13" fill="none" stroke="${C.red}" stroke-width="3"/>
    <path d="M232 168 l16 16" stroke="${C.red}" stroke-width="3" stroke-linecap="round"/>
    <text x="200" y="256" font-size="11" fill="${C.ink}" opacity=".65" font-family="sans-serif">dry in summer</text>
  </g>

  <!-- woman walking with a water pot, long distance -->
  <g transform="translate(276,178)">
    <ellipse cx="9" cy="-16" rx="13" ry="7" fill="${C.blue}"/>
    <circle cx="9" cy="1" r="8" fill="#8d5b3f"/>
    <path d="M9 9 l-7 24 h14 z" fill="${C.purple}"/>
    <path d="M4 33 l-4 18 M14 33 l4 18" stroke="${C.dark}" stroke-width="3.5" stroke-linecap="round"/>
  </g>
  <path d="M300 224 h74" stroke="${C.ink}" stroke-width="2" stroke-dasharray="5 6" opacity=".45"/>
  <text x="302" y="216" font-size="11" fill="${C.ink}" opacity=".65" font-family="sans-serif">3 km walk</text>

  <!-- the arrow of transformation -->
  <path d="M382 150 q24 -34 60 -34 h30" stroke="${C.blue}" stroke-width="3" fill="none"
        stroke-linecap="round" stroke-dasharray="7 7"/>
  <path d="M466 110 l14 6 -14 6z" fill="${C.blue}"/>

  <!-- college -->
  <g transform="translate(492,96)">
    <path d="M0 22 L40 2 L80 22 Z" fill="${C.blue}"/>
    <rect x="6" y="22" width="68" height="46" fill="${C.white}" stroke="${C.grey}"/>
    <rect x="16" y="34" width="13" height="14" fill="url(#win)"/>
    <rect x="34" y="34" width="13" height="14" fill="url(#win)"/>
    <rect x="52" y="34" width="13" height="14" fill="url(#win)"/>
    <rect x="34" y="54" width="13" height="14" fill="${C.dark}" opacity=".6"/>
    <text x="40" y="84" font-size="11" fill="${C.ink}" text-anchor="middle" font-family="sans-serif">college</text>
  </g>

  <!-- industry gear + sensor -->
  <g transform="translate(614,110)">
    <circle cx="20" cy="20" r="16" fill="none" stroke="${C.teal}" stroke-width="6"/>
    <circle cx="20" cy="20" r="5" fill="${C.teal}"/>
    <g stroke="${C.teal}" stroke-width="5" stroke-linecap="round">
      <path d="M20 -1 v-7"/><path d="M20 41 v7"/><path d="M-1 20 h-7"/><path d="M41 20 h7"/>
    </g>
    <text x="20" y="62" font-size="11" fill="${C.ink}" text-anchor="middle" font-family="sans-serif">industry</text>
  </g>

  <!-- working handpump + happy result -->
  <g transform="translate(508,182)">
    <rect x="14" y="4" width="9" height="50" rx="3" fill="${C.dark}"/>
    <rect x="0" y="22" width="38" height="7" rx="3" fill="${C.dark}"/>
    <path d="M23 8 q22 -6 26 10" stroke="${C.dark}" stroke-width="7" fill="none" stroke-linecap="round"/>
    <path d="M50 22 q3 12 -3 18 q-8 -6 3 -18z" fill="${C.blue}"/>
    <circle cx="62" cy="6" r="13" fill="${C.green}"/>
    <path d="M56 6 l4 5 8 -9" stroke="${C.white}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
  <g transform="translate(596,190)">
    <ellipse cx="9" cy="-14" rx="12" ry="6" fill="${C.teal}"/>
    <circle cx="9" cy="2" r="8" fill="#8d5b3f"/>
    <path d="M9 10 l-7 22 h14 z" fill="${C.green}"/>
    <path d="M4 32 l-3 16 M14 32 l3 16" stroke="${C.dark}" stroke-width="3.5" stroke-linecap="round"/>
  </g>
  <text x="560" y="262" font-size="12" fill="${C.green}" font-weight="700" text-anchor="middle"
        font-family="sans-serif">200 m walk</text>

  <!-- rising proof chart -->
  <g transform="translate(672,196)">
    <rect x="0" y="26" width="12" height="20" rx="2" fill="${C.lblue}"/>
    <rect x="18" y="14" width="12" height="32" rx="2" fill="${C.blue}"/>
    <rect x="36" y="2" width="12" height="44" rx="2" fill="${C.green}"/>
    <text x="24" y="62" font-size="11" fill="${C.ink}" text-anchor="middle" font-family="sans-serif">proof</text>
  </g>
</svg>`;

/* ------------------------------------------------------- STEP ICONS (48px) */
const wrap = (inner, bg) =>
  `<svg viewBox="0 0 48 48" class="ico" role="img"><rect width="48" height="48" rx="14" fill="${bg}"/>${inner}</svg>`;

export const stepIcon = {
  speak: () => wrap(`
    <rect x="20" y="11" width="8" height="16" rx="4" fill="${C.blue}"/>
    <path d="M16 24 a8 8 0 0 0 16 0" stroke="${C.blue}" stroke-width="2.6" fill="none" stroke-linecap="round"/>
    <path d="M24 32 v5" stroke="${C.blue}" stroke-width="2.6" stroke-linecap="round"/>
    <path d="M18 37 h12" stroke="${C.blue}" stroke-width="2.6" stroke-linecap="round"/>`, C.sky),
  check: () => wrap(`
    <path d="M24 10 l12 5 v9 c0 8-5 12-12 14 -7-2-12-6-12-14 v-9z" fill="none" stroke="${C.teal}" stroke-width="2.6"/>
    <path d="M19 24 l4 4 7-8" stroke="${C.teal}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`,
    '#e3f4f3'),
  link: () => wrap(`
    <circle cx="15" cy="16" r="4" fill="${C.purple}"/><circle cx="33" cy="14" r="4" fill="${C.purple}"/>
    <circle cx="14" cy="33" r="4" fill="${C.purple}"/><circle cx="32" cy="34" r="4" fill="${C.purple}"/>
    <circle cx="24" cy="24" r="5" fill="${C.purple}" opacity=".35"/>
    <g stroke="${C.purple}" stroke-width="2" opacity=".75">
      <path d="M18 18 l3 3"/><path d="M30 17 l-3 4"/><path d="M18 30 l3-3"/><path d="M29 31 l-2-3"/></g>`, '#eeebf8'),
  team: () => wrap(`
    <circle cx="17" cy="18" r="5" fill="${C.amber}"/><circle cx="31" cy="18" r="5" fill="${C.amber}" opacity=".7"/>
    <path d="M8 36 c0-6 4-9 9-9 s9 3 9 9z" fill="${C.amber}"/>
    <path d="M22 36 c0-6 4-9 9-9 s9 3 9 9z" fill="${C.amber}" opacity=".7"/>`, '#fdf3e3'),
  build: () => wrap(`
    <path d="M30 12 a7 7 0 0 0-9 9 L12 30 a3 3 0 0 0 4 4 l9-9 a7 7 0 0 0 9-9 l-5 5 -4-1 -1-4z"
          fill="${C.green}"/>`, '#e8f4ea'),
  proof: () => wrap(`
    <rect x="11" y="26" width="7" height="12" rx="2" fill="${C.lblue}"/>
    <rect x="21" y="18" width="7" height="20" rx="2" fill="${C.blue}"/>
    <rect x="31" y="10" width="7" height="28" rx="2" fill="${C.green}"/>`, C.sky),
  book: () => wrap(`
    <path d="M10 14 q7-3 13 1 v20 q-6-4-13-1z" fill="${C.red}" opacity=".55"/>
    <path d="M38 14 q-7-3-13 1 v20 q6-4 13-1z" fill="${C.red}"/>
    <path d="M24 15 v20" stroke="#fdecea" stroke-width="2"/>
    <path d="M14 20 h6 M14 25 h6 M28 20 h6 M28 25 h6" stroke="#fdecea"
          stroke-width="1.6" stroke-linecap="round"/>`, '#fdecea'),
  home: () => wrap(`
    <path d="M24 11 L38 23 v14 a2 2 0 0 1-2 2 H12 a2 2 0 0 1-2-2 V23z" fill="${C.blue}"/>
    <rect x="21" y="28" width="6" height="11" fill="${C.white}"/>`, C.sky),
};

/* --------------------------------------------------------- ROLE PORTRAITS */
const person = (skin, cloth, extra = '') => `
  <circle cx="30" cy="24" r="11" fill="${skin}"/>
  <path d="M30 37 c-11 0-18 7-18 16 h36 c0-9-7-16-18-16z" fill="${cloth}"/>${extra}`;

export const roleArt = {
  citizen: () => `<svg viewBox="0 0 60 60" class="face">
    ${person('#c78b62', C.teal, `<path d="M19 20 a11 11 0 0 1 22 0 z" fill="${C.purple}"/>`)}</svg>`,
  officer: () => `<svg viewBox="0 0 60 60" class="face">
    ${person('#d5a077', C.dark, `<rect x="18" y="14" width="24" height="6" rx="3" fill="${C.blue}"/>
      <rect x="26" y="44" width="8" height="9" fill="${C.white}" opacity=".9"/>`)}</svg>`,
  college: () => `<svg viewBox="0 0 60 60" class="face">
    ${person('#b97b52', C.amber, `<path d="M16 18 L30 11 L44 18 L30 25 z" fill="${C.dark}"/>
      <path d="M40 20 v8" stroke="${C.dark}" stroke-width="2"/>`)}</svg>`,
  company: () => `<svg viewBox="0 0 60 60" class="face">
    ${person('#e0b48b', C.green, `<path d="M22 39 l8 7 8-7" fill="${C.white}" opacity=".85"/>`)}</svg>`,
};

/* ------------------------------------------------------- EMPTY-STATE ART */
export const emptyArt = (kind = 'search') => {
  const art = {
    search: `<circle cx="46" cy="42" r="20" fill="none" stroke="${C.lblue}" stroke-width="5"/>
      <path d="M61 57 l16 16" stroke="${C.lblue}" stroke-width="6" stroke-linecap="round"/>`,
    inbox: `<path d="M18 34 h64 v34 a4 4 0 0 1-4 4 H22 a4 4 0 0 1-4-4z" fill="${C.sky}" stroke="${C.lblue}" stroke-width="3"/>
      <path d="M18 34 l14-18 h36 l14 18" fill="none" stroke="${C.lblue}" stroke-width="3"/>
      <path d="M18 48 h20 l5 8 h14 l5-8 h20" fill="none" stroke="${C.lblue}" stroke-width="3"/>`,
    build: `<rect x="24" y="46" width="52" height="28" rx="4" fill="${C.sky}" stroke="${C.lblue}" stroke-width="3"/>
      <path d="M36 46 V32 a14 14 0 0 1 28 0 v14" fill="none" stroke="${C.lblue}" stroke-width="3"/>`,
    done: `<circle cx="50" cy="50" r="26" fill="${C.sky}" stroke="${C.lgreen}" stroke-width="3"/>
      <path d="M38 51 l8 9 17-19" stroke="${C.green}" stroke-width="5" fill="none"
        stroke-linecap="round" stroke-linejoin="round"/>`,
  }[kind] || '';
  return `<svg viewBox="0 0 100 100" class="empty-art">${art}</svg>`;
};

/* ------------------------------------------------- SMALL INLINE UI ICONS */
export const ui = (name, color = 'currentColor') => {
  const p = {
    mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v4M8 22h8" fill="none" stroke-width="2"/>',
    pin: '<path d="M12 22s7-7.6 7-12a7 7 0 1 0-14 0c0 4.4 7 12 7 12z" fill="none" stroke-width="2"/><circle cx="12" cy="10" r="2.5"/>',
    cam: '<path d="M3 8h4l2-3h6l2 3h4v12H3z" fill="none" stroke-width="2"/><circle cx="12" cy="13" r="4" fill="none" stroke-width="2"/>',
    send: '<path d="M3 20l19-8L3 4l4 8z" fill="none" stroke-width="2" stroke-linejoin="round"/>',
    ok: '<path d="M4 13l5 5L20 6" fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
    x: '<path d="M6 6l12 12M18 6L6 18" fill="none" stroke-width="3" stroke-linecap="round"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" fill="none" stroke-width="2"/><circle cx="12" cy="12" r="3" fill="none" stroke-width="2"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>',
    warn: '<path d="M12 3l10 18H2z" fill="none" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v4" stroke-width="2.4" stroke-linecap="round"/><circle cx="12" cy="17.5" r="1.2"/>',
    money: '<rect x="2" y="6" width="20" height="12" rx="2" fill="none" stroke-width="2"/><circle cx="12" cy="12" r="3" fill="none" stroke-width="2"/>',
    phone: '<path d="M6.5 3h3l2 5-2.5 1.5a12 12 0 0 0 5.5 5.5L16 12.5l5 2v3a2 2 0 0 1-2.2 2A17 17 0 0 1 3.5 5.2 2 2 0 0 1 5.5 3z" fill="none" stroke-width="2" stroke-linejoin="round"/>',
    office: '<path d="M4 21V7l8-4 8 4v14" fill="none" stroke-width="2" stroke-linejoin="round"/><path d="M9 21v-6h6v6" fill="none" stroke-width="2"/><path d="M9 11h2M13 11h2" stroke-width="2" stroke-linecap="round"/>',
    chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z" fill="none" stroke-width="2" stroke-linejoin="round"/>',
  }[name] || '';
  return `<svg viewBox="0 0 24 24" class="ui-ico" fill="${color}" stroke="${color}">${p}</svg>`;
};

/* --------------------------------------------------- HELPLINE ILLUSTRATION */
export const helplineArt = () => `
<svg viewBox="0 0 120 120" class="help-art" role="img" aria-label="Call the helpline">
  <circle cx="60" cy="60" r="54" fill="#e8f1fc"/>
  <circle cx="60" cy="60" r="40" fill="#cfe3f8"/>
  <path d="M42 28h12l7 18-9 5.5a44 44 0 0 0 20 20L78 62l18 7v12a7 7 0 0 1-7.7 7A62 62 0 0 1 35 35.7 7 7 0 0 1 42 28z"
        fill="${C.blue}"/>
  <g stroke="${C.teal}" stroke-width="3.5" fill="none" stroke-linecap="round" opacity=".85">
    <path d="M84 34a26 26 0 0 1 8 8"/><path d="M90 26a38 38 0 0 1 11 11"/>
  </g>
</svg>`;
