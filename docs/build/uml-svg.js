/**
 * Hand-authored SVG for the diagrams that need true UML notation.
 *
 * Mermaid covers class, sequence, state, ER and activity diagrams natively and
 * well. It has no notation for three things this document needs:
 *
 *   - provided/required interfaces (the lollipop and socket) on a COMPONENT
 *     diagram - a flowchart arrow says "A talks to B", which is a weaker and
 *     different claim than "A realises IDatabase and B consumes it";
 *   - the 3D node and nested artifacts of a DEPLOYMENT diagram;
 *   - the actor, ellipse and system boundary of a USE CASE diagram.
 *
 * Drawing those by hand is the honest option. Approximating them with
 * flowcharts and calling the result UML would not be.
 *
 * Palette matches dashboards/streamlit/theme.py throughout.
 */
window.UML_SVG = {
  /* =======================================================================
     Component diagram - provided and required interfaces
     ======================================================================= */
  components: `
<svg viewBox="0 0 1040 640" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="UML component diagram of the PulseAnalytics modules">
  <defs>
    <marker id="use-arrow" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10" fill="none" stroke="#898781" stroke-width="1.4"/>
    </marker>
    <g id="cmp-icon">
      <rect x="0" y="4" width="18" height="13" fill="#ffffff" stroke="#52514e" stroke-width="1.1"/>
      <rect x="-4" y="6.5" width="8" height="3.5" fill="#ffffff" stroke="#52514e" stroke-width="1.1"/>
      <rect x="-4" y="12" width="8" height="3.5" fill="#ffffff" stroke="#52514e" stroke-width="1.1"/>
    </g>
  </defs>

  <style>
    .cbox  { fill:#eaf3fe; stroke:#2a78d6; stroke-width:1.5; }
    .cbox2 { fill:#fdf3e2; stroke:#eb6834; stroke-width:1.5; }
    .cbox3 { fill:#e9f6e9; stroke:#1baf7a; stroke-width:1.5; }
    .ster  { font:italic 10px 'Segoe UI',sans-serif; fill:#52514e; }
    .cname { font:600 13px 'Segoe UI',sans-serif; fill:#0b0b0b; }
    .cpath { font:10px 'Cascadia Mono',Consolas,monospace; fill:#898781; }
    .iface { font:600 10.5px 'Segoe UI',sans-serif; fill:#0b0b0b; }
    .conn  { stroke:#52514e; stroke-width:1.4; fill:none; }
    .use   { stroke:#898781; stroke-width:1.2; fill:none; stroke-dasharray:5 3;
             marker-end:url(#use-arrow); }
    .usetx { font:italic 9.5px 'Segoe UI',sans-serif; fill:#898781; }
    .grp   { fill:none; stroke:#c3c2b7; stroke-width:1.1; stroke-dasharray:6 4; }
    .grptx { font:600 10px 'Segoe UI',sans-serif; fill:#898781; letter-spacing:.06em; }
  </style>

  <!-- ---- grouping frames ---- -->
  <rect class="grp" x="14" y="22" width="330" height="248" rx="6"/>
  <text class="grptx" x="26" y="40">BATCH INGESTION</text>
  <rect class="grp" x="696" y="22" width="330" height="248" rx="6"/>
  <text class="grptx" x="708" y="40">REAL-TIME INGESTION</text>
  <rect class="grp" x="14" y="404" width="1012" height="220" rx="6"/>
  <text class="grptx" x="26" y="422">TRANSFORMATION, ANALYSIS AND PRESENTATION</text>

  <!-- ---- C1 etl.extract ---- -->
  <rect class="cbox" x="34" y="54" width="196" height="70" rx="3"/>
  <use href="#cmp-icon" x="204" y="60"/>
  <text class="ster"  x="48" y="76">&#171;component&#187;</text>
  <text class="cname" x="48" y="94">Extract</text>
  <text class="cpath" x="48" y="110">etl.extract</text>

  <!-- provided: ISource -->
  <line class="conn" x1="132" y1="124" x2="132" y2="150"/>
  <circle cx="132" cy="157" r="6.5" fill="#ffffff" stroke="#52514e" stroke-width="1.5"/>
  <text class="iface" x="146" y="161">ISourceExtract</text>
  <!-- required by C2 -->
  <path class="conn" d="M 122.5 176 A 9.5 9.5 0 0 0 141.5 176"/>
  <line class="conn" x1="132" y1="176" x2="132" y2="196"/>

  <!-- ---- C2 etl.load ---- -->
  <rect class="cbox" x="34" y="196" width="196" height="70" rx="3"/>
  <use href="#cmp-icon" x="204" y="202"/>
  <text class="ster"  x="48" y="218">&#171;component&#187;</text>
  <text class="cname" x="48" y="236">Load</text>
  <text class="cpath" x="48" y="252">etl.load</text>

  <!-- ---- C3 streaming.producer ---- -->
  <rect class="cbox2" x="810" y="54" width="196" height="70" rx="3"/>
  <use href="#cmp-icon" x="980" y="60"/>
  <text class="ster"  x="824" y="76">&#171;component&#187;</text>
  <text class="cname" x="824" y="94">Event producer</text>
  <text class="cpath" x="824" y="110">streaming.producer</text>

  <line class="conn" x1="908" y1="124" x2="908" y2="150"/>
  <circle cx="908" cy="157" r="6.5" fill="#ffffff" stroke="#52514e" stroke-width="1.5"/>
  <text class="iface" x="922" y="161">IEventBus</text>
  <path class="conn" d="M 898.5 176 A 9.5 9.5 0 0 0 917.5 176"/>
  <line class="conn" x1="908" y1="176" x2="908" y2="196"/>

  <!-- ---- C4 streaming.bus ---- -->
  <rect class="cbox2" x="810" y="196" width="196" height="70" rx="3"/>
  <use href="#cmp-icon" x="980" y="202"/>
  <text class="ster"  x="824" y="218">&#171;component&#187;</text>
  <text class="cname" x="824" y="236">Event bus</text>
  <text class="cpath" x="824" y="252">streaming.bus</text>
  <text class="usetx" x="824" y="264">File | Kafka | Event Hubs</text>

  <!-- ---- C5 Database facade (centre) ---- -->
  <rect class="cbox3" x="422" y="196" width="212" height="82" rx="3"/>
  <use href="#cmp-icon" x="608" y="202"/>
  <text class="ster"  x="436" y="218">&#171;component&#187; &#171;facade&#187;</text>
  <text class="cname" x="436" y="238">Database</text>
  <text class="cpath" x="436" y="254">pulse.db</text>
  <text class="usetx" x="436" y="270">DuckDB and PostgreSQL</text>

  <!-- provided: IDatabase -->
  <line class="conn" x1="528" y1="196" x2="528" y2="168"/>
  <circle cx="528" cy="161" r="6.5" fill="#ffffff" stroke="#52514e" stroke-width="1.5"/>
  <text class="iface" x="542" y="165">IDatabase</text>

  <!-- usage dependencies onto IDatabase -->
  <path class="use" d="M 230 214 C 330 214 400 175 512 161"/>
  <path class="use" d="M 810 218 C 720 218 640 175 544 161"/>
  <path class="use" d="M 200 470 C 300 400 420 230 522 176"/>
  <path class="use" d="M 528 470 C 528 400 528 300 528 176"/>
  <path class="use" d="M 852 470 C 800 400 640 220 542 170"/>
  <text class="usetx" x="300" y="196">&#171;use&#187;</text>

  <!-- ---- C6 streaming.consumer ---- -->
  <rect class="cbox2" x="810" y="300" width="196" height="70" rx="3"/>
  <use href="#cmp-icon" x="980" y="306"/>
  <text class="ster"  x="824" y="322">&#171;component&#187;</text>
  <text class="cname" x="824" y="340">Stream consumer</text>
  <text class="cpath" x="824" y="356">streaming.consumer</text>
  <path class="conn" d="M 900.5 290 A 9.5 9.5 0 0 0 919.5 290"/>
  <line class="conn" x1="910" y1="266" x2="910" y2="290"/>

  <!-- ---- C7 database SQL ---- -->
  <rect class="cbox" x="34" y="470" width="196" height="70" rx="3"/>
  <use href="#cmp-icon" x="204" y="476"/>
  <text class="ster"  x="48" y="492">&#171;component&#187;</text>
  <text class="cname" x="48" y="510">Transformations</text>
  <text class="cpath" x="48" y="526">database/*.sql</text>

  <!-- ---- C8 etl.quality ---- -->
  <rect class="cbox" x="272" y="470" width="196" height="70" rx="3"/>
  <use href="#cmp-icon" x="442" y="476"/>
  <text class="ster"  x="286" y="492">&#171;component&#187;</text>
  <text class="cname" x="286" y="510">Data quality</text>
  <text class="cpath" x="286" y="526">etl.quality</text>

  <!-- ---- C9 curated access ---- -->
  <rect class="cbox3" x="510" y="470" width="212" height="70" rx="3"/>
  <use href="#cmp-icon" x="696" y="476"/>
  <text class="ster"  x="524" y="492">&#171;component&#187;</text>
  <text class="cname" x="524" y="510">Curated access</text>
  <text class="cpath" x="524" y="526">analytics.common.datasets</text>

  <line class="conn" x1="616" y1="540" x2="616" y2="568.5"/>
  <circle cx="616" cy="575" r="6.5" fill="#ffffff" stroke="#52514e" stroke-width="1.5"/>
  <line class="conn" x1="622.5" y1="575" x2="874.5" y2="575"/>
  <line class="conn" x1="884" y1="540" x2="884" y2="565.5"/>
  <path class="conn" d="M 884 565.5 A 9.5 9.5 0 0 1 884 584.5"/>
  <text class="iface" x="748" y="568" text-anchor="middle">ICuratedData</text>

  <!-- ---- C10 presentation ---- -->
  <rect class="cbox" x="764" y="470" width="240" height="70" rx="3"/>
  <use href="#cmp-icon" x="978" y="476"/>
  <text class="ster"  x="778" y="492">&#171;component&#187;</text>
  <text class="cname" x="778" y="510">Presentation</text>
  <text class="cpath" x="778" y="526">dashboards/ &#183; realtime_api</text>

  <!-- ---- legend ---- -->
  <g transform="translate(34,600)">
    <circle cx="6" cy="-4" r="6" fill="#ffffff" stroke="#52514e" stroke-width="1.5"/>
    <text class="usetx" x="18" y="0">provided interface</text>
    <path d="M 150 -13 A 9 9 0 0 0 150 5" fill="none" stroke="#52514e" stroke-width="1.4"/>
    <text class="usetx" x="164" y="0">required interface</text>
    <line x1="290" y1="-4" x2="330" y2="-4" stroke="#898781" stroke-width="1.2"
          stroke-dasharray="5 3" marker-end="url(#use-arrow)"/>
    <text class="usetx" x="338" y="0">&#171;use&#187; dependency</text>
  </g>
</svg>
`,

  /* =======================================================================
     Deployment diagram - the Azure target
     ======================================================================= */
  deployAzure: `
<svg viewBox="0 0 1040 700" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="UML deployment diagram of the Azure target environment">
  <defs>
    <marker id="dep-arrow" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10" fill="none" stroke="#52514e" stroke-width="1.4"/>
    </marker>
  </defs>
  <style>
    .nfront { fill:#eaf3fe; stroke:#2a78d6; stroke-width:1.4; }
    .ntop   { fill:#cde2fb; stroke:#2a78d6; stroke-width:1.4; }
    .nside  { fill:#b7d3f6; stroke:#2a78d6; stroke-width:1.4; }
    .sfront { fill:#fdf3e2; stroke:#eb6834; stroke-width:1.4; }
    .stop   { fill:#fbe4cd; stroke:#eb6834; stroke-width:1.4; }
    .sside  { fill:#f7d6b8; stroke:#eb6834; stroke-width:1.4; }
    .ster   { font:italic 9.5px 'Segoe UI',sans-serif; fill:#52514e; }
    .nname  { font:600 12px 'Segoe UI',sans-serif; fill:#0b0b0b; }
    .ndet   { font:9.5px 'Segoe UI',sans-serif; fill:#898781; }
    .art    { fill:#ffffff; stroke:#52514e; stroke-width:1.1; }
    .artx   { font:10px 'Segoe UI',sans-serif; fill:#0b0b0b; }
    .env    { fill:none; stroke:#c3c2b7; stroke-width:1.3; stroke-dasharray:7 4; }
    .envtx  { font:600 10.5px 'Segoe UI',sans-serif; fill:#52514e; letter-spacing:.05em; }
    .link   { stroke:#52514e; stroke-width:1.3; fill:none; marker-end:url(#dep-arrow); }
    .linktx { font:9.5px 'Segoe UI',sans-serif; fill:#898781; }
  </style>

  <!-- ============ GitHub Actions runner ============ -->
  <g transform="translate(30,40)">
    <polygon class="ntop"  points="0,14 14,0 214,0 200,14"/>
    <polygon class="nside" points="200,14 214,0 214,74 200,88"/>
    <rect    class="nfront" x="0" y="14" width="200" height="74"/>
    <text class="ster"  x="12" y="32">&#171;device&#187;</text>
    <text class="nname" x="12" y="50">GitHub Actions runner</text>
    <text class="ndet"  x="12" y="66">ubuntu-latest, ephemeral</text>
    <text class="ndet"  x="12" y="80">OIDC federated identity</text>
  </g>

  <!-- ============ Azure subscription boundary ============ -->
  <rect class="env" x="290" y="24" width="726" height="600" rx="8"/>
  <text class="envtx" x="304" y="44">AZURE SUBSCRIPTION &#183; rg-pulse-{env}-uks</text>

  <!-- ---- Container Apps environment ---- -->
  <rect class="env" x="308" y="58" width="330" height="196" rx="6"/>
  <text class="envtx" x="320" y="76">&#171;executionEnvironment&#187; CONTAINER APPS</text>

  <g transform="translate(326,88)">
    <polygon class="ntop"  points="0,12 12,0 152,0 140,12"/>
    <polygon class="nside" points="140,12 152,0 152,58 140,70"/>
    <rect    class="nfront" x="0" y="12" width="140" height="58"/>
    <text class="ster"  x="10" y="28">&#171;container&#187;</text>
    <text class="nname" x="10" y="45">Dashboard</text>
    <text class="ndet"  x="10" y="60">Streamlit :8501</text>
  </g>
  <g transform="translate(486,88)">
    <polygon class="ntop"  points="0,12 12,0 132,0 120,12"/>
    <polygon class="nside" points="120,12 132,0 132,58 120,70"/>
    <rect    class="nfront" x="0" y="12" width="120" height="58"/>
    <text class="ster"  x="10" y="28">&#171;container&#187;</text>
    <text class="nname" x="10" y="45">API</text>
    <text class="ndet"  x="10" y="60">FastAPI :8000</text>
  </g>

  <!-- artifact deployed to both -->
  <g transform="translate(340,176)">
    <rect class="art" x="0" y="0" width="266" height="34" rx="2"/>
    <path d="M 252 0 L 252 10 L 262 10" fill="none" stroke="#52514e" stroke-width="1.1"/>
    <text class="ster" x="10" y="14">&#171;artifact&#187;</text>
    <text class="artx" x="10" y="28">pulse/platform:&lt;git-sha&gt; — ONE image, both apps</text>
  </g>

  <!-- ---- Data services ---- -->
  <g transform="translate(680,88)">
    <polygon class="stop"  points="0,12 12,0 172,0 160,12"/>
    <polygon class="sside" points="160,12 172,0 172,70 160,82"/>
    <rect    class="sfront" x="0" y="12" width="160" height="70"/>
    <text class="ster"  x="10" y="28">&#171;device&#187;</text>
    <text class="nname" x="10" y="45">PostgreSQL</text>
    <text class="ndet"  x="10" y="60">Flexible Server 16</text>
    <text class="ndet"  x="10" y="74">TLS enforced</text>
  </g>

  <g transform="translate(680,196)">
    <polygon class="stop"  points="0,12 12,0 172,0 160,12"/>
    <polygon class="sside" points="160,12 172,0 172,70 160,82"/>
    <rect    class="sfront" x="0" y="12" width="160" height="70"/>
    <text class="ster"  x="10" y="28">&#171;device&#187;</text>
    <text class="nname" x="10" y="45">Event Hubs</text>
    <text class="ndet"  x="10" y="60">Kafka protocol :9093</text>
    <text class="ndet"  x="10" y="74">4 hubs, 2 groups</text>
  </g>

  <g transform="translate(680,304)">
    <polygon class="stop"  points="0,12 12,0 172,0 160,12"/>
    <polygon class="sside" points="160,12 172,0 172,70 160,82"/>
    <rect    class="sfront" x="0" y="12" width="160" height="70"/>
    <text class="ster"  x="10" y="28">&#171;device&#187;</text>
    <text class="nname" x="10" y="45">ADLS Gen2</text>
    <text class="ndet"  x="10" y="60">bronze / silver / gold</text>
    <text class="ndet"  x="10" y="74">lifecycle tiering</text>
  </g>

  <!-- ---- Platform services ---- -->
  <g transform="translate(326,300)">
    <polygon class="ntop"  points="0,12 12,0 172,0 160,12"/>
    <polygon class="nside" points="160,12 172,0 172,58 160,70"/>
    <rect    class="nfront" x="0" y="12" width="160" height="58"/>
    <text class="ster"  x="10" y="28">&#171;device&#187;</text>
    <text class="nname" x="10" y="45">Container Registry</text>
    <text class="ndet"  x="10" y="60">pull via managed identity</text>
  </g>

  <g transform="translate(326,392)">
    <polygon class="ntop"  points="0,12 12,0 172,0 160,12"/>
    <polygon class="nside" points="160,12 172,0 172,58 160,70"/>
    <rect    class="nfront" x="0" y="12" width="160" height="58"/>
    <text class="ster"  x="10" y="28">&#171;device&#187;</text>
    <text class="nname" x="10" y="45">Key Vault</text>
    <text class="ndet"  x="10" y="60">every connection string</text>
  </g>

  <g transform="translate(326,484)">
    <polygon class="ntop"  points="0,12 12,0 172,0 160,12"/>
    <polygon class="nside" points="160,12 172,0 172,58 160,70"/>
    <rect    class="nfront" x="0" y="12" width="160" height="58"/>
    <text class="ster"  x="10" y="28">&#171;device&#187;</text>
    <text class="nname" x="10" y="45">Log Analytics</text>
    <text class="ndet"  x="10" y="60">+ Application Insights</text>
  </g>

  <g transform="translate(680,440)">
    <polygon class="stop"  points="0,12 12,0 172,0 160,12"/>
    <polygon class="sside" points="160,12 172,0 172,58 160,70"/>
    <rect    class="sfront" x="0" y="12" width="160" height="58"/>
    <text class="ster"  x="10" y="28">&#171;device&#187;</text>
    <text class="nname" x="10" y="45">Databricks</text>
    <text class="ndet"  x="10" y="60">batch pipeline job</text>
  </g>

  <!-- ---- state backend, outside the estate ---- -->
  <g transform="translate(30,196)">
    <polygon class="ntop"  points="0,12 12,0 212,0 200,12"/>
    <polygon class="nside" points="200,12 212,0 212,58 200,70"/>
    <rect    class="nfront" x="0" y="12" width="200" height="58"/>
    <text class="ster"  x="12" y="28">&#171;device&#187;</text>
    <text class="nname" x="12" y="45">Terraform state</text>
    <text class="ndet"  x="12" y="60">one state key per environment</text>
  </g>

  <!-- ---- communication paths ---- -->
  <!-- Routed around the nodes, not through them. The target nodes already
       state their protocol, so the connectors carry no redundant labels. -->
  <path class="link" d="M 244 84 L 314 84"/>
  <text class="linktx" x="279" y="76" text-anchor="middle">deploys</text>

  <path class="link" d="M 136 128 L 136 190"/>
  <text class="linktx" x="144" y="162">reads and writes state</text>

  <!-- container apps -> data services, leaving from the group edge -->
  <path class="link" d="M 640 118 L 674 118"/>
  <path class="link" d="M 640 150 L 656 150 L 656 232 L 674 232"/>

  <!-- registry -> the artifact the apps pull -->
  <path class="link" d="M 406 296 L 406 218"/>
  <text class="linktx" x="412" y="278">AcrPull</text>

  <!-- key vault -> the apps, routed left of the group -->
  <path class="link" d="M 322 420 L 298 420 L 298 246 L 322 246"/>
  <text class="linktx" x="240" y="350">secrets</text>

  <!-- databricks -> the lake -->
  <path class="link" d="M 760 436 L 760 390"/>
  <text class="linktx" x="768" y="418">reads and writes</text>

  <!-- ---- legend ---- -->
  <g transform="translate(310,652)">
    <polygon class="ntop"  points="0,10 10,0 46,0 36,10"/>
    <polygon class="nside" points="36,10 46,0 46,26 36,36"/>
    <rect    class="nfront" x="0" y="10" width="36" height="26"/>
    <text class="linktx" x="56" y="30">&#171;device&#187; / &#171;executionEnvironment&#187; node</text>
    <rect class="art" x="330" y="12" width="70" height="22" rx="2"/>
    <text class="linktx" x="410" y="30">&#171;artifact&#187; deployed unit</text>
    <line x1="580" y1="24" x2="620" y2="24" stroke="#52514e" stroke-width="1.3"
          marker-end="url(#dep-arrow)"/>
    <text class="linktx" x="628" y="28">communication path</text>
  </g>
</svg>
`,

  /* =======================================================================
     Use case diagram - actors, system boundary, use cases  (BRD)
     ======================================================================= */
  useCases: `
<svg viewBox="0 0 1040 760" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="UML use case diagram for PulseAnalytics">
  <defs>
    <marker id="uc-arrow" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10" fill="none" stroke="#898781" stroke-width="1.3"/>
    </marker>
    <g id="stickman">
      <circle cx="0" cy="-26" r="9" fill="#ffffff" stroke="#2a78d6" stroke-width="1.8"/>
      <line x1="0" y1="-17" x2="0" y2="6" stroke="#2a78d6" stroke-width="1.8"/>
      <line x1="-13" y1="-8" x2="13" y2="-8" stroke="#2a78d6" stroke-width="1.8"/>
      <line x1="0" y1="6" x2="-11" y2="24" stroke="#2a78d6" stroke-width="1.8"/>
      <line x1="0" y1="6" x2="11" y2="24" stroke="#2a78d6" stroke-width="1.8"/>
    </g>
    <g id="stickman2">
      <circle cx="0" cy="-26" r="9" fill="#ffffff" stroke="#898781" stroke-width="1.8"/>
      <line x1="0" y1="-17" x2="0" y2="6" stroke="#898781" stroke-width="1.8"/>
      <line x1="-13" y1="-8" x2="13" y2="-8" stroke="#898781" stroke-width="1.8"/>
      <line x1="0" y1="6" x2="-11" y2="24" stroke="#898781" stroke-width="1.8"/>
      <line x1="0" y1="6" x2="11" y2="24" stroke="#898781" stroke-width="1.8"/>
    </g>
  </defs>
  <style>
    .uc      { fill:#eaf3fe; stroke:#2a78d6; stroke-width:1.4; }
    .uc2     { fill:#e9f6e9; stroke:#1baf7a; stroke-width:1.4; }
    .uctx    { font:11px 'Segoe UI',sans-serif; fill:#0b0b0b; text-anchor:middle; }
    .ucid    { font:600 9px 'Cascadia Mono',Consolas,monospace; fill:#2a78d6; text-anchor:middle; }
    .actor   { font:600 11px 'Segoe UI',sans-serif; fill:#0b0b0b; text-anchor:middle; }
    .actor2  { font:600 11px 'Segoe UI',sans-serif; fill:#52514e; text-anchor:middle; }
    .assoc   { stroke:#52514e; stroke-width:1.1; fill:none; }
    .rel     { stroke:#898781; stroke-width:1.1; fill:none; stroke-dasharray:5 3;
               marker-end:url(#uc-arrow); }
    .reltx   { font:italic 9px 'Segoe UI',sans-serif; fill:#898781; text-anchor:middle; }
    .bnd     { fill:#fcfcfb; stroke:#52514e; stroke-width:1.5; }
    .bndtx   { font:600 12px 'Segoe UI',sans-serif; fill:#0b0b0b; text-anchor:middle; }
  </style>

  <!-- ---- system boundary ---- -->
  <rect class="bnd" x="250" y="30" width="540" height="700" rx="4"/>
  <text class="bndtx" x="520" y="56">PulseAnalytics</text>
  <line x1="250" y1="68" x2="790" y2="68" stroke="#c3c2b7" stroke-width="1"/>

  <!-- ================= primary actors (left) ================= -->
  <g transform="translate(110,130)"><use href="#stickman"/>
    <text class="actor" x="0" y="42">Executive</text></g>
  <g transform="translate(110,270)"><use href="#stickman"/>
    <text class="actor" x="0" y="42">Marketing</text><text class="actor" x="0" y="56">manager</text></g>
  <g transform="translate(110,420)"><use href="#stickman"/>
    <text class="actor" x="0" y="42">Merchandising</text><text class="actor" x="0" y="56">manager</text></g>
  <g transform="translate(110,570)"><use href="#stickman"/>
    <text class="actor" x="0" y="42">Operations</text><text class="actor" x="0" y="56">analyst</text></g>

  <!-- ================= secondary actors (right) ================= -->
  <g transform="translate(930,150)"><use href="#stickman2"/>
    <text class="actor2" x="0" y="42">Order system</text></g>
  <g transform="translate(930,300)"><use href="#stickman2"/>
    <text class="actor2" x="0" y="42">Payment</text><text class="actor2" x="0" y="56">gateway</text></g>
  <g transform="translate(930,450)"><use href="#stickman2"/>
    <text class="actor2" x="0" y="42">FX service</text></g>
  <g transform="translate(930,600)"><use href="#stickman2"/>
    <text class="actor2" x="0" y="42">Data analyst</text></g>

  <!-- ================= use cases ================= -->
  <g><ellipse class="uc" cx="420" cy="120" rx="118" ry="30"/>
     <text class="ucid" x="420" y="112">UC-01</text>
     <text class="uctx" x="420" y="128">Review trading performance</text></g>

  <g><ellipse class="uc" cx="420" cy="205" rx="118" ry="30"/>
     <text class="ucid" x="420" y="197">UC-02</text>
     <text class="uctx" x="420" y="213">Analyse revenue drivers</text></g>

  <g><ellipse class="uc" cx="420" cy="290" rx="118" ry="30"/>
     <text class="ucid" x="420" y="282">UC-03</text>
     <text class="uctx" x="420" y="298">Evaluate campaign return</text></g>

  <g><ellipse class="uc" cx="420" cy="375" rx="118" ry="30"/>
     <text class="ucid" x="420" y="367">UC-04</text>
     <text class="uctx" x="420" y="383">Segment the customer base</text></g>

  <g><ellipse class="uc" cx="420" cy="460" rx="118" ry="30"/>
     <text class="ucid" x="420" y="452">UC-05</text>
     <text class="uctx" x="420" y="468">Target customers at risk</text></g>

  <g><ellipse class="uc" cx="420" cy="545" rx="118" ry="30"/>
     <text class="ucid" x="420" y="537">UC-06</text>
     <text class="uctx" x="420" y="553">Plan replenishment</text></g>

  <g><ellipse class="uc" cx="420" cy="630" rx="118" ry="30"/>
     <text class="ucid" x="420" y="622">UC-07</text>
     <text class="uctx" x="420" y="638">Monitor live trading</text></g>

  <g><ellipse class="uc" cx="420" cy="700" rx="118" ry="26"/>
     <text class="ucid" x="420" y="694">UC-08</text>
     <text class="uctx" x="420" y="710">Forecast demand</text></g>

  <!-- included / supporting use cases (right column) -->
  <g><ellipse class="uc2" cx="666" cy="163" rx="104" ry="27"/>
     <text class="ucid" x="666" y="157">UC-09</text>
     <text class="uctx" x="666" y="172">Ingest batch extract</text></g>

  <g><ellipse class="uc2" cx="666" cy="248" rx="104" ry="27"/>
     <text class="ucid" x="666" y="242">UC-10</text>
     <text class="uctx" x="666" y="257">Ingest live events</text></g>

  <g><ellipse class="uc2" cx="666" cy="333" rx="104" ry="27"/>
     <text class="ucid" x="666" y="327">UC-11</text>
     <text class="uctx" x="666" y="342">Enforce data quality</text></g>

  <g><ellipse class="uc2" cx="666" cy="418" rx="104" ry="27"/>
     <text class="ucid" x="666" y="412">UC-12</text>
     <text class="uctx" x="666" y="427">Restate to local currency</text></g>

  <g><ellipse class="uc2" cx="666" cy="600" rx="104" ry="27"/>
     <text class="ucid" x="666" y="594">UC-13</text>
     <text class="uctx" x="666" y="609">Operate the pipeline</text></g>

  <!-- ================= actor associations ================= -->
  <line class="assoc" x1="150" y1="130" x2="302" y2="120"/>
  <line class="assoc" x1="150" y1="140" x2="302" y2="205"/>

  <line class="assoc" x1="150" y1="270" x2="302" y2="290"/>
  <line class="assoc" x1="150" y1="278" x2="302" y2="375"/>
  <line class="assoc" x1="150" y1="286" x2="302" y2="460"/>

  <line class="assoc" x1="150" y1="420" x2="302" y2="212"/>
  <line class="assoc" x1="150" y1="428" x2="302" y2="545"/>
  <line class="assoc" x1="150" y1="436" x2="302" y2="700"/>

  <line class="assoc" x1="150" y1="570" x2="302" y2="630"/>
  <line class="assoc" x1="150" y1="578" x2="302" y2="552"/>

  <line class="assoc" x1="890" y1="150" x2="770" y2="163"/>
  <line class="assoc" x1="890" y1="300" x2="770" y2="255"/>
  <line class="assoc" x1="890" y1="450" x2="770" y2="424"/>
  <line class="assoc" x1="890" y1="600" x2="770" y2="600"/>

  <!-- ================= include / extend ================= -->
  <path class="rel" d="M 538 128 C 580 140 600 150 566 158"/>
  <text class="reltx" x="574" y="120">&#171;include&#187;</text>

  <path class="rel" d="M 538 632 C 580 620 600 600 566 340"/>
  <text class="reltx" x="600" y="520">&#171;include&#187;</text>

  <path class="rel" d="M 538 212 C 590 230 600 300 566 330"/>
  <text class="reltx" x="596" y="284">&#171;include&#187;</text>

  <path class="rel" d="M 538 296 L 566 412"/>
  <text class="reltx" x="536" y="368">&#171;extend&#187;</text>

  <path class="rel" d="M 538 624 L 566 254"/>

  <!-- ---- legend ---- -->
  <g transform="translate(258,748)">
    <text class="reltx" x="0" y="0" style="text-anchor:start">
      Blue = business-facing use case &#183; Green = supporting use case &#183;
      dashed = &#171;include&#187; / &#171;extend&#187;
    </text>
  </g>
</svg>
`,
};
