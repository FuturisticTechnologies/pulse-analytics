# Document build

Renders the two PDF deliverables in `docs/` from HTML source.

```bash
cd docs/build
npm install      # ~2 minutes, downloads mermaid and puppeteer-core only
npm run build    # writes both PDFs into docs/
npm run verify   # independently re-checks the rendered output
```

| Output | Pages | Diagrams |
| --- | ---: | ---: |
| `docs/PulseAnalytics-Architecture.pdf` | 38 | 15 |
| `docs/PulseAnalytics-BRD.pdf` | 38 | 7 |

## Why this toolchain

**Entirely offline.** It drives the copy of Chrome already installed on the
machine through `puppeteer-core`, and Mermaid is loaded from `node_modules`
rather than a CDN. No content is sent anywhere, and the build works on a
locked-down network. `puppeteer-core` rather than `puppeteer` deliberately: the
latter downloads its own ~150 MB Chromium, which this does not need.

**No LaTeX, no pandoc, no Graphviz.** Each would be a large install for a
result Chrome already produces, and none is present on a typical analyst
workstation.

## Files

| File | Role |
| --- | --- |
| `render.js` | Renders both documents. Two passes: measure, then print. |
| `verify.js` | Re-checks the output independently of the renderer. |
| `styles.css` | Print stylesheet. Same palette as `dashboards/streamlit/theme.py`. |
| `boot.js` | Injects diagram sources and hand-authored SVG, then runs Mermaid. |
| `diagrams-architecture.js` | Mermaid sources for the architecture document. |
| `diagrams-brd.js` | Mermaid sources for the BRD. |
| `uml-svg.js` | Hand-authored SVG for the three diagrams Mermaid cannot express. |
| `architecture.html`, `brd.html` | The document content. |

## Three decisions worth knowing about

### Diagram sources live outside the HTML

UML notation collides with the HTML parser: `<<abstract>>` becomes an unknown
element and `<|--` opens a tag. Escaping every occurrence by hand is unreadable
and a reliable source of silent corruption — the first draft lost a class
relationship this way and the parse error was thrown by Mermaid, not by HTML.

So diagram sources sit in `diagrams-*.js` and `boot.js` injects them with
`textContent`, which the parser never touches. It also keeps the diagram
definitions reviewable on their own.

### Contents page numbers are measured, not estimated

Screen layout cannot answer "which page is this heading on". `page-break-before`
has no effect outside paged media, so measuring element offsets in the viewport
and dividing by a page height reports *every* heading on page 1 of a document
that prints to thirty-eight. The first implementation did exactly that and was
confidently wrong.

The paginator is therefore asked directly: for each contents entry, everything
after it is hidden and the document is printed to a buffer, and the page count
of that buffer **is** the page the heading falls on. It costs one print per
entry — about twenty seconds per document — and it is exact.

### Three diagrams are hand-authored SVG

Mermaid covers class, sequence, state, ER and activity diagrams natively and
well. It has no notation for:

- **provided/required interfaces** (the lollipop and socket) on a component
  diagram — a flowchart arrow says "A talks to B", which is a weaker and
  different claim than "A realises `IDatabase` and B consumes it";
- the **3D node and nested artifacts** of a deployment diagram;
- the **actor, ellipse and system boundary** of a use case diagram.

Those three are drawn by hand in `uml-svg.js`. Approximating them with
flowcharts and calling the result UML would not have been honest.

## Changing a document

1. Edit `architecture.html` / `brd.html`, or the diagram source files.
2. `npm run build`.
3. `npm run verify` — confirms every diagram rendered, that no Mermaid error
   was swallowed, and that the contents numbers are monotonic and in range.

A heading referenced by the contents but absent from the body fails the build
with the name of the missing anchor, rather than printing a blank page number.

## Reviewing the diagrams alone

Faster than a full build when iterating on a figure — point a browser at
`architecture.html` directly. Diagrams render on load; only the contents page
numbers need the full build.
