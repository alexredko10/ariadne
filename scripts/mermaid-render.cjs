#!/usr/bin/env node
/**
 * scripts/mermaid-render.cjs
 *
 * Offline Mermaid-to-SVG renderer for Ariadne.
 *
 * Reads Mermaid source from stdin, calls mermaid.parse + mermaid.render
 * inside a jsdom virtual DOM, outputs SVG to stdout.
 *
 * The key trick: mermaid.render() returns an SVG string from pure
 * layout computation — no real browser paint needed. JSDOM provides
 * enough DOM API for the layout engine. SVG text measurement uses
 * a simple stub when the real DOM methods are unavailable.
 *
 * Security:
 *   - securityLevel: 'strict' — disables click handlers, links, forms
 *   - stdin only: no filesystem, network, or shell execution
 *   - stderr for errors only
 *   - SVG output to stdout only
 */

// Stub SVGTextElement.getBBox for mermaid in jsdom — no real layout needed
// mermaid calls getBBox() during layout; we return a fixed bounding box
const origDefineProperty = Object.defineProperty;

const { JSDOM } = require('jsdom');

// Polyfill CSSStyleSheet for mermaid under jsdom
if (typeof globalThis.CSSStyleSheet === 'undefined') {
  globalThis.CSSStyleSheet = class CSSStyleSheet {
    constructor() { this.cssRules = []; }
    insertRule(rule, index) {
      if (index === undefined) index = this.cssRules.length;
      this.cssRules.push({ cssText: rule, type: 1 });
      return index;
    }
    deleteRule(index) { this.cssRules.splice(index, 1); }
  };
}

async function main() {
  // Read all stdin
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const input = Buffer.concat(chunks).toString('utf-8');

  if (!input || !input.trim()) {
    process.stderr.write('ERROR: empty input\n');
    process.exit(1);
  }

  // Build virtual DOM
  const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
    url: 'http://localhost',
    pretendToBeVisual: true,
    resources: 'usable',
  });
  const win = dom.window;

  // Expose required globals for mermaid
  globalThis.window = win;
  globalThis.document = win.document;
  globalThis.navigator = win.navigator;
  globalThis.HTMLElement = win.HTMLElement;
  globalThis.SVGElement = win.SVGElement;
  globalThis.SVGGraphicsElement = win.SVGGraphicsElement;
  globalThis.Element = win.Element;
  globalThis.Node = win.Node;
  globalThis.DocumentFragment = win.DocumentFragment;
  globalThis.DOMParser = win.DOMParser;
  globalThis.MutationObserver = win.MutationObserver;
  globalThis.location = win.location;

  // Stub getBBox on SVG elements — required by mermaid's layout engine
  // JSDOM doesn't implement getBBox; returning a fixed box works because
  // mermaid only needs approximate text dimensions for layout
  if (win.SVGGraphicsElement && !win.SVGGraphicsElement.prototype.getBBox) {
    win.SVGGraphicsElement.prototype.getBBox = function() {
      return { x: 0, y: 0, width: 100, height: 20 };
    };
  }
  if (win.SVGElement && !win.SVGElement.prototype.getBBox) {
    win.SVGElement.prototype.getBBox = function() {
      return { x: 0, y: 0, width: 100, height: 20 };
    };
  }

  // Dynamic import of mermaid (ESM-only in v11)
  const mermaidModule = await import('mermaid');
  const mermaid = mermaidModule.default || mermaidModule;

  // Initialize with strict security
  mermaid.initialize({
    securityLevel: 'strict',
    startOnLoad: false,
    suppressErrorRendering: true,
    fontFamily: 'sans-serif',
  });

  try {
    const { svg } = await mermaid.render('ariadne-diagram', input);
    process.stdout.write(svg);
  } catch (err) {
    process.stderr.write('ERROR: ' + (err.message || String(err)) + '\n');
    process.exit(2);
  }
}

main().catch((err) => {
  process.stderr.write('ERROR: ' + (err.message || String(err)) + '\n');
  process.exit(3);
});
