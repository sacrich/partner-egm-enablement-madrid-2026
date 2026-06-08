import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "dist-scraped");

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage();
const url =
  "https://partnerworkshops.salesforce.com/workshops/marketing-cloud/setup.html";
console.log("Scraping", url);
await page.goto(url, { waitUntil: "networkidle", timeout: 120000 });
await page.waitForSelector(".vp-page-content, #main-content", { timeout: 60000 });
const main =
  (await page.$(".vp-page-content")) ||
  (await page.$("#main-content")) ||
  (await page.$("main"));
const html = main ? await main.innerHTML() : "";
writeFileSync(join(OUT, "setup-marketing-cloud-next-raw.html"), html, "utf8");
console.log("chars", html.length);
const ids = [...html.matchAll(/<h2 id="([^"]+)"/g)].map((m) => m[1]);
console.log("h2:", ids.join(", "));
await browser.close();
