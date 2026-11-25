const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const fromWeb = require('node:module').createRequire(path.resolve('apps/web/package.json'));
const { chromium } = fromWeb('@playwright/test');

async function exportPdf(browser, htmlPath, pdfPath, landscape) {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.goto(pathToFileURL(path.resolve(htmlPath)).href, { waitUntil: 'load' });
  await page.evaluate(async () => {
    await document.fonts.ready;
    const imgs = Array.from(document.querySelectorAll('img'));
    await Promise.all(
      imgs.map(async (img) => {
        if (!img.complete) {
          await new Promise((res) => {
            img.addEventListener('load', res, { once: true });
            img.addEventListener('error', res, { once: true });
          });
        }
        if (img.naturalWidth === 0) {
          throw new Error('Broken image in PDF HTML: ' + img.src);
        }
        await img.decode().catch(() => {});
      })
    );
  });
  await page.pdf({
    path: path.resolve(pdfPath),
    format: 'A4',
    landscape,
    printBackground: true,
    margin: { top: '0mm', right: '0mm', bottom: '0mm', left: '0mm' },
    preferCSSPageSize: true,
  });
  await ctx.close();
  const bytes = fs.statSync(path.resolve(pdfPath)).size;
  console.log(`Generated ${pdfPath} (${(bytes / (1024 * 1024)).toFixed(2)} MB)`);
}

async function main() {
  const mac = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  const browser = await chromium.launch({
    executablePath: process.env.MIRA_CHROME || (fs.existsSync(mac) ? mac : undefined),
  });
  try {
    await exportPdf(
      browser,
      'submission/src/evaluation_report.html',
      'submission/Mira_Evaluation_and_Reliability_Report.pdf',
      false
    );
    await exportPdf(
      browser,
      'submission/src/product_guide.html',
      'submission/Mira_Product_Experience_and_Workflow_Guide.pdf',
      true
    );
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
