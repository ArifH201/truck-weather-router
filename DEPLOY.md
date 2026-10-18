# Deployment

Backend on Render, frontend on Vercel. Both have free tiers. Deploy the backend
first because the frontend build needs its URL.

## 1. Push to GitHub

Create a public repository and push the project root (it contains `backend/`,
`frontend/`, `README.md`, and `render.yaml`). Check that no `node_modules/` or
`.env` file is committed.

## 2. Backend on Render

1. Render dashboard → **New → Blueprint** → select the repo. It reads `render.yaml`.
   (Or create a Web Service manually: root directory `backend`, build
   `pip install -r requirements.txt`, start `gunicorn config.wsgi --workers 2 --threads 4 --timeout 60`.)
2. Wait for the first deploy, then open `https://<service>.onrender.com/api/health`.
   You should see `{"status": "ok"}`.
3. Note the service URL.

## 3. Frontend on Vercel

1. Vercel → **Add New → Project** → import the same repo.
2. Set **Root Directory** to `frontend`. Framework preset: Vite
   (build `npm run build`, output `dist`).
3. Add the environment variable `VITE_API_URL` = your Render URL, with no trailing slash.
4. Deploy and note the Vercel URL.

## 4. Allow the frontend to call the backend (CORS)

In Render → the service → **Environment**, set
`CORS_ALLOWED_ORIGINS` = your Vercel URL (e.g. `https://my-app.vercel.app`, no
trailing slash). Several origins can be comma-separated. Redeploy if Render does not
restart automatically. Without this the browser blocks every API call.

## 5. Pre-submission checklist

- [ ] Run a real trip on the **hosted** app (e.g. Chicago → Denver, tomorrow, 42,000 lb)
- [ ] Try a heavy load and a light one on the same trip and confirm risk changes
- [ ] Try a nonsense place name and a past date and confirm the error messages
- [ ] Scrub the heatmap slider and confirm it is smooth
- [ ] Check it on a phone-width window
- [ ] Put the live URL and Loom link at the top of the README
- [ ] Repository is public and the README setup steps work from a clean clone

## Known free-tier behaviour

- **Cold starts:** Render's free tier sleeps after inactivity, and the first request
  can take about a minute. Open the app a few minutes before a reviewer might, and
  mention it in the README or Loom.
- **Geocoding from shared hosting IPs:** Nominatim may rate-limit or block busy
  shared IPs. If geocoding fails only on the hosted app, switch `geocode` in
  `providers.py` to another provider (e.g. Mapbox or OpenRouteService with a free key).
- **Cache is per worker and lost on restart.** This is fine for a demo.

## Optional: demo mode on the hosted app

Demo mode (simulated storm) is disabled in production by default. To show it on the
hosted app, add `DEMO_WEATHER_ENABLED=1` in Render's environment. Say clearly in the
README and Loom that it is simulated; the app labels it on screen too. Leave it off
for the real submission if you prefer reviewers to see only live forecasts.
