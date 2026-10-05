// eslint-disable-next-line @typescript-eslint/naming-convention
declare interface Window {
  define: any;
  requirejs: any;
}

// TS node resolution ignores the "exports" map, webpack resolves these to katex's ESM build
declare module 'katex/contrib/auto-render';
// the real sanitize-html (the 'sanitize-html' request itself is aliased to ./sanitize by the app bundles)
declare module 'sanitize-html/index.js';
