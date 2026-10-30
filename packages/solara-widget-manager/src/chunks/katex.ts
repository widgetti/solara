// feature "katex": both imports resolve to the ESM build (katex.mjs), so there is one KaTeX copy
import renderMathInElement from 'katex/contrib/auto-render';
import katex from 'katex';
import 'katex/dist/katex.min.css';

export { katex, renderMathInElement };
