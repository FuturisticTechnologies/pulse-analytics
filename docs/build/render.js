/**
 * Renders the HTML source documents to PDF.
 *
 * Entirely offline: it drives the copy of Chrome already installed on the
 * machine through puppeteer-core, and Mermaid is loaded from node_modules
 * rather than a CDN. Nothing about the project is sent anywhere, and the build
 * works on a locked-down network.
 *
 *   npm install && npm run build
 *
 * ---------------------------------------------------------------------------
 * How the table of contents gets real page numbers
 *
 * Screen layout cannot answer "which page is this heading on". `page-break-before`
 * has no effect outside paged media, so measuring element offsets in the
 * viewport and dividing by a page height is wrong - it reports every heading on
 * page 1 of a document that prints to forty.
 *
 * So the paginator is asked directly. For each heading, everything after it is
 * hidden and the document is printed to a buffer; the page count of that buffer
 * IS the page the heading falls on. It costs one print per entry, which is a few
 * seconds, and it is exact rather than approximately right.
 * ---------------------------------------------------------------------------
 */

const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");

const HERE = __dirname;
const OUT_DIR = path.resolve(HERE, "..");

const DOCUMENTS = [
  {
    source: "architecture.html",
    output: "PulseAnalytics-Architecture.pdf",
    title: "PulseAnalytics · Software Architecture Document",
  },
  {
    source: "brd.html",
    output: "PulseAnalytics-BRD.pdf",
    title: "PulseAnalytics · Business Requirements Document",
  },
];

const PDF_OPTIONS = {
  format: "A4",
  printBackground: true,
  margin: { top: "18mm", bottom: "18mm", left: "16mm", right: "16mm" },
  preferCSSPageSize: false,
};

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].filter(Boolean);

function findChrome() {
  for (const candidate of CHROME_CANDIDATES) {
    if (fs.existsSync(candidate)) return candidate;
  }
  throw new Error(
    "No Chrome or Edge found. Set CHROME_PATH to the executable.\nTried:\n  " +
      CHROME_CANDIDATES.join("\n  ")
  );
}

/**
 * Count pages in a Chrome-produced PDF.
 *
 * page.pdf() returns a Uint8Array, whose toString() ignores an encoding
 * argument and yields comma-separated byte values - so it must be wrapped in a
 * Buffer before any text scanning, or every count silently comes back zero.
 */
function countPages(data) {
  const text = Buffer.from(data).toString("latin1");
  const matches = text.match(/\/Type\s*\/Page[^s]/g);
  return matches ? matches.length : 0;
}

function footerTemplate(title) {
  return `
    <div style="width:100%;font-family:'Segoe UI',system-ui,sans-serif;font-size:8pt;
                color:#898781;padding:0 16mm;display:flex;justify-content:space-between;">
      <span>${title}</span>
      <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
    </div>`;
}

async function waitForDiagrams(page) {
  await page.waitForFunction(() => window.__diagramsReady === true, {
    timeout: 180000,
  });
  const failures = await page.evaluate(() => window.__diagramErrors || []);
  if (failures.length) {
    throw new Error("Mermaid failed to render:\n  " + failures.join("\n  "));
  }
  return page.evaluate(() => document.querySelectorAll(".mermaid svg").length);
}

/**
 * The page each heading falls on, measured by the paginator itself.
 * Only headings the contents page actually references are measured.
 */
async function measureHeadingPages(page) {
  const ids = await page.evaluate(() =>
    [...document.querySelectorAll("[data-toc-for]")].map((el) =>
      el.getAttribute("data-toc-for")
    )
  );

  const pages = {};
  for (const id of ids) {
    const found = await page.evaluate((targetId) => {
      const doc = document.getElementById("doc");
      const target = document.getElementById(targetId);
      if (!doc || !target) return false;
      for (const child of doc.children) {
        const isAfter =
          target.compareDocumentPosition(child) &
          Node.DOCUMENT_POSITION_FOLLOWING;
        child.style.display = isAfter ? "none" : "";
      }
      return true;
    }, id);

    if (!found) {
      pages[id] = { error: "no element with that id" };
      continue;
    }
    const count = countPages(await page.pdf(PDF_OPTIONS));
    pages[id] = count > 0 ? count : { error: "paginator returned zero pages" };
  }

  // Put every element back before the real print.
  await page.evaluate(() => {
    const doc = document.getElementById("doc");
    if (doc) for (const child of doc.children) child.style.display = "";
  });

  return pages;
}

async function render(browser, doc) {
  const sourcePath = path.join(HERE, doc.source);
  if (!fs.existsSync(sourcePath)) {
    throw new Error(`missing source document: ${doc.source}`);
  }

  const page = await browser.newPage();
  await page.setViewport({ width: 794, height: 1123 });
  const consoleErrors = [];
  page.on("pageerror", (err) => consoleErrors.push(err.message));

  const url = "file:///" + sourcePath.split(path.sep).join("/");
  await page.goto(url, { waitUntil: "networkidle0", timeout: 180000 });

  const diagrams = await waitForDiagrams(page);
  if (consoleErrors.length) {
    throw new Error("page errors:\n  " + consoleErrors.join("\n  "));
  }

  const headingPages = await measureHeadingPages(page);
  const unresolved = Object.entries(headingPages)
    .filter(([, v]) => typeof v !== "number")
    .map(([k, v]) => k + " (" + v.error + ")");
  if (unresolved.length) {
    throw new Error(
      "could not resolve contents entries:\n  " + unresolved.join("\n  ")
    );
  }

  await page.evaluate((pages) => {
    document.querySelectorAll("[data-toc-for]").forEach((slot) => {
      slot.textContent = String(pages[slot.getAttribute("data-toc-for")]);
    });
  }, headingPages);

  const pdfPath = path.join(OUT_DIR, doc.output);
  await page.pdf({
    ...PDF_OPTIONS,
    path: pdfPath,
    displayHeaderFooter: true,
    headerTemplate: "<div></div>",
    footerTemplate: footerTemplate(doc.title),
  });

  await page.close();

  const bytes = fs.statSync(pdfPath).size;
  const totalPages = countPages(fs.readFileSync(pdfPath));
  return {
    pdfPath,
    diagrams,
    entries: Object.keys(headingPages).length,
    totalPages,
    bytes,
  };
}

(async () => {
  const executablePath = findChrome();
  console.log(`Chrome:  ${executablePath}`);
  console.log(`Output:  ${OUT_DIR}\n`);

  const browser = await puppeteer.launch({
    executablePath,
    headless: "new",
    args: [
      "--no-sandbox",
      "--disable-dev-shm-usage",
      "--allow-file-access-from-files",
      "--font-render-hinting=none",
    ],
  });

  let failed = false;
  try {
    for (const doc of DOCUMENTS) {
      const started = Date.now();
      process.stdout.write(`Rendering ${doc.source} ... `);
      try {
        const r = await render(browser, doc);
        console.log(
          `ok (${((Date.now() - started) / 1000).toFixed(1)}s)\n` +
            `  -> ${path.basename(r.pdfPath)}  ${r.totalPages} pages, ` +
            `${r.diagrams} diagrams, ${r.entries} contents entries, ` +
            `${(r.bytes / 1024).toFixed(0)} KB`
        );
      } catch (err) {
        failed = true;
        console.log(`FAILED\n  ${err.message}`);
      }
    }
  } finally {
    await browser.close();
  }

  process.exit(failed ? 1 : 0);
})();
