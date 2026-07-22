const fs = require('fs');
const path = require('path');
const { chromium, webkit } = require('playwright');

const baseUrl = process.env.SITE_URL || 'http://127.0.0.1:8766/';
const outputDir = path.resolve(process.env.QA_DIR || 'qa');
fs.mkdirSync(outputDir, { recursive: true });

const viewports = [
  [320, 850], [360, 800], [390, 844], [428, 926], [768, 1024],
  [844, 390], [900, 900], [901, 900], [1440, 900],
];
const screenshotWidths = new Set(['320x850', '390x844', '844x390', '1440x900']);
const failures = [];

function check(condition, message) {
  if (!condition) failures.push(message);
}

async function inspectViewport(browser, width, height, options = {}) {
  const key = `${width}x${height}${options.suffix || ''}`;
  const context = await browser.newContext({
    viewport: { width, height },
    reducedMotion: options.reducedMotion || 'no-preference',
    forcedColors: options.forcedColors || 'none',
    isMobile: Boolean(options.isMobile),
    hasTouch: Boolean(options.hasTouch),
  });
  const page = await context.newPage();
  const runtimeErrors = [];
  page.on('console', message => { if (message.type() === 'error') runtimeErrors.push(`console: ${message.text()}`); });
  page.on('pageerror', error => runtimeErrors.push(`pageerror: ${error.message}`));
  page.on('requestfailed', request => runtimeErrors.push(`requestfailed: ${request.url()} ${request.failure()?.errorText || ''}`));

  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.evaluate(async () => {
    for (let y = 0; y < document.documentElement.scrollHeight; y += Math.max(300, window.innerHeight * .75)) {
      window.scrollTo(0, y);
      await new Promise(resolve => setTimeout(resolve, 20));
    }
    await Promise.all(Array.from(document.images, image => image.decode().catch(() => undefined)));
    window.scrollTo(0, 0);
  });

  const result = await page.evaluate(() => {
    const visible = element => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    };
    const doc = document.documentElement;
    const actions = document.querySelector('.hero-actions').getBoundingClientRect();
    const stats = document.querySelector('.hero-stats').getBoundingClientRect();
    const collision = Math.max(0, Math.min(actions.bottom, stats.bottom) - Math.max(actions.top, stats.top));
    const controls = Array.from(document.querySelectorAll('.button,.source-links a,.menu-toggle,#primary-nav a,.mobile-cta a,.gallery-item a,.lightbox button,.comp-map-legend button,.comp-toolbar button,.comp-details summary,.comp-map-link,.location-links a'))
      .filter(visible)
      .map(element => ({
        text: element.textContent.trim().replace(/\s+/g, ' '),
        width: Math.round(element.getBoundingClientRect().width * 10) / 10,
        height: Math.round(element.getBoundingClientRect().height * 10) / 10,
      }));
    const clipped = Array.from(document.querySelectorAll('h1,h2,h3,p,a,button,b,span'))
      .filter(visible)
      .filter(element => !element.classList.contains('sr-only'))
      .filter(element => !element.closest('.table-shell'))
      .filter(element => {
        const style = getComputedStyle(element);
        return /(hidden|clip)/.test(style.overflow + style.overflowX + style.overflowY) &&
          (element.scrollWidth > element.clientWidth + 1 || element.scrollHeight > element.clientHeight + 1);
      })
      .map(element => `${element.tagName.toLowerCase()}.${element.className || ''}:${element.textContent.trim().slice(0, 50)}`);
    const tables = Array.from(document.querySelectorAll('.table-shell')).map(region => {
      const firstCell = region.querySelector('th:first-child,td:first-child');
      return {
        tabindex: region.getAttribute('tabindex'),
        role: region.getAttribute('role'),
        label: region.getAttribute('aria-label'),
        overflows: region.scrollWidth > region.clientWidth + 1,
        hasCue: Boolean(region.parentElement.querySelector('.table-scroll-cue')),
        sticky: firstCell ? getComputedStyle(firstCell).position === 'sticky' : false,
      };
    });
    const images = Array.from(document.images).map(img => ({ src: img.getAttribute('src'), alt: img.getAttribute('alt'), complete: img.complete, naturalWidth: img.naturalWidth }));
    const hashLinks = Array.from(document.querySelectorAll('a[href^="#"]')).map(link => link.getAttribute('href')).filter(href => href !== '#');
    return {
      documentOverflow: doc.scrollWidth - doc.clientWidth,
      heroCollision: collision,
      controls,
      clipped,
      tables,
      images,
      compCount: document.querySelectorAll('[data-comp-card]').length,
      compMapButtons: document.querySelectorAll('[data-comp-target]').length,
      galleryCount: document.querySelectorAll('[data-gallery-link]').length,
      hasGalleryDialog: Boolean(document.querySelector('[data-gallery-dialog]')),
      h1Count: document.querySelectorAll('h1').length,
      landmarks: { main: Boolean(document.querySelector('main')), nav: Boolean(document.querySelector('nav')), footer: Boolean(document.querySelector('footer')) },
      brokenAnchors: hashLinks.filter(href => !document.querySelector(href)),
      unresolved: /{{|}}|TODO|PLACEHOLDER/i.test(document.documentElement.innerHTML),
      noindex: document.querySelector('meta[name="robots"]')?.content.includes('noindex') || false,
    };
  });

  check(result.documentOverflow <= 1, `${key}: document overflow ${result.documentOverflow}px`);
  check(result.heroCollision <= 1, `${key}: hero actions overlap KPI strip by ${result.heroCollision}px`);
  result.controls.forEach(control => check(control.height >= 44 && control.width >= 44, `${key}: undersized control "${control.text}" ${control.width}x${control.height}`));
  check(result.clipped.length === 0, `${key}: clipped text ${result.clipped.join(', ')}`);
  check(result.h1Count === 1, `${key}: expected one H1, found ${result.h1Count}`);
  check(Object.values(result.landmarks).every(Boolean), `${key}: missing landmark ${JSON.stringify(result.landmarks)}`);
  check(result.brokenAnchors.length === 0, `${key}: broken anchors ${result.brokenAnchors.join(', ')}`);
  check(!result.unresolved, `${key}: unresolved template or placeholder text`);
  check(result.noindex, `${key}: privacy noindex missing`);
  check(result.compCount === 6, `${key}: expected six sale comparables, found ${result.compCount}`);
  check(result.compMapButtons === 6, `${key}: expected six interactive map legend controls, found ${result.compMapButtons}`);
  check(result.galleryCount >= 12, `${key}: expected at least 12 gallery images, found ${result.galleryCount}`);
  check(result.hasGalleryDialog, `${key}: accessible gallery dialog missing`);
  result.images.forEach(image => {
    check(Boolean(image.alt), `${key}: missing alt text on ${image.src}`);
    check(image.complete && image.naturalWidth > 0, `${key}: broken image ${image.src}`);
  });
  result.tables.forEach((table, index) => {
    check(table.tabindex === '0' && table.role === 'region' && Boolean(table.label), `${key}: table ${index + 1} lacks keyboard region semantics`);
    if (table.overflows) {
      check(table.hasCue, `${key}: table ${index + 1} lacks overflow cue`);
      if (width <= 620) check(table.sticky, `${key}: table ${index + 1} lacks sticky identifying column`);
    }
  });
  check(runtimeErrors.length === 0, `${key}: runtime errors ${runtimeErrors.join('; ')}`);

  if (screenshotWidths.has(`${width}x${height}`) && !options.suffix) {
    await page.screenshot({ path: path.join(outputDir, `walnut-${width}x${height}.png`), fullPage: true });
  }

  if (width <= 900 && !options.skipMenu) {
    const toggle = page.locator('.menu-toggle');
    if (width === 320) {
      await page.locator('.preview-band').evaluate(element => { element.textContent += ' — confidential review edition for approved recipients only'; });
    }
    await toggle.click();
    check(await toggle.getAttribute('aria-expanded') === 'true', `${key}: menu did not open`);
    check((await toggle.textContent()).includes('Close navigation'), `${key}: open menu lacks Close accessible name`);
    check(await page.evaluate(() => document.activeElement === document.querySelector('#primary-nav a')), `${key}: first menu link was not focused`);
    const menuGeometry = await page.evaluate(() => ({
      headerBottom: document.querySelector('.site-header').getBoundingClientRect().bottom,
      navTop: document.querySelector('#primary-nav').getBoundingClientRect().top,
      backdropTop: document.querySelector('.menu-backdrop').getBoundingClientRect().top,
    }));
    check(Math.abs(menuGeometry.navTop - menuGeometry.headerBottom) <= 1, `${key}: menu top ${menuGeometry.navTop} does not match header bottom ${menuGeometry.headerBottom}`);
    check(Math.abs(menuGeometry.backdropTop - menuGeometry.headerBottom) <= 1, `${key}: backdrop top ${menuGeometry.backdropTop} does not match header bottom ${menuGeometry.headerBottom}`);
    await page.keyboard.press('Shift+Tab');
    check(await page.evaluate(() => document.activeElement === document.querySelector('.menu-toggle')), `${key}: focus did not move to menu toggle`);
    await page.keyboard.press('Shift+Tab');
    check(await page.evaluate(() => document.activeElement === document.querySelector('#primary-nav a:last-child')), `${key}: focus escaped backward from menu`);
    await page.keyboard.press('Escape');
    check(await toggle.getAttribute('aria-expanded') === 'false', `${key}: Escape did not close menu`);
    check((await toggle.textContent()).includes('Open navigation'), `${key}: closed menu lacks Open accessible name`);
    check(await page.evaluate(() => document.activeElement === document.querySelector('.menu-toggle')), `${key}: focus was not restored after Escape`);
    await toggle.click();
    await page.locator('.menu-backdrop').dispatchEvent('click');
    check(await toggle.getAttribute('aria-expanded') === 'false', `${key}: outside click did not close menu`);
    await toggle.click();
    await page.locator('#primary-nav a').first().click();
    await page.waitForTimeout(50);
    check(await toggle.getAttribute('aria-expanded') === 'false', `${key}: link click did not close menu`);
    check(await page.evaluate(() => document.activeElement === document.querySelector('.menu-toggle')), `${key}: focus was not restored after link click`);
  }

  if (width === 390 && !options.suffix) {
    await page.locator('[data-comp-filter="same-regime"]').click();
    const filteredCount = await page.locator('[data-comp-card]:visible').count();
    check(filteredCount === 3, `${key}: same-regime filter showed ${filteredCount} cards instead of 3`);
    await page.locator('[data-comp-filter="all"]').click();
    check(await page.locator('[data-comp-card]:visible').count() === 6, `${key}: all-comps filter did not restore six cards`);

    await page.locator('[data-comp-target="atwood"]').click();
    await page.waitForTimeout(500);
    check(await page.locator('[data-comp-id="atwood"] details').getAttribute('open') !== null, `${key}: map legend did not expand Atwood details`);

    const firstGalleryLink = page.locator('[data-gallery-link]').first();
    await firstGalleryLink.click();
    check(await page.locator('[data-gallery-dialog]').getAttribute('open') !== null, `${key}: gallery dialog did not open`);
    const firstGallerySource = await page.locator('[data-gallery-image]').getAttribute('src');
    await page.locator('[data-gallery-next]').click();
    const secondGallerySource = await page.locator('[data-gallery-image]').getAttribute('src');
    check(firstGallerySource !== secondGallerySource, `${key}: gallery next control did not change the image`);
    await page.keyboard.press('Escape');
    check(await page.locator('[data-gallery-dialog]').getAttribute('open') === null, `${key}: Escape did not close gallery dialog`);
  }

  await context.close();
}

(async () => {
  const chrome = await chromium.launch({ headless: true });
  for (const [width, height] of viewports) await inspectViewport(chrome, width, height);
  await inspectViewport(chrome, 390, 844, { reducedMotion: 'reduce', suffix: '-reduced-motion', skipMenu: true });
  await inspectViewport(chrome, 390, 844, { forcedColors: 'active', suffix: '-forced-colors', skipMenu: true });
  await inspectViewport(chrome, 360, 800, { isMobile: true, hasTouch: true, suffix: '-android-chrome' });
  await chrome.close();

  const safari = await webkit.launch({ headless: true });
  await inspectViewport(safari, 390, 844, { isMobile: true, hasTouch: true, suffix: '-ios-safari' });
  await safari.close();

  if (failures.length) {
    console.error(`UI REGRESSION FAILED (${failures.length})`);
    failures.forEach(failure => console.error(`- ${failure}`));
    process.exit(1);
  }
  console.log(`UI REGRESSION PASSED (${viewports.length + 4} browser/viewport runs)`);
  console.log(`Artifacts: ${outputDir}`);
})().catch(error => {
  console.error(error);
  process.exit(1);
});
