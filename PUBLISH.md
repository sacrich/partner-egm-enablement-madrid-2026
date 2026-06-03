# Publicar la guía para partners (GitHub Pages)

La forma más simple de compartir el sitio es **GitHub Pages**: URL pública, HTTPS, sin servidor propio.

## Requisitos

- Cuenta en [GitHub](https://github.com)
- Repositorio **público** (Pages gratuito en repos públicos)
- Carpeta `workshop-personalization/dist` generada (`python3 build.py`)

## Pasos (primera vez)

### 1. Crear el repositorio en GitHub

1. En GitHub: **New repository**
2. Nombre sugerido: `partner-egm-enablement-2026` (o el que prefieras)
3. **Public**
4. No marques “Add README” si vas a subir este proyecto desde tu Mac

### 2. Subir el proyecto desde tu Mac

En Terminal:

```bash
cd "/Users/sacrich/Desktop/PARTNER ENABLEMENT MADRID"

git init
git add .
git commit -m "Partner EGM Enablement 2026 — mandatory pre-work guide"

git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

Sustituye `TU_USUARIO` y `TU_REPO` por tu organización o usuario y el nombre del repo.

### 3. Activar GitHub Pages

1. En el repo: **Settings** → **Pages**
2. En **Build and deployment** → **Source**, elige **GitHub Actions**
3. Tras el primer push, se ejecuta el workflow **Deploy Partner Enablement guide**
4. En **Settings → Pages** verás la URL, por ejemplo:

   `https://TU_USUARIO.github.io/TU_REPO/`

Esa es la URL que envías a los partners.

## Actualizar el contenido

Si cambias textos o regeneras `dist`:

```bash
cd "/Users/sacrich/Desktop/PARTNER ENABLEMENT MADRID/workshop-personalization"
python3 build.py

cd ..
git add workshop-personalization/dist
git commit -m "Update workshop guide"
git push
```

En 1–2 minutos Pages se actualiza solo.

## Notas importantes

| Tema | Detalle |
|------|---------|
| **Vídeos** | Vidyard necesita internet; funcionan en la URL publicada |
| **Privacidad** | Repo público = cualquiera con el enlace puede ver la guía. Para acceso restringido usa repo privado + GitHub Team Pages, o Netlify/Vercel con contraseña |
| **Contenido Salesforce** | Material basado en Partner Workshops; úsalo solo en el ámbito acordado con partners |
| **Copiar código** | En `https://` el botón Copy funciona mejor que con `file://` |

## Alternativas

- **Netlify Drop**: arrastra la carpeta `dist` en [app.netlify.com/drop](https://app.netlify.com/drop) → URL al instante
- **ZIP por email/Slack**: menos cómodo; vídeos y copy pueden fallar sin HTTPS
