import renderMathInElement from 'katex/dist/contrib/auto-render';

import { IRenderMime } from '@jupyterlab/rendermime-interfaces';

import { DescriptionView } from '@jupyter-widgets/controls';

let latexDelimiters = [
    { left: '$$', right: '$$', display: true },
    { left: '$', right: '$', display: false },
    { left: '\\(', right: '\\)', display: false },
    { left: '\\[', right: '\\]', display: true }
];

// Override DescriptionView with one that doesn't use MathJax, and instead just uses KatexTypesetter
DescriptionView.prototype.typeset = function(element: HTMLElement, text?: string): void {
    this.displayed.then(() => {
        const widget_manager: any = this.model.widget_manager;
        const latexTypesetter = widget_manager._rendermime?.latexTypesetter;
        if (latexTypesetter) {
          if (text !== void 0) {
            element.textContent = text;
          }
          latexTypesetter.typeset(element);
        }
    });
}

export class KatexTypesetter implements IRenderMime.ILatexTypesetter {
    /**
     * Typeset the math in a node.
     */
    typeset(node: HTMLElement): void {
        renderMathInElement(node, {
            delimiters: latexDelimiters
        });
    }
  }

export function renderKatex(): void {
    renderMathInElement(document, {
        delimiters: latexDelimiters,
    });
}
