# Antigravity uchun vazifa — SamCity web frontend UI/UX & responsive audit

> Bu promptni Antigravity'ga (yoki brauzer + serverni boshqara oladigan agentga)
> to'liq nusxalab bering. U loyihani ishga tushirib, brauzerda har sahifani
> ko'rib, kamchiliklarni topib tuzatishi kerak.

---

## CONTEXT (read first)

You are working on **SamCity**, a Django web "super-app" for residents of a city
(Shofirkon/Samarqand). The web frontend is server-rendered Django templates. There
is also a separate Flutter mobile app in `mobile/` — **ignore the mobile app**, work
ONLY on the Django web templates and static files.

**Project root:** `C:\Users\user\Desktop\merged_project`
**Stack:** Django 5, server-rendered templates, vanilla JS, Leaflet maps. No React/Vue.
**Run the server:** `python manage.py runserver` then open `http://127.0.0.1:8000`.
Create a test login if needed (registration uses phone + OTP; the OTP is printed to
the server console — look for `DEBUG: OTP for <phone> is <code>`).

**Design system — all global CSS lives inline in `main/templates/base.html`:**
- Dark theme is the DEFAULT (`data-theme="dark"`), light theme also exists.
- CSS tokens in `:root` / `[data-theme="dark"]`: `--accent` (emerald `#0ea371` /
  dark `#34d399`), `--teal`, `--gold`, `--surface`, `--text`, `--text2`, `--border`,
  `--radius`, shadows, etc. **Reuse these tokens — never hardcode colors.**
- Reusable components: `.btn` (`.btn-accent/.btn-outline/.btn-ghost/.btn-green`),
  `.card`, `.lcard` (list/product cards), `.grid-2/.grid-3/.grid-4`, `.chip`,
  `.badge`, `.empty-state`, `.page-header`, `.svc-card` (homepage service cards),
  `.hero-search`, `.info-row`, `.timeline`, `.bottom-nav` (mobile), `.mm-panel`
  (mobile drawer).
- All UI text is **Uzbek (latin)** — keep it Uzbek.

**Audience:** ordinary residents, many of whom rarely use websites/apps. The UI must
be **simple, obvious, and fast** — big tap targets, clear labels, minimal steps,
primary actions impossible to miss.

## ALREADY FIXED (do NOT redo these — verify they still work):
1. Cart moved to a permanent top-right icon+badge in the navbar (`.nav-cart`).
2. Navbar overflow: links collapse to a burger drawer below 1240px (no more hidden
   horizontal scroll).
3. Map marker popups now include image + name + category + description + address +
   phone + a "To'liq ma'lumot" button (`main/static/js/samcity-map.js`,
   `places/views.py` geojson adds `image`/`desc`).
4. Disabled the 3D-tilt on `.lcard` (it conflicted with CSS hover and made cards
   jump) and disabled "magnetic" buttons (buttons ran away from the cursor).

---

## YOUR TASKS

### Task A — Full responsive audit & fixes (HIGHEST PRIORITY)
Open EVERY major page and test at these widths: **360, 414, 768, 1024, 1440 px**
(use the browser device toolbar). Take a screenshot at each width. Fix every layout
break you find: horizontal overflow/scroll, overlapping elements, text clipping,
tiny tap targets (<44px), images breaking aspect ratio, cards misaligning, sticky
elements covering content, the mobile bottom-nav covering page content, modals/forms
not fitting.

Pages to check (URLs relative to `/`):
- `/` (home — landing with hero & service cards)
- `/all-ads/` or `/ads/` (e'lonlar list), an ad detail, `/ad-new` form
- `/delivery/` (do'konlar list), a store detail (product cards), `/delivery/cart/`,
  checkout, `/delivery/orders/`, order detail/track
- `/taxi/`, taxist detail, `/taxi/trips/`
- `/booking/` venues, venue detail, venue booking form, my bookings
- `/map/` (Leaflet map + floating sidebar)
- `/payments/`, `/jobs/`, `/chat/`, `/dashboard/`, `/profile/`, register/login/OTP

For each fix, prefer editing the shared CSS in `base.html` (so it fixes everywhere)
over per-page hacks. Verify the fix at all breakpoints before moving on.

### Task B — "Broken" delivery cards
On `/delivery/` and store detail pages, verify the `.lcard` product/store cards
render cleanly (image aspect ratio, spacing, the "Savatga" button, price alignment)
at all widths. Fix any remaining visual breakage. Files:
`delivery/templates/delivery/store_list.html`, `store_detail.html`, `base.html` CSS.

### Task C — Simplify for non-technical residents
Make the site dramatically easier for first-time, low-literacy-with-tech users:
- **Home page:** ensure the first screen clearly presents the core services
  (Yetkazish, Taksi, E'lonlar, Joylar, To'lovlar, Xarita) as big, labeled, tappable
  cards — above any marketing/flair. A resident must understand "what can I do here"
  in 3 seconds. File: `main/templates/home.html`.
- **Reduce visual noise:** the site has heavy effects (aurora background, grain,
  animated gradients, scroll-progress bar, card spotlight). Tone these DOWN so the
  UI feels calm and loads fast on cheap Android phones — without removing the brand
  feel entirely. Respect `prefers-reduced-motion`.
- **Clear primary actions:** every page should have one obvious primary button.
- Keep navigation shallow — important destinations reachable in ≤2 taps.

### Task D — Map page polish
Verify `/map/`: markers clickable, popup shows the rich info (image/name/details),
the category filter sidebar is usable on mobile (it should stack above the map under
560px), and "Joylashuvim" (GPS) works. File: `places/templates/places/map.html`.

---

## RULES
- **Do NOT break existing functionality.** Test flows after changes (login, add to
  cart, checkout, create ad, book venue).
- Keep all UI text in **Uzbek**.
- Reuse the existing CSS tokens & components; match the current emerald/teal dark
  design language.
- After editing static JS/CSS, if `DEBUG=False`, run `python manage.py collectstatic`.
- Work page-by-page; screenshot before & after each fix to prove it.
- Run `python manage.py test` at the end to confirm nothing server-side broke.

## ACCEPTANCE CRITERIA
- No horizontal scroll or overlapping/clipped elements on any page at 360–1440px.
- Cart, and every primary action, is obvious and reachable within 2 taps.
- Delivery cards render cleanly at all widths.
- Map markers open a rich popup (image + details).
- Home page leads with simple, labeled service cards.
- A non-technical person can find and complete: "order food", "call a taxi",
  "post an ad", "pay a bill" without confusion.
- `python manage.py test` passes.
