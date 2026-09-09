/* Shared shell for every Duty of Care page: header, sponsor stack ribbon, crisis footer,
   reading-mode and theme toggles, and a few helpers. Crisis resources are in the DOM
   before any interaction on every page. */
(function () {
  const $ = (q, root) => (root || document).querySelector(q);
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
  };
  function el(tag, text, cls) {
    const n = document.createElement(tag);
    if (text !== undefined && text !== null) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  }
  window.el = el;
  window.$q = $;

  const RIBBON = {
    google: [
      ['gemini', 'Gemini on Vertex AI'], ['adk', 'ADK'], ['agent_engine', 'Agent Engine'], ['agent_search', 'Agent Search'], ['model_armor', 'Model Armor'],
      ['vertex_evaluation', 'Gen AI Evaluation'], ['cloudrun', 'Cloud Run'], ['artifact_registry', 'Artifact Registry'], ['secret_manager', 'Secret Manager'], ['cloud_build', 'Cloud Build'], ['cloud_logging', 'Cloud Logging'], ['cloud_monitoring', 'Monitoring'],
    ],
    partner: [
      ['replit_agent', 'Agent'], ['replit_deployment', 'Autoscale'], ['replit_auth', 'Auth'],
      ['replit_database', 'Database'], ['replit_app_storage', 'App Storage'], ['replit_scheduled', 'Scheduled'], ['replit_secrets', 'Secrets'],
    ],
  };
  const NAV = [['/', 'Review'], ['/presets', 'Demo library'], ['/evidence', 'Evidence'], ['/developers', 'Developers'], ['/stack', 'Stack']];

  function buildHeader() {
    const header = el('header', undefined, 'site');
    const nav = el('nav', undefined, 'shell');
    const brand = el('a', 'DUTY OF CARE', 'brand'); brand.href = '/';
    const links = el('div', undefined, 'navlinks');
    const here = location.pathname.replace(/\/$/, '') || '/';
    NAV.forEach(([href, label]) => {
      const a = el('a', label); a.href = href;
      if ((href === '/' && here === '/') || (href !== '/' && here.startsWith(href))) a.setAttribute('aria-current', 'page');
      links.append(a);
    });
    const tools = el('div', undefined, 'tools');
    const plain = el('button', 'Plain'); plain.dataset.modeButton = 'plain';
    const tech = el('button', 'Technical'); tech.dataset.modeButton = 'technical';
    const theme = el('button', 'Dark'); theme.dataset.themeButton = '';
    const live = el('button', 'Live stack'); live.dataset.live = '';
    tools.append(plain, tech, theme, live);
    nav.append(brand, links, tools);
    header.append(nav);
    return header;
  }

  function buildRibbon() {
    const ribbon = el('div', undefined, 'ribbon'); ribbon.dataset.ribbon = '';
    const shell = el('div', undefined, 'shell');
    shell.append(el('span', 'Built with', 'lbl'));
    [['google', 'Google Cloud'], ['partner', 'Replit']].forEach(([group, label]) => {
      const grp = el('span', undefined, 'grp ' + group);
      grp.append(el('b', label));
      RIBBON[group].forEach(([key, name]) => {
        const a = el('a', undefined, 'tool'); a.href = '/stack#' + key; a.dataset.stackKey = key;
        a.title = name + ' · checking…';
        a.append(el('span', undefined, 'dot'), document.createTextNode(name));
        grp.append(a);
      });
      shell.append(grp);
    });
    const more = el('a', 'How each is used →', 'more'); more.href = '/stack';
    shell.append(more);
    ribbon.append(shell);
    return ribbon;
  }

  function buildLivePanel() {
    const aside = el('aside', undefined, 'livepanel'); aside.dataset.livePanel = ''; aside.hidden = true;
    aside.append(el('strong', 'Live integrations'), el('p', 'Real round trips, cached for one minute.', 'small'));
    const host = el('div', 'Waiting…'); host.dataset.health = '';
    const close = el('button', 'Close'); close.dataset.liveClose = '';
    aside.append(host, close);
    return aside;
  }

  function setMode(mode) {
    document.documentElement.dataset.reading = mode;
    document.querySelectorAll('[data-mode-button]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.modeButton === mode)));
    store.set('care-mode', mode);
  }
  function setTheme(dark) {
    document.documentElement.dataset.theme = dark ? 'dark' : '';
    const b = $('[data-theme-button]'); if (b) b.textContent = dark ? 'Light' : 'Dark';
    store.set('care-theme', dark ? 'dark' : 'light');
  }

  let stackCache = null;
  async function loadStack() {
    if (stackCache) return stackCache;
    try {
      const r = await fetch('/v1/stack');
      stackCache = (await r.json()).data;
    } catch { stackCache = null; }
    return stackCache;
  }
  window.loadStack = loadStack;

  async function paintRibbon() {
    const data = await loadStack();
    if (!data) return;
    const byKey = Object.fromEntries(data.components.map(c => [c.key, c]));
    document.querySelectorAll('[data-stack-key]').forEach(a => {
      const c = byKey[a.dataset.stackKey]; if (!c) return;
      const dot = a.querySelector('.dot'); dot.className = 'dot ' + c.status;
      a.title = c.name + ' · ' + c.status + (c.evidence ? ' · ' + c.evidence : '');
    });
  }

  async function showLive() {
    const panel = $('[data-live-panel]'); panel.hidden = false;
    const host = $('[data-health]'); host.textContent = 'Checking…';
    try {
      const r = await fetch('/health'); const p = await r.json(); host.replaceChildren();
      Object.entries(p.integrations).forEach(([name, v]) => {
        const row = el('p');
        row.append(el('span', undefined, 'dot ' + (v.ok ? 'live' : 'unreachable')), document.createTextNode(' ' + name.replaceAll('_', ' ') + ' · ' + (v.ok ? 'available' : 'unavailable') + (v.host ? ' · ' + v.host : '')));
        host.append(row);
      });
      const surf = el('p', 'Surface: ' + p.product_surface + ' · corpus ' + p.corpus_version, 'small');
      host.append(surf);
    } catch { host.textContent = 'Health check unavailable'; }
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.body.prepend(buildHeader(), buildRibbon());
    const skip = el('a', 'Skip to content', 'skip'); skip.href = '#main'; document.body.prepend(skip);
    document.body.append(buildLivePanel());
    setMode(store.get('care-mode') === 'technical' ? 'technical' : 'plain');
    document.querySelectorAll('[data-mode-button]').forEach(b => b.onclick = () => setMode(b.dataset.modeButton));
    setTheme(store.get('care-theme') === 'dark');
    $('[data-theme-button]').onclick = () => setTheme(document.documentElement.dataset.theme !== 'dark');
    $('[data-live]').onclick = showLive;
    $('[data-live-close]').onclick = () => { $('[data-live-panel]').hidden = true; };
    paintRibbon();
    document.dispatchEvent(new CustomEvent('shell:ready'));
  });

  // Helpers shared by pages.
  window.careFetch = async function (path, options) {
    const r = await fetch(path, options);
    const type = r.headers.get('content-type') || '';
    const body = type.includes('json') ? await r.json() : await r.text();
    if (!r.ok) {
      const msg = (body && body.error && (body.error.message + (body.error.fix ? ' ' + body.error.fix : ''))) || (body && body.detail && body.detail.message) || ('HTTP ' + r.status);
      const err = new Error(msg); err.status = r.status; err.body = body; throw err;
    }
    return body;
  };
  window.downloadText = function (filename, text, type) {
    const blob = new Blob([text], { type: type || 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = filename; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  window.CLASS_LABEL = { method_specificity: 'Method specificity', framing_as_solution: 'Framed as solution', absence_of_help_seeking: 'No help-seeking', romanticisation: 'Romanticisation', repetition: 'Repetition', signposting_absence: 'No signpost' };
  window.screenplayPage = function (scenes, triggers, onMark) {
    const page = el('div', undefined, 'page');
    const head = el('div', undefined, 'pagehead');
    head.append(el('span', 'Scene coverage'), el('span', scenes.length + (scenes.length === 1 ? ' scene' : ' scenes')));
    page.append(head);
    scenes.forEach(scene => {
      page.append(el('div', scene.heading, 'slug'));
      const spans = (triggers || []).filter(t => t.scene_id === scene.scene_id && t.match_start >= 0).sort((a, b) => a.match_start - b.match_start);
      const body = el('p'); let cursor = 0;
      spans.forEach(t => {
        if (t.match_start < cursor) return;
        if (t.match_start > cursor) body.append(document.createTextNode(scene.text.slice(cursor, t.match_start)));
        const m = el('mark', scene.text.slice(t.match_start, t.match_end), 'trig tc-' + t.trigger_class);
        m.dataset.scene = scene.scene_id; m.dataset.klass = t.trigger_class;
        m.title = window.CLASS_LABEL[t.trigger_class] || t.trigger_class;
        m.append(el('sup', '▲'));
        if (onMark) m.onclick = () => onMark(scene.scene_id, m);
        body.append(m); cursor = t.match_end;
      });
      body.append(document.createTextNode(scene.text.slice(cursor)));
      page.append(body);
    });
    return page;
  };
  // Final Draft (.fdx) and plain-text screenplay import, done in the browser so no
  // file is uploaded anywhere until the writer presses Review.
  window.parseScreenplayFile = async function (file) {
    const text = await file.text();
    if (!/\.fdx$/i.test(file.name)) return text;
    const doc = new DOMParser().parseFromString(text, 'application/xml');
    const out = [];
    doc.querySelectorAll('Paragraph').forEach(p => {
      const type = p.getAttribute('Type') || '';
      const line = Array.from(p.querySelectorAll('Text')).map(t => t.textContent).join('').trim();
      if (!line) return;
      if (type === 'Scene Heading') out.push('', line.toUpperCase(), '');
      else if (type === 'Character') out.push('', line.toUpperCase());
      else if (type === 'Parenthetical') out.push(line);
      else if (type === 'Dialogue') out.push(line, '');
      else out.push(line, '');
    });
    return out.join('\n').replace(/\n{3,}/g, '\n\n').trim();
  };
})();
