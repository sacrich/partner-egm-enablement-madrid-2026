# Guía consolidada — Salesforce Personalization (teoría)

Sitio estático con **solo los 7 módulos** que definiste, sin navegación al resto de [Partner Workshops](https://partnerworkshops.salesforce.com).

## Módulos incluidos

1. Setup Personalization  
2. Web Sitemap  
3. Web Schemas  
4. Data Streams  
5. Identity Resolution  
6. Item Data Graphs  
7. Profile Data Graphs  

## Cómo ver la guía

Abre en el navegador:

`dist/index.html`

(O sirve la carpeta `dist` con cualquier servidor estático.)

## Regenerar el contenido

Si actualizan las páginas en el portal:

```bash
cd workshop-personalization
export PLAYWRIGHT_BROWSERS_PATH="$(pwd)/.pw-browsers"
npx playwright install chromium   # solo la primera vez
node scrape-playwright.mjs
python3 build.py
```

## Notas

- Los **vídeos Vidyard** siguen enlazados al embed original (requieren red y contraseña `LearnSPtoday` donde aplique).
- Los enlaces útiles externos (Partner Community, Chrome Web Store, Postman, documentación Salesforce) se mantienen.
- Los enlaces a **otros workshops** del mismo portal quedan desactivados a propósito.
- Los CSV de ejemplo se descargan a `dist/data/` cuando el build puede alcanzarlos.
