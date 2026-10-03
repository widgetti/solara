import { IRenderMime } from '@jupyterlab/rendermime-interfaces';

import { getLoadedFeature, loadFeature } from './features';

const latexDelimiters = [
  { left: '$$', right: '$$', display: true },
  { left: '$', right: '$', display: false },
  { left: '\\(', right: '\\)', display: false },
  { left: '\\[', right: '\\]', display: true }
];
const mathDelimiter = /\$|\\\(|\\\[/;
// the tags KaTeX's auto-render skips
const ignoredTags = new Set(['SCRIPT', 'NOSCRIPT', 'STYLE', 'TEXTAREA', 'PRE', 'CODE', 'OPTION', 'TEMPLATE']);

function hasMath(node: Node): boolean {
  const root = node.nodeType === Node.DOCUMENT_NODE ? (node as Document).body : node;
  if (!root) {
    return false;
  }
  if (root.nodeType === Node.TEXT_NODE) {
    return mathDelimiter.test(root.textContent || '');
  }
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const text = walker.currentNode;
    if (mathDelimiter.test(text.textContent || '')) {
      let parent = text.parentElement;
      while (parent && parent !== root && !ignoredTags.has(parent.tagName)) {
        parent = parent.parentElement;
      }
      if (!parent || parent === root) {
        return true;
      }
    }
  }
  return false;
}

/** The KaTeX chunk: {katex, renderMathInElement}. */
export function loadKatex(): Promise<any> {
  return loadFeature('katex');
}

function typeset(node: HTMLElement | Document): void {
  const chunk = getLoadedFeature('katex');
  if (chunk) {
    chunk.renderMathInElement(node, { delimiters: latexDelimiters });
  } else if (hasMath(node)) {
    // load KaTeX only for text with a math delimiter: DescriptionView typesets
    // every description (e.g. every slider label)
    loadKatex().then(chunk => chunk.renderMathInElement(node, { delimiters: latexDelimiters }));
  }
}

export class KatexTypesetter implements IRenderMime.ILatexTypesetter {
  /**
   * Typeset the math in a node.
   */
  typeset(node: HTMLElement): void {
    typeset(node);
  }
}

export function renderKatex(): void {
  typeset(document);
}
