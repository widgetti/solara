// Stub for sanitize-html. The app bundles alias every 'sanitize-html' import to this module,
// so the core bundle has no sanitizer code. The one real copy is in the internal "sanitizer"
// chunk, which jupyter-controls and output-widget need, and which registers itself here.
import { loadFeature } from './features';

let real: any = null;

export function setSanitizer(sanitizeHtml: any): void {
  real = sanitizeHtml;
  sanitize.defaults = sanitizeHtml.defaults;
}

function escapeHtml(text: string): string {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const sanitize: any = function (dirty: string, options?: any): string {
  if (real) {
    return real(dirty, options);
  }
  // called before the sanitizer chunk ran: never return unsanitized HTML
  loadFeature('sanitizer').catch(console.error);
  return escapeHtml(dirty);
};

// @jupyterlab/apputils' Sanitizer reads these when its module runs (values of sanitize-html 2.x)
sanitize.defaults = {
  allowedSchemes: ['http', 'https', 'ftp', 'mailto', 'tel'],
};

sanitize.simpleTransform = function (newTagName: string, newAttribs?: any, merge?: boolean) {
  merge = merge === undefined ? true : merge;
  newAttribs = newAttribs || {};
  return function (tagName: string, attribs: any) {
    if (merge) {
      for (const attrib in newAttribs) {
        attribs[attrib] = newAttribs[attrib];
      }
    } else {
      attribs = newAttribs;
    }
    return { tagName: newTagName, attribs: attribs };
  };
};

export default sanitize;
