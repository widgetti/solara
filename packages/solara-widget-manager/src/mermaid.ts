import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: true,
});

export function renderMermaid(): void {
  mermaid.init();
}
