/* A small fake DOM for the script of a rendered page. It parses the page, runs the page's own
   inline script against it, replays the steps it is given and prints what a reader would then
   see, as JSON. Usage: node dom_harness.js <page.html> <steps.json> */
'use strict';

const fs = require('node:fs');
const vm = require('node:vm');

const VOID_TAGS = new Set(['meta', 'link', 'br', 'hr', 'img', 'input']);
const RAW_TAGS = new Set(['script', 'style']);
const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', '#x27': "'", '#39': "'" };
const TOKEN =
  /<!--[\s\S]*?-->|<![^>]*>|<\/([a-z][a-z0-9]*)\s*>|<([a-z][a-z0-9]*)((?:\s+[\w:-]+(?:="[^"]*")?)*)\s*\/?>|[^<]+|</gi;

const page = {
  listeners: {},
  observers: [],
  schemeListeners: [],
  timers: [],
  clipboard: [],
  commands: [],
  themes: [],
  runs: [],
  config: null,
  dark: false,
  clipboardDenied: false,
};

const decode = (text) => text.replace(/&(#x27|#39|amp|lt|gt|quot);/g, (_, name) => ENTITIES[name]);
const toAttribute = (key) => 'data-' + key.replace(/[A-Z]/g, (letter) => '-' + letter.toLowerCase());

const dispatch = (type, target) => {
  for (const handler of page.listeners[type] || []) handler({ type, target });
};

const reportChange = (element, name) => {
  for (const observer of page.observers) {
    const watched = observer.target === element && observer.names.includes(name);
    if (watched) queueMicrotask(observer.callback);
  }
};

const parseCompound = (text) => {
  const compound = { tag: '', classes: [], attributes: [], nots: [] };
  let rest = text.trim().replace(/:not\(([^()]*)\)/g, (_, inner) => {
    compound.nots.push(parseCompound(inner));
    return '';
  });
  rest = rest.replace(/\[([\w-]+)(?:="([^"]*)")?\]/g, (_, name, value) => {
    compound.attributes.push([name, value]);
    return '';
  });
  rest = rest.replace(/\.([\w-]+)/g, (_, name) => {
    compound.classes.push(name);
    return '';
  });
  if (!/^[a-z0-9]*$/i.test(rest)) throw new Error('the fake DOM cannot read the selector ' + text);
  compound.tag = rest.toLowerCase();
  return compound;
};

const matchesCompound = (element, compound) =>
  (!compound.tag || element.tag === compound.tag) &&
  compound.classes.every((name) => element.classNames.includes(name)) &&
  compound.attributes.every(
    ([name, value]) =>
      element.hasAttribute(name) && (value === undefined || element.attributes[name] === value),
  ) &&
  !compound.nots.some((inner) => matchesCompound(element, inner));

const DATASET = {
  get: (element, key) => (typeof key === 'string' ? element.attributes[toAttribute(key)] : undefined),
  has: (element, key) => element.hasAttribute(toAttribute(key)),
  set: (element, key, value) => {
    element.setAttribute(toAttribute(key), value);
    return true;
  },
  deleteProperty: (element, key) => {
    element.removeAttribute(toAttribute(key));
    return true;
  },
};

class Element {
  constructor(tag, attributes = {}) {
    this.tag = tag;
    this.attributes = attributes;
    this.children = [];
    this.parent = null;
    this.dataset = new Proxy(this, DATASET);
    this.classList = { add: (name) => this.addClass(name) };
  }

  get classNames() {
    return (this.attributes.class || '').split(/\s+/).filter(Boolean);
  }

  get descendants() {
    const elements = this.children.filter((child) => child instanceof Element);
    return elements.flatMap((child) => [child, ...child.descendants]);
  }

  get textContent() {
    return this.children.map((child) => (child instanceof Element ? child.textContent : child)).join('');
  }

  set textContent(text) {
    this.children = [String(text)];
  }

  get hidden() {
    return this.hasAttribute('hidden');
  }

  set hidden(value) {
    this.setFlag('hidden', value);
  }

  get open() {
    return this.hasAttribute('open');
  }

  set open(value) {
    if (Boolean(value) === this.open) return;
    this.setFlag('open', value);
    queueMicrotask(() => dispatch('toggle', this));
  }

  get value() {
    return this.attributes.value;
  }

  set value(text) {
    this.attributes.value = String(text);
  }

  addClass(name) {
    if (!this.classNames.includes(name)) this.setAttribute('class', [...this.classNames, name].join(' '));
  }

  setFlag(name, value) {
    if (value) this.setAttribute(name, '');
    if (!value) this.removeAttribute(name);
  }

  hasAttribute(name) {
    return Object.hasOwn(this.attributes, name);
  }

  getAttribute(name) {
    return this.hasAttribute(name) ? this.attributes[name] : null;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
    reportChange(this, name);
  }

  removeAttribute(name) {
    delete this.attributes[name];
    reportChange(this, name);
  }

  append(child) {
    child.parent = this;
    this.children.push(child);
  }

  remove() {
    this.parent.children = this.parent.children.filter((child) => child !== this);
    this.parent = null;
  }

  select() {}

  matches(selector) {
    return selector.split(',').some((text) => matchesCompound(this, parseCompound(text)));
  }

  closest(selector) {
    let node = this;
    while (node && !node.matches(selector)) node = node.parent;
    return node || null;
  }

  querySelectorAll(selector) {
    return this.descendants.filter((node) => node.matches(selector));
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
}

const readAttributes = (text) => {
  const attributes = {};
  for (const [, name, value] of text.matchAll(/([\w:-]+)(?:="([^"]*)")?/g)) {
    attributes[name] = decode(value || '');
  }
  return attributes;
};

const closeElement = (open, tag) => {
  let node = open;
  while (node && node.tag !== tag) node = node.parent;
  if (!node) throw new Error('the page closes ' + tag + ' without opening it');
  return node.parent;
};

const parsePage = (html) => {
  const tree = new Element('#document');
  let open = tree;
  let match;
  TOKEN.lastIndex = 0;
  while ((match = TOKEN.exec(html))) {
    const [text, closing, opening, attributeText] = match;
    if (closing) {
      open = closeElement(open, closing.toLowerCase());
      continue;
    }
    if (!opening) {
      if (!text.startsWith('<!')) open.children.push(decode(text));
      continue;
    }
    const element = new Element(opening.toLowerCase(), readAttributes(attributeText));
    open.append(element);
    if (RAW_TAGS.has(element.tag)) {
      const end = html.indexOf('</' + element.tag, TOKEN.lastIndex);
      element.children.push(html.slice(TOKEN.lastIndex, end));
      TOKEN.lastIndex = end;
    }
    if (!VOID_TAGS.has(element.tag)) open = element;
  }
  return tree;
};

const createDocument = (tree) => ({
  documentElement: tree.querySelector('html'),
  body: tree.querySelector('body'),
  getElementById: (id) => tree.querySelector('[id="' + id + '"]'),
  querySelectorAll: (selector) => tree.querySelectorAll(selector),
  querySelector: (selector) => tree.querySelector(selector),
  createElement: (tag) => new Element(tag),
  execCommand: (name) => page.commands.push(name),
  addEventListener: (type, handler) => {
    page.listeners[type] = [...(page.listeners[type] || []), handler];
  },
});

const isDark = (root) =>
  root.hasAttribute('data-theme') ? root.attributes['data-theme'] === 'dark' : page.dark;

const createMermaid = (document) => ({
  initialize: (config) => {
    page.config = config;
    page.themes.push({
      dark: config.themeVariables.darkMode,
      ink: config.themeVariables.primaryTextColor,
      security: config.securityLevel,
      starts_on_load: config.startOnLoad,
    });
  },
  run: async ({ nodes } = {}) => {
    const given = [...(nodes || document.querySelectorAll('.mermaid'))];
    const targets = given.filter((node) => !node.hasAttribute('data-processed'));
    const ink = page.config ? page.config.themeVariables.primaryTextColor : 'no theme';
    const sources = targets.map((node) => node.textContent);
    page.runs.push(sources);
    for (const node of targets) node.setAttribute('data-processed', 'true');
    await null;
    targets.forEach((node, index) => {
      node.textContent = 'drawn in ' + ink + ': ' + sources[index];
    });
  },
});

const createSandbox = (document, withMermaid) => {
  const root = document.documentElement;
  const sandbox = {
    document,
    navigator: {
      clipboard: {
        writeText: async (text) => {
          if (page.clipboardDenied) throw new Error('denied');
          page.clipboard.push(text);
        },
      },
    },
    getComputedStyle: () => ({
      getPropertyValue: (name) => ' ' + (isDark(root) ? 'dark' : 'light') + name + ' ',
    }),
    matchMedia: () => ({
      matches: page.dark,
      addEventListener: (type, handler) => page.schemeListeners.push(handler),
    }),
    MutationObserver: class {
      constructor(callback) {
        this.callback = callback;
      }

      observe(target, options) {
        page.observers.push({ target, names: options.attributeFilter, callback: this.callback });
      }
    },
    setTimeout: (handler) => page.timers.push(handler),
  };
  sandbox.window = sandbox;
  if (withMermaid) sandbox.mermaid = createMermaid(document);
  return sandbox;
};

const pick = (document, step) => {
  const found = document.querySelectorAll(step.select)[step.index || 0];
  if (!found) throw new Error('nothing matches ' + step.select + ' at ' + (step.index || 0));
  return found;
};

const STEPS = {
  load: (document) => dispatch('DOMContentLoaded', document),
  click: (document, step) => dispatch('click', pick(document, step)),
  toggle: (document, step) => {
    pick(document, step).open = step.open;
  },
  theme: (document, step) => {
    const root = document.documentElement;
    if (step.value) root.setAttribute('data-theme', step.value);
    if (!step.value) root.removeAttribute('data-theme');
  },
  scheme: (document, step) => {
    page.dark = step.dark;
    for (const handler of page.schemeListeners) handler({ matches: step.dark });
  },
  timers: () => {
    for (const handler of page.timers.splice(0)) handler();
  },
  deny_clipboard: () => {
    page.clipboardDenied = true;
  },
};

const describe = (document) => {
  const fold = document.querySelector('[data-fold]');
  return {
    root_classes: document.documentElement.classNames,
    status: document.getElementById('status').textContent,
    fold: fold ? fold.textContent : null,
    chips: document.querySelectorAll('[data-filter]').map((chip) => ({
      filter: chip.dataset.filter,
      value: chip.dataset.value,
      pressed: chip.getAttribute('aria-pressed') === 'true',
    })),
    entries: document.querySelectorAll('.entry[data-kind]').map((entry) => ({
      ref: entry.querySelector('.ref').textContent,
      kind: entry.dataset.kind,
      thread: entry.dataset.thread,
      hidden: entry.hidden,
    })),
    sections: document.querySelectorAll('details.section').map((section) => ({
      title: section.querySelector('h2').textContent,
      open: section.open,
      hidden: section.hidden,
    })),
    diagrams: document.querySelectorAll('pre.mermaid').map((node) => ({
      text: node.textContent,
      drawn: node.hasAttribute('data-processed'),
    })),
    themes: page.themes,
    runs: page.runs,
    clipboard: page.clipboard,
    commands: page.commands,
    copied: document.querySelectorAll('[data-copied]').map((button) => button.dataset.copy),
    timers: page.timers.length,
    textareas: document.querySelectorAll('textarea').length,
  };
};

const settle = () => new Promise((resolve) => setImmediate(resolve));

const main = async () => {
  const [pagePath, stepsPath] = process.argv.slice(2);
  const document = createDocument(parsePage(fs.readFileSync(pagePath, 'utf8')));
  const { steps, mermaid } = JSON.parse(fs.readFileSync(stepsPath, 'utf8'));
  const sandbox = createSandbox(document, mermaid);
  const scripts = document.querySelectorAll('script').filter((node) => !node.hasAttribute('src'));
  for (const script of scripts) vm.runInNewContext(script.textContent, sandbox);
  for (const step of steps) {
    STEPS[step.do](document, step);
    await settle();
  }
  process.stdout.write(JSON.stringify(describe(document)));
};

main();
