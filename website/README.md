# Reso Resort — booking website

Angular 21 SPA for the Reso resort collection. Talks to the Odoo reso_pms JSON
API (`/api/v1/website/*`) — see `../custom_addons/reso_pms/controllers/booking_website.py`.

## Development

```bash
npm install
npm start -- --proxy-config proxy.conf.json   # serves on :4200, /api → localhost:8069
```

Run Odoo locally first (port 8069) so the app has live data.

The API base URL is read at runtime from `public/config.json`
(`{"apiBaseUrl": ""}` = same origin, which is how the nginx container serves it).
Point it at `http://localhost:8069` for a plain static dev server without the proxy.

## Build

```bash
npm run build        # output in dist/reso-resort/browser/
```

## Docker

```bash
docker build -t reso-website .
docker run -p 8080:80 reso-website
```

The image is multi-stage (node build → nginx). `nginx.conf` serves the SPA and
proxies `/api/` to the Odoo container (`http://web:8069`), so with
`docker compose up` the whole stack works out of the box.

## Structure

- `src/app/core` — runtime config loader, API service, models
- `src/app/shared` — navbar/footer, theme service + toggle (light/dark), scroll-reveal directive, room visual placeholder, price pipe, property store
- `src/app/pages` — home, rooms, room detail, book (availability → guest details → payment), contact, 404
