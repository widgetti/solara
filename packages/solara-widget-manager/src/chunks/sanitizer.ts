// internal feature "sanitizer": the one sanitize-html copy, needed by jupyter-controls and output-widget.
// The core bundle aliases 'sanitize-html' to ../sanitize (a stub), this deep import skips that alias.
import sanitizeHtml from 'sanitize-html/index.js';
import { setSanitizer } from '../sanitize';

setSanitizer(sanitizeHtml);

export { sanitizeHtml };
