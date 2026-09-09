/**
 * Shared page boot for both documents.
 *
 * Diagram sources live in diagrams.js, not in the HTML. UML notation is full of
 * characters the HTML parser wants for itself - `<<abstract>>` becomes an
 * unknown element, `<|--` starts a tag - and escaping every one of them by hand
 * is both unreadable and a reliable source of silent corruption. Injecting the
 * source with textContent sidesteps the parser completely, and keeps the
 * diagram definitions reviewable on their own.
 */
(async () => {
  window.__diagramErrors = [];

  // Palette from dashboards/streamlit/theme.py, so a diagram here and a chart
  // on the dashboard are recognisably the same system.
  const THEME = {
    background: "#ffffff",
    primaryColor: "#eaf3fe",
    primaryBorderColor: "#2a78d6",
    primaryTextColor: "#0b0b0b",
    secondaryColor: "#fdf3e2",
    secondaryBorderColor: "#eb6834",
    tertiaryColor: "#e9f6e9",
    tertiaryBorderColor: "#1baf7a",
    lineColor: "#52514e",
    textColor: "#0b0b0b",
    mainBkg: "#eaf3fe",
    nodeBorder: "#2a78d6",
    clusterBkg: "#fcfcfb",
    clusterBorder: "#c3c2b7",
    edgeLabelBackground: "#ffffff",
    fontFamily: "Segoe UI, system-ui, sans-serif",
    fontSize: "13px",

    // Sequence diagrams
    actorBkg: "#eaf3fe",
    actorBorder: "#2a78d6",
    actorTextColor: "#0b0b0b",
    actorLineColor: "#c3c2b7",
    signalColor: "#52514e",
    signalTextColor: "#0b0b0b",
    labelBoxBkgColor: "#fcfcfb",
    labelBoxBorderColor: "#c3c2b7",
    loopTextColor: "#52514e",
    noteBkgColor: "#fdf3e2",
    noteBorderColor: "#eb6834",
    noteTextColor: "#0b0b0b",
    sequenceNumberColor: "#ffffff",

    // State diagrams
    labelColor: "#0b0b0b",
    altBackground: "#fcfcfb",
  };

  function inject() {
    const sources = window.DIAGRAMS || {};
    const missing = [];
    document.querySelectorAll("[data-diagram]").forEach((el) => {
      const key = el.getAttribute("data-diagram");
      const src = sources[key];
      if (!src) {
        missing.push(key);
        return;
      }
      // textContent, never innerHTML: the parser never sees the UML.
      el.textContent = src.trim();
    });
    if (missing.length) {
      window.__diagramErrors.push(
        "no source defined for diagram(s): " + missing.join(", ")
      );
    }
  }

  function injectSvg() {
    const sources = window.UML_SVG || {};
    const missing = [];
    document.querySelectorAll("[data-svg]").forEach((el) => {
      const key = el.getAttribute("data-svg");
      const svg = sources[key];
      if (!svg) {
        missing.push(key);
        return;
      }
      // innerHTML is correct here and nowhere else on the page: this markup is
      // authored in uml-svg.js, not derived from anything external.
      el.innerHTML = svg.trim();
    });
    if (missing.length) {
      window.__diagramErrors.push(
        "no SVG defined for figure(s): " + missing.join(", ")
      );
    }
    document.querySelectorAll("[data-svg]").forEach((el) => {
      if (!el.querySelector("svg")) {
        window.__diagramErrors.push(
          "hand-authored SVG did not parse: " + el.getAttribute("data-svg")
        );
      }
    });
  }

  try {
    inject();
    injectSvg();
    mermaid.initialize({
      startOnLoad: false,
      theme: "base",
      themeVariables: THEME,
      fontFamily: "Segoe UI, system-ui, sans-serif",
      // Deterministic ids so re-rendering the document produces byte-identical
      // SVG, and a diff between two builds shows only real changes.
      deterministicIds: true,
      deterministicIDSeed: "pulseanalytics",
      maxTextSize: 200000,
      flowchart: { htmlLabels: true, curve: "basis", padding: 10 },
      sequence: {
        useMaxWidth: true,
        boxMargin: 8,
        mirrorActors: false,
        actorMargin: 42,
        messageFontSize: 12,
        noteFontSize: 11,
      },
      class: { useMaxWidth: true },
      state: { useMaxWidth: true },
      er: { useMaxWidth: true, layoutDirection: "TB", entityPadding: 12 },
      themeCSS: `
        .messageText, .noteText, .labelText { font-size: 12px; }
        .nodeLabel, .edgeLabel { font-size: 12.5px; }
      `,
    });

    await mermaid.run({ querySelector: ".mermaid" });
  } catch (err) {
    window.__diagramErrors.push(String((err && err.message) || err));
  }

  // Every diagram element must have produced an SVG. A silent no-op would
  // otherwise ship a document with blank figures in it.
  document.querySelectorAll(".mermaid").forEach((el) => {
    if (!el.querySelector("svg")) {
      window.__diagramErrors.push(
        "no SVG produced for: " + (el.getAttribute("data-diagram") || "(inline)")
      );
    }
  });

  window.__diagramsReady = true;
})();
