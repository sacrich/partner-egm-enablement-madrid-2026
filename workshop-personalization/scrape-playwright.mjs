import { chromium } from "playwright";
import { writeFileSync, mkdirSync, existsSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "dist-scraped");

const PAGES = [
  { slug: "setup-personalization", title: "Setup Personalization" },
  { slug: "sitemap", title: "Web Sitemap" },
  { slug: "web-schemas", title: "Web Schemas" },
  { slug: "data-streams", title: "Data Streams" },
  { slug: "identity-resolution", title: "Identity Resolution" },
  { slug: "item-data-graphs", title: "Item Data Graphs" },
  { slug: "profile-data-graphs", title: "Profile Data Graphs" },
];

const BASE =
  "https://partnerworkshops.salesforce.com/workshops/salesforce-personalization";
const ALLOWED = new Set(PAGES.map((p) => p.slug));

function rewriteHtml(html, slug) {
  return html
    .replace(/src="\/assets\//g, 'src="assets/')
    .replace(/href="\/workshops\/salesforce-personalization\/([^"#?]+)\.html([^"]*)"/g, (_, name, hash) => {
      const s = name.replace(/\.html$/, "");
      if (ALLOWED.has(s)) {
        return `href="${s}.html${hash || ""}"`;
      }
      return 'href="#" data-blocked="1"';
    })
    .replace(/href="\/[^"]*"/g, 'href="#" data-blocked="1"');
}

mkdirSync(OUT, { recursive: true });
mkdirSync(join(OUT, "assets"), { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage();

for (const p of PAGES) {
  const url = `${BASE}/${p.slug}.html`;
  console.log("Scraping", url);
  await page.goto(url, { waitUntil: "networkidle", timeout: 120000 });
  await page.waitForSelector(".vp-page-content, #main-content, .theme-container", {
    timeout: 60000,
  });
  const main =
    (await page.$(".vp-page-content")) ||
    (await page.$("#main-content")) ||
    (await page.$("main"));
  let html = main ? await main.innerHTML() : await page.content();
  html = rewriteHtml(html, p.slug);
  writeFileSync(join(OUT, `${p.slug}.html`), html, "utf8");
  console.log("  chars", html.length);
}

await browser.close();
console.log("Done →", OUT);
