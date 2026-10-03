import { IRenderMime } from '@jupyterlab/rendermime-interfaces';

import { getLoadedFeature, loadFeature } from './features';

const latexDelimiters = [
  { left: '$$', right: '$$', display: true },
  { left: '$', right: '$', display: false },
  { left: '\\(', right: '\\)', display: false },
  { left: '\\[', right: '\\]', display: true }
];
// KaTeX's auto-render typesets only between a left and a right delimiter, in one run of sibling
// text nodes. This finds a superset of that, so a single '$' (e.g. a label 'Price ($)') does not load KaTeX.
const mathPair = /\$[^$]*\$|\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\]/;
// the tags KaTeX's auto-render skips
const ignoredTags = new Set(['SCRIPT', 'NOSCRIPT', 'STYLE', 'TEXTAREA', 'PRE', 'CODE', 'OPTION', 'TEMPLATE']);

// the text of node and of the text nodes right after it (auto-render joins those)
function textRun(node: Node): string {
  let text = node.textContent || '';
  for (let sibling = node.nextSibling; sibling && sibling.nodeType === Node.TEXT_NODE; sibling = sibling.nextSibling) {
    text += sibling.textContent || '';
  }
  return text;
}

function hasMath(node: Node): boolean {
  const root = node.nodeType === Node.DOCUMENT_NODE ? (node as Document).body : node;
  if (!root) {
    return false;
  }
  if (root.nodeType === Node.TEXT_NODE) {
    return mathPair.test(root.textContent || '');
  }
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const text = walker.currentNode;
    const previous = text.previousSibling;
    if (previous && previous.nodeType === Node.TEXT_NODE) {
      // part of the run of the text node before it
      continue;
    }
    if (mathPair.test(textRun(text))) {
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
