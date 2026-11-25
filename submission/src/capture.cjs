const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const fromWeb = require('node:module').createRequire(path.resolve('apps/web/package.json'));
const { chromium } = fromWeb('@playwright/test');

const base = 'http://127.0.0.1:5175';
const home = base + '/workspace/index.html';
const api = process.env.RECORD_API;
const outDir = process.env.SHOTS_OUT;

assert.match(api || '', /^http:\/\/127\.0\.0\.1:\d+$/);
fs.mkdirSync(outDir, { recursive: true });

function readCred(role) {
  const email = role + '.demo@ceyloncompass.example';
  const doc = fs.readFileSync('docs/system-audit/CLEAN_DATABASE_RESET.md', 'utf8');
  const line = doc.split('\n').find((l) => l.includes('`' + email + '`') && l.includes('password:'));
  const password = line?.match(/password: `([^`]+)`/)?.[1];
  assert(password, 'Missing synthetic demo password for ' + role);
  return { email, password };
}

async function waitImagesAndFonts(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    const imgs = Array.from(document.querySelectorAll('img'));
    await Promise.all(
      imgs.map(async (img) => {
        if (!img.complete) {
          await new Promise((res) => {
            img.addEventListener('load', res, { once: true });
            img.addEventListener('error', res, { once: true });
            setTimeout(res, 4000);
          });
        }
        try {
          if (img.naturalWidth > 0) await img.decode();
        } catch {}
      })
    );
  });
  await page.waitForTimeout(350);
}

async function shot(page, filename) {
  await waitImagesAndFonts(page);
  const dest = path.join(outDir, filename);
  await page.screenshot({ path: dest, fullPage: false });
  console.log('Captured:', filename);
}

async function attachApiProxy(ctx) {
  await ctx.route('**/api/**', async (route) => {
    const u = new URL(route.request().url());
    if (u.origin !== base) return route.abort();
    try {
      const res = await route.fetch({ url: api + u.pathname + u.search, maxRedirects: 0, timeout: 60000 });
      await route.fulfill({ response: res });
      await res.dispose();
    } catch {
      await route.abort().catch(() => {});
    }
  });
}

async function sendMira(page, prompt) {
  const field = page.getByPlaceholder("Tell Mira what you're looking for...");
  await field.fill(prompt);
  const [resp] = await Promise.all([
    page.waitForResponse((r) => new URL(r.url()).pathname === '/api/agent' && r.request().method() === 'POST', { timeout: 60000 }),
    page.getByRole('button', { name: 'Send message' }).click(),
  ]);
  assert.equal(resp.status(), 200);
  await resp.finished();
  await page.waitForTimeout(500);
}

async function main() {
  const mac = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  const browser = await chromium.launch({
    executablePath: process.env.MIRA_CHROME || (fs.existsSync(mac) ? mac : undefined),
  });
  const fixesOnly = Boolean(process.env.FIXES_ONLY);

  try {
    // 1. Desktop 1440x900 @2x — Public & Traveller browsing pages
    if (!process.env.SKIP_TRAVELLER) {
      const ctx = await browser.newContext({
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 2,
        serviceWorkers: 'block',
      });
      await attachApiProxy(ctx);
      const page = await ctx.newPage();
      page.setDefaultTimeout(15000);

      if (!fixesOnly) {
        await page.goto(home);
        await page.evaluate(() => window.scrollTo(0, 0));
        await shot(page, 'home-hero.png');

        await page.evaluate(() => window.scrollTo(0, 760));
        await shot(page, 'home-featured.png');

        await page.goto(home + '#/explore');
        await page.evaluate(() => window.scrollTo(0, 0));
        await shot(page, 'explore.png');

        await page.goto(home + '#/destinations');
        await page.evaluate(() => window.scrollTo(0, 0));
        await shot(page, 'destinations.png');
      }

      await page.goto(home + '#/destinations/ella');
      await page.evaluate(() => window.scrollTo(0, 0));
      await shot(page, 'destination-ella.png');

      if (!fixesOnly) {
        await page.goto(home + '#/tours');
        await page.evaluate(() => window.scrollTo(0, 0));
        await shot(page, 'tours.png');
      }

      await page.goto(home + '#/tours/sigiriya-minneriya-day-tour-from-kandy');
      await page.evaluate(() => window.scrollTo(0, 0));
      await shot(page, 'tour-detail-sigiriya.png');

      await page.goto(home + '#/policies/booking-and-payment');
      await page.evaluate(() => window.scrollTo(0, 0));
      await shot(page, 'policy-payment.png');

      if (!fixesOnly) {
        await page.goto(home + '#/login');
        await page.evaluate(() => window.scrollTo(0, 0));
        await shot(page, 'login.png');

        await page.goto(home + '#/register');
        await page.evaluate(() => window.scrollTo(0, 0));
        await shot(page, 'register.png');

        // Sign in as synthetic traveller and capture profile
        const trav = readCred('traveller');
        await page.goto(home + '#/login');
        await page.locator('#login-email').fill(trav.email);
        await page.locator('#login-password').fill(trav.password);
        await page.locator('form button[type="submit"]').click();
        await page.waitForURL(/#\/profile/, { timeout: 15000 });
        await page.waitForTimeout(800);
        await shot(page, 'traveller-profile.png');

        // Sign out and verify guest nav returns
        await page.getByRole('button', { name: /Sign Out/i }).first().click();
        await page.waitForTimeout(600);
      }

      await page.goto(home + '#/mira');
      if (!fixesOnly) {
        await shot(page, 'mira-new.png');
      }

      // TravellerPicker + TourCard turn
      await sendMira(page, 'Sigiriya day trip');
      await shot(page, 'mira-traveller-picker.png');

      if (!fixesOnly) {
        // Discovery turn -> TourCard + DestinationHighlight
        await page.getByRole('button', { name: 'New Trip' }).click();
        await page.waitForTimeout(300);
        await sendMira(page, 'I want to explore Sigiriya');
        await shot(page, 'mira-picker-tourcard.png');

        // Quick booker quote + mock decline recovery
        await sendMira(page, 'Sigiriya day trip for two adults on 10 January 2027');
        const quoteRegion = page.getByRole('region', { name: 'Verified quote', exact: true });
        await quoteRegion.waitFor();
        const select = quoteRegion.getByRole('combobox');
        if (await select.count()) {
          await select.selectOption('declined');
          await quoteRegion.getByRole('button', { name: 'Try mock booking' }).click();
          await quoteRegion.getByRole('status').waitFor();
        }
        await shot(page, 'mira-quick-decline.png');
      }

      await ctx.close();
    }

    // 2. Desktop 1440x900 @2x — Staff Console & Governance
    {
      const ctx = await browser.newContext({
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 2,
        serviceWorkers: 'block',
      });
      await attachApiProxy(ctx);
      const page = await ctx.newPage();
      page.setDefaultTimeout(15000);

      await page.goto(base + '/staff');
      if (!fixesOnly) {
        await shot(page, 'staff-signin.png');
      }

      const staffCred = readCred('staff');
      await page.getByLabel('Staff Email').fill(staffCred.email);
      await page.locator('input[type=password]').fill(staffCred.password);
      await page.getByRole('button', { name: 'Sign In to Staff Console' }).click();
      await page.getByRole('button', { name: 'Enquiries' }).waitFor();
      await page.waitForTimeout(600);
      await page.evaluate(() => window.scrollTo(0, 0));
      await shot(page, 'staff-overview-eval.png');

      // Enquiries tab with ENQ-2026-85BCD416 selected
      await page.getByRole('button', { name: 'Enquiries' }).click();
      await page.waitForTimeout(500);
      await page.getByRole('button', { name: /ENQ-2026-85BCD416/ }).click();
      await page.waitForTimeout(500);
      if (!fixesOnly) {
        await page.evaluate(() => window.scrollTo(0, 0));
        await shot(page, 'staff-enquiries-top.png');
      }

      // Scroll Verified Quote & Margin (Staff Only) into center
      const finHeading = page.getByText('Verified Quote & Margin (Staff Only)', { exact: true });
      await finHeading.scrollIntoViewIfNeeded();
      await finHeading.evaluate((el) => el.scrollIntoView({ block: 'center' }));
      await page.waitForTimeout(300);
      await shot(page, 'staff-enquiries-detail.png');

      // Open trace inspector and center the trace JSON box
      await page.getByRole('button', { name: 'Inspect Trace' }).click();
      await page.waitForTimeout(500);
      const tracePre = page.locator('pre').filter({ hasText: 'validated_ui' }).first();
      await tracePre.waitFor();
      await tracePre.evaluate((el) => el.scrollIntoView({ block: 'center' }));
      await page.waitForTimeout(300);
      await shot(page, 'staff-trace-inspector.png');

      if (!fixesOnly) {
        await page.getByRole('button', { name: 'Content Review' }).click();
        await page.waitForTimeout(400);
        const promptBox = page.getByPlaceholder(/Prepare a private Hill Country/);
        await promptBox.fill('Add a 5-day Hill Country tea and train journey using published Ella material');
        const [draftResp] = await Promise.all([
          page.waitForResponse((r) => r.url().endsWith('/api/staff/drafts') && r.request().method() === 'POST'),
          page.getByRole('button', { name: 'Create Draft' }).click(),
        ]);
        const created = await draftResp.json();
        await page.waitForTimeout(500);
        const listResp = await page.evaluate(async () => (await fetch('/api/staff/drafts')).json());
        const draftObj = listResp.find((d) => d.id === created.id) || listResp[0];
        const draftTitleRe = new RegExp(draftObj.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
        await page.getByRole('button', { name: draftTitleRe }).first().click();
        await page.waitForTimeout(400);
        await page.evaluate(() => window.scrollTo(0, 180));
        await shot(page, 'staff-draft-restricted.png');

        await page.getByRole('button', { name: 'Sign out' }).click();
        await page.waitForTimeout(400);
        const approverCred = readCred('approver');
        await page.getByLabel('Staff Email').fill(approverCred.email);
        await page.locator('input[type=password]').fill(approverCred.password);
        await page.getByRole('button', { name: 'Sign In to Staff Console' }).click();
        await page.getByRole('button', { name: 'Content Review' }).waitFor();
        await page.getByRole('button', { name: 'Content Review' }).click();
        await page.waitForTimeout(400);
        await page.getByRole('button', { name: draftTitleRe }).first().click();
        await page.waitForTimeout(400);
        await page.evaluate(() => window.scrollTo(0, 180));
        await shot(page, 'staff-approver-review.png');

        const approveBtn = page.getByRole('button', { name: 'Approve Content' });
        if (await approveBtn.count()) {
          await approveBtn.click();
          await page.waitForTimeout(400);
        }
        const publishBtn = page.getByRole('button', { name: /Approve & Publish/ });
        if (await publishBtn.count()) {
          await publishBtn.click();
          await page.waitForTimeout(600);
        }
        await shot(page, 'staff-approver-published.png');
      }

      // Rate Preview tab with live calculation
      await page.getByRole('button', { name: 'Rate Preview' }).click();
      await page.waitForTimeout(400);
      await page.getByRole('button', { name: 'Run Rate Preview' }).click();
      await page.waitForTimeout(600);
      await page.evaluate(() => window.scrollTo(0, 180));
      await shot(page, 'staff-rate-preview.png');

      await ctx.close();
    }

    // 3. Mobile 390x844 @2x — Responsive experience
    if (!fixesOnly) {
      const ctx = await browser.newContext({
        viewport: { width: 390, height: 844 },
        deviceScaleFactor: 2,
        isMobile: true,
        hasTouch: true,
        serviceWorkers: 'block',
      });
      await attachApiProxy(ctx);
      const page = await ctx.newPage();
      page.setDefaultTimeout(15000);

      await page.goto(home);
      await shot(page, 'mobile-home.png');

      const menuBtn = page.getByRole('button', { name: 'Toggle menu' });
      if (await menuBtn.count()) {
        await menuBtn.click();
        await page.waitForTimeout(300);
        await shot(page, 'mobile-nav.png');
        await menuBtn.click().catch(() => {});
      }

      await page.goto(home + '#/mira');
      await waitImagesAndFonts(page);
      await sendMira(page, 'Sigiriya day trip for two adults on 10 January 2027');
      await shot(page, 'mobile-mira-chat.png');

      const journeyTab = page.getByRole('button', { name: /Journey|Workspace/i }).first();
      if (await journeyTab.count()) {
        await journeyTab.click();
        await page.waitForTimeout(400);
      }
      await shot(page, 'mobile-mira-journey.png');

      await ctx.close();
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
