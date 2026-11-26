/* Filters, folding, copying and diagrams for a board, lens or plan page. The page reads the same
   without this script: every entry is in the HTML, and the controls stay hidden. */
(() => {
  const root = document.documentElement;
  const status = document.getElementById('status');
  const FILTERED = '.entry[data-kind], .entry[data-lane]';
  const off = {};
  const listSections = () => [...document.querySelectorAll('details.section')];

  const applyFilters = () => {
    const groups = Object.entries(off);
    for (const entry of document.querySelectorAll(FILTERED)) {
      entry.hidden = groups.some(([group, values]) => values.has(entry.dataset[group] ?? ''));
    }
    for (const section of listSections()) {
      const entries = [...section.querySelectorAll(FILTERED)];
      section.hidden = entries.length > 0 && entries.every((entry) => entry.hidden);
    }
  };

  const toggleChip = (chip) => {
    const shown = chip.getAttribute('aria-pressed') !== 'true';
    chip.setAttribute('aria-pressed', String(shown));
    off[chip.dataset.filter] ??= new Set();
    const hidden = off[chip.dataset.filter];
    if (shown) hidden.delete(chip.dataset.value);
    if (!shown) hidden.add(chip.dataset.value);
    applyFilters();
  };

  const syncFold = () => {
    const button = document.querySelector('[data-fold]');
    if (!button) return;
    const anyOpen = listSections().some((section) => section.open);
    button.textContent = anyOpen ? 'Collapse all' : 'Expand all';
  };

  const foldAll = () => {
    const open = !listSections().some((section) => section.open);
    for (const section of listSections()) section.open = open;
    syncFold();
  };

  const writeClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = document.createElement('textarea');
      area.value = text;
      document.body.append(area);
      area.select();
      document.execCommand('copy');
      area.remove();
    }
  };

  const copy = async (button) => {
    await writeClipboard(button.dataset.copy);
    button.dataset.copied = '';
    status.textContent = 'Copied ' + button.dataset.copy;
    setTimeout(() => delete button.dataset.copied, 1200);
  };

  const readToken = (name) => getComputedStyle(root).getPropertyValue(name).trim();

  const sources = new Map();
  let drawing = Promise.resolve();

  const enqueue = (task) => {
    drawing = drawing.then(task).catch(() => {});
  };

  const configureDiagrams = () => {
    const chosen = root.dataset.theme;
    const dark = chosen ? chosen === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'base',
      flowchart: { useMaxWidth: false },
      themeVariables: {
        darkMode: dark,
        background: readToken('--ground'),
        primaryColor: readToken('--surface'),
        primaryTextColor: readToken('--ink'),
        primaryBorderColor: readToken('--quiet'),
        lineColor: readToken('--quiet'),
        secondaryColor: readToken('--ground'),
        tertiaryColor: readToken('--ground'),
        clusterBkg: readToken('--ground'),
        clusterBorder: readToken('--line'),
        edgeLabelBackground: readToken('--ground'),
        fontFamily: readToken('--text'),
      },
    });
  };

  const drawWaiting = () => {
    const waiting = [...document.querySelectorAll('pre.mermaid:not([data-processed])')];
    const nodes = waiting.filter((node) => !node.closest('details:not([open])'));
    for (const node of nodes) {
      if (!sources.has(node)) sources.set(node, node.textContent);
    }
    if (!nodes.length) return undefined;
    return window.mermaid.run({ nodes, suppressErrors: true });
  };

  const restoreSources = () => {
    for (const [node, source] of sources) {
      node.textContent = source;
      node.removeAttribute('data-processed');
    }
  };

  const drawOpenDiagrams = () => {
    if (window.mermaid) enqueue(drawWaiting);
  };

  const redrawDiagrams = () => {
    enqueue(() => {
      restoreSources();
      configureDiagrams();
      return drawWaiting();
    });
  };

  const startDiagrams = () => {
    if (!window.mermaid || !document.querySelector('pre.mermaid')) return;
    configureDiagrams();
    drawOpenDiagrams();
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', redrawDiagrams);
    const themes = new MutationObserver(redrawDiagrams);
    themes.observe(root, { attributes: true, attributeFilter: ['data-theme'] });
  };

  const onToggle = () => {
    syncFold();
    drawOpenDiagrams();
  };

  document.addEventListener('click', (event) => {
    const control = event.target.closest('[data-copy], [data-filter], [data-fold]');
    if (!control) return;
    if ('copy' in control.dataset) copy(control);
    if ('filter' in control.dataset) toggleChip(control);
    if ('fold' in control.dataset) foldAll();
  });
  document.addEventListener('toggle', onToggle, true);
  document.addEventListener('DOMContentLoaded', startDiagrams);
  root.classList.add('js');
})();
