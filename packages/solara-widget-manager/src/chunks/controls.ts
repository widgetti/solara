// feature "jupyter-controls": @jupyter-widgets/controls
import * as controls from '@jupyter-widgets/controls';

// Override DescriptionView with one that doesn't use MathJax, and instead just uses KatexTypesetter
controls.DescriptionView.prototype.typeset = function (element: HTMLElement, text?: string): void {
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
};

export { controls };
