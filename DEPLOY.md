# Deployment (free): GitHub + Vercel

Code lives on GitHub. Both the Django API and the React app are hosted on Vercel's
free (Hobby) plan as two separate Vercel projects from the same repository.
GitHub Pages is not used because it serves static files only and cannot run Django.

Deploy the backend first, because the frontend build needs its URL.

## 1. Push to GitHub

Create a public repository and push the project root (it contains `backend/`,
`frontend/`, and `README.md`). Check that no `node_modules/`, `.venv/` or `.env`
file is committed.

## 2. Backend on Vercel

1. vercel.com → sign in with GitHub → **Add New → Project** → import the repo.
2. Set **Root Directory** to `backend`. Vercel finds `manage.py` and detects Django
   (the framework preset should say Django).
3. Add **Environment Variables**:
   - `DJANGO_DEBUG` = `0`
   - `DJANGO_SECRET_KEY` = a long random string
     (generate one with `python -c "import secrets; print(secrets.token_urlsafe(50))"`)
   - `CORS_ALLOWED_ORIGINS` = `https://placeholder.vercel.app` (changed in step 4)
4. **Deploy**, then open `https://<backend>.vercel.app/api/health`. You should see
   `{"status": "ok", "demo_enabled": false}`.

`backend/vercel.json` lets the API run for up to 60 seconds, since a trip analysis
makes several external calls.

## 3. Frontend on Vercel

1. **Add New → Project** → import the **same** repo again.
2. Set **Root Directory** to `frontend` (framework preset: Vite).
3. Add the environment variable `VITE_API_URL` = the backend URL from step 2
   (for example `https://truck-router-api.vercel.app`, no trailing slash).
4. **Deploy** and note the frontend URL.

## 4. Connect them (CORS)

In the **backend** project → Settings → Environment Variables, change
`CORS_ALLOWED_ORIGINS` to the exact frontend URL (no trailing slash, no path), then
**Redeploy** (Deployments → the latest one → Redeploy). Environment changes only
apply to new deployments.

## 5. Pre-submission checklist

- [ ] `/api/health` works on the backend URL
- [ ] A real trip works on the hosted frontend (e.g. Chicago → Denver, tomorrow, 42,000 lb)
- [ ] Heavy vs light load changes risk
- [ ] Nonsense place and past date show clear errors
- [ ] Heatmap slider is smooth
- [ ] Live URL and Loom link are at the top of the README
- [ ] Repository is public and the README setup steps work from a clean clone

## Troubleshooting

- **"Cannot reach the server" in the app:** `VITE_API_URL` is missing or wrong.
  Fix it in the frontend project and **Redeploy** (it is baked in at build time).
- **CORS error in the browser console:** `CORS_ALLOWED_ORIGINS` does not match the
  frontend URL exactly, or you did not redeploy the backend after changing it.
- **Backend build fails on the Python version:** open the backend project's settings
  and choose Python 3.11 or newer (Django 5 needs 3.10+).
- **Error 500 or a timeout:** Vercel → backend project → Deployments → the
  deployment → **Logs** shows the Python error. Paste it to get help.
- **"Could not find location" only on the hosted app:** the free geocoder
  (Nominatim) may rate-limit Vercel's shared IPs. Only `geocode` in
  `backend/routing/providers.py` needs to change to another provider.

## Free-tier notes

- The first request after a quiet period is a little slower (a function cold start,
  a few seconds, not a minute).
- The weather cache lives in memory per function instance, so it is not shared
  across instances and is lost when an instance is recycled. Fine for a demo; Redis
  would be the next step.
- Optional demo mode (simulated storm) is off in production. To enable it, add
  `DEMO_WEATHER_ENABLED=1` to the backend project, and say clearly that it is
  simulated. For the real submission, leaving it off is cleaner.
