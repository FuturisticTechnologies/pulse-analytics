/**
 * Independent check of the rendered PDFs.
 *
 * Re-measures each contents entry the same way render.js did, then confirms the
 * numbers are internally consistent: monotonically increasing, never past the
 * last page, and the first section after the front matter starts where it
 * should. A contents page with plausible-looking wrong numbers is worse than
 * one with none.
 */
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PDF_OPTIONS = {
  format: "A4",
  printBackground: true,
  margin: { top: "18mm", bottom: "18mm", left: "16mm", right: "16mm" },
};

const countPages = (data) =>
  (Buffer.from(data).toString("latin1").match(/\/Type\s*\/Page[^s]/g) || []).length;

const DOCS = [
  { src: "architecture.html", pdf: "../PulseAnalytics-Architecture.pdf" },
  { src: "brd.html", pdf: "../PulseAnalytics-BRD.pdf" },
];

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: "new",
    args: ["--no-sandbox", "--allow-file-access-from-files"],
  });

  let problems = 0;

  for (const doc of DOCS) {
    const page = await browser.newPage();
    await page.setViewport({ width: 794, height: 1123 });
    await page.goto("file:///" + path.resolve(doc.src).split(path.sep).join("/"), {
      waitUntil: "networkidle0",
      timeout: 180000,
    });
    await page.waitForFunction(() => window.__diagramsReady === true, { timeout: 180000 });

    const errs = await page.evaluate(() => window.__diagramErrors || []);
    const svgCount = await page.evaluate(
      () => document.querySelectorAll(".mermaid svg, .uml svg").length
    );
    const total = countPages(await page.pdf(PDF_OPTIONS));
    const onDisk = countPages(fs.readFileSync(doc.pdf));

    const ids = await page.evaluate(() =>
      [...document.querySelectorAll("[data-toc-for]")].map((el) =>
        el.getAttribute("data-toc-for")
      )
    );

    const measured = [];
    for (const id of ids) {
      await page.evaluate((t) => {
        const root = document.getElementById("doc");
        const target = document.getElementById(t);
        for (const c of root.children) {
          c.style.display =
            target.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING
              ? "none"
              : "";
        }
      }, id);
      measured.push({ id, page: countPages(await page.pdf(PDF_OPTIONS)) });
    }

    console.log(`\n${doc.src}`);
    console.log(`  diagrams rendered : ${svgCount}`);
    console.log(`  mermaid errors    : ${errs.length ? errs.join("; ") : "none"}`);
    console.log(`  pages (live/disk) : ${total} / ${onDisk}`);

    if (errs.length) problems++;
    if (total !== onDisk) {
      console.log("  ! live render and file on disk disagree on page count");
      problems++;
    }

    // Monotonic, in range, and the body starts after the front matter.
    let prev = 0;
    let ordering = true;
    for (const m of measured) {
      if (m.page < prev) ordering = false;
      if (m.page < 1 || m.page > total) {
        console.log(`  ! ${m.id} -> page ${m.page} is outside 1..${total}`);
        problems++;
      }
      prev = m.page;
    }
    console.log(`  contents entries  : ${measured.length}, ` +
      `pages ${measured[0].page}..${measured[measured.length - 1].page}` +
      `, ${ordering ? "monotonic" : "OUT OF ORDER"}`);
    if (!ordering) problems++;

    const firstBody = measured[0].page;
    if (firstBody < 3) {
      console.log(`  ! first section on page ${firstBody}; cover + contents should precede it`);
      problems++;
    }

    await page.close();
  }

  await browser.close();
  console.log(problems === 0 ? "\nAll checks passed." : `\n${problems} problem(s).`);
  process.exit(problems ? 1 : 0);
})();
