# Ceylon Compass Holidays

Local continuation of Lovable project `76891a34-82ad-4509-81b3-f61bf293d36a`, imported from revision `d9666a8c45af9aa11cf4b20076ec2ff2ab350daf`. This standalone TypeScript/TanStack app runs alongside the assignment frontend in `../web`.

From the repository root, run `make dev`. Open http://127.0.0.1:5175 for the traveller site and http://127.0.0.1:3000/staff for the staff console. The website sends same-origin requests to FastAPI. Set the server-side `MIRA_API_URL` to change the upstream and add the site's origin to `MIRA_ADDITIONAL_ORIGINS` on the API.

From this directory, run `npm ci`, `npm test`, `npx tsc --noEmit` and `npm run build`. With FastAPI running, launch the production build with `NITRO_PORT=5175 node .output/server/index.mjs`. Run `make notebook-browser` from the repository root with the site running. See the [delivery notes](../../docs/NOTEBOOK_DELIVERY.md) for the desktop and mobile checks.

A visitor cookie identifies notebook ownership. FastAPI persists the trip, its conversation and enquiries. Gemini interprets requests, published sources ground the itinerary and the rate workbook supplies eligible quotes. Bookings are simulated. My Trips reopens the saved notebook in the same browser.
