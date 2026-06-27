# PHASE 1 — Full Project Audit (Shofirkon Super App)

**Auditor:** Senior Django/Production review
**Method:** Rigorous static analysis of every app (models, views, urls, forms, admin, consumers, signals, routing, templates, migrations, settings, static).
**Constraint:** The Linux sandbox is out of disk space, so `manage.py check` / tests could **not** be run live. Items that strictly require a running server are marked **[RUNTIME]**. Static analysis already caught real, confirmed bugs (e.g. the decimal-localization map crash).

**Rule compliance:** Per the workflow, Phase 1 changes *nothing* except producing this audit. (Map fixes earlier in the session were a separate, explicit user request and are listed under §2.)

---

## 1. Severity legend

- 🔴 **P0** — breaks functionality or a security hole; must fix.
- 🟠 **P1** — incorrect behavior, data risk, or production blocker.
- 🟡 **P2** — hardening, performance, or polish.
- ✅ — verified healthy.

---

## 2. Already fixed earlier this session (context)

| Area | Issue | Status |
|---|---|---|
| Map | Decimal localization (`USE_I18N`+`uz` → `40,1156`) turned `[lat,lng]` into a 4-element array → Leaflet `toLatLng()` returned `null` → `project()` crash → blank map | ✅ Fixed in `map.html`, `place_detail.html`, `nearby.html`, `order_track.html`, `place_form.html`, `store_detail.html` via `\|unlocalize` |
| Map | Leaflet loaded only from unpkg (single CDN) → blank map if blocked | ✅ Switched to cdnjs + unpkg fallback + `crossorigin` + on-page self-diagnostics |
| Map | Sparse demo data | ✅ `seed_demo_full` expanded to ~210 places + stores + online taxists |
| Auth | `auth.User` vs `main.User` E304 clash (in old `check.txt`) | ✅ Already resolved: `AUTH_USER_MODEL='main.User'` + `related_name='main_user_set'/'main_user_permissions'` |
| Templates | `Invalid filter: 'split'` (old `errors.txt`) | ✅ Stale: `split` registered in `custom_filters.py`; offending `business_*` templates no longer exist |

---

## 3. Findings by category

### 3.1 Authentication & Users  → Phase 2
- ✅ `AUTH_USER_MODEL='main.User'`; custom `User(AbstractBaseUser, PermissionsMixin)` with `USERNAME_FIELD='phone'`, `UserManager`, and **explicit `related_name`** on `groups`/`user_permissions` (E304 resolved).
- ✅ No direct `from django.contrib.auth.models import User` anywhere; all code uses `get_user_model()` / `settings.AUTH_USER_MODEL`.
- 🟠 **P1 — Admin "Add user" likely broken.** `main/admin.py` `UserAdmin(BaseUserAdmin)` overrides `fieldsets`/`add_fieldsets` but does **not** set a custom `add_form`/`form`. `BaseUserAdmin.add_form = UserCreationForm` is bound to the default auth user and expects `username`; with a phone-based custom user the admin add-user page can raise. Fix: point admin to `main.forms.CustomUserCreationForm` (already exists) + a `UserChangeForm` subclass.
- 🟡 **P2** — `CustomUserCreationForm.save()` sets `email` but not `name`/`role`; fine for current flow, note for completeness.

### 3.2 Database / models / migrations  → Phase 3
- 🟠 **P1 — No latitude/longitude validators.** `places.Place.latitude/longitude`, `delivery.Store.latitude/longitude`, `taxi.Taxist.latitude/longitude`, `Trip.*_lat/_lng` are bare `FloatField`s. Out-of-range values (e.g. the localization bug) are accepted silently. Add `MinValueValidator(-90)/MaxValueValidator(90)` (lat) and `-180/180` (lng).
- 🟠 **P1 — Rating not bounded everywhere.** `places.PlaceReview.rating = PositiveSmallIntegerField(default=5)` has **no max** (can store 7). `taxi.ServiceReview/TaxistReview` correctly use `choices=1..5`. `User.rating = DecimalField(default=5.0)` unbounded. Add validators / `MaxValueValidator(5)`.
- 🟠 **P1 — Phone has no format validation** (`User.phone = CharField(unique=True)`). Add a `RegexValidator` (e.g. `^\+998\d{9}$`) or normalize in the manager.
- 🟡 **P2 — OTP** `OTPCode` model present (admin shows `code/used/expires_at`); **[RUNTIME]** verify expiry + single-use enforced in the verify view; add attempt limiting (see 3.4).
- 🟡 **P2 — File/image fields lack model-level validators.** `AdImage.image`, `User.avatar`, `Place.image`, `Store.logo`, `ChatMessage.file/image/audio` accept any type/size at the model layer. A `validate_file_type` helper exists in `main/utils.py` (image ext + 5 MB) but is **not wired** into most `ImageField`/`FileField`s. Chat WS enforces 8 MB but not type. Add validators / form clean.
- 🟡 **P2 — `DEFAULT_AUTO_FIELD='AutoField'`** (not `BigAutoField`); int-PK tables (places, delivery) could exhaust 32-bit at scale. Low risk for a district app.
- ✅ Migrations: the two parallel `places/0002_*` migrations are reconciled by `0003_merge_*` (correct). `delivery` migrations sequential (0001→0008). `main` sequential. No obvious broken graph statically; **[RUNTIME]** `makemigrations --check --dry-run` recommended.

### 3.3 Templates & UI  → Phase 4
- 🟠 **P1 — Decimal-localization is systemic.** Fixed for all *map* coordinate embeds, but **any** float/Decimal model value rendered as a bare JS number or into a `type=number` input elsewhere has the same risk (e.g. prices in inline scripts, boost amounts). Recommend a project-wide sweep + `{% localize off %}` blocks or `\|unlocalize` in JS/number-input contexts. **[RUNTIME]** confirm per page.
- 🟡 **P2 — Branding inconsistency.** `base.html <title>` and many template titles still say "SamCity"; settings cache `'samcity-cache'`, log `'samcity.log'`, static `samcity*.js`. Not an error; rebrand to "Shofirkon" for the demo.
- ✅ All ~379 `{% url %}` references resolve to defined names/namespaces (verified earlier). Custom filters `\|som`/`\|stars` always preceded by `{% load taxi_extras %}`.

### 3.4 Security  → Phase 5
- 🔴 **P0 — WebSockets not origin-validated.** `asgi.py` uses `AuthMiddlewareStack(URLRouter(...))` but no `AllowedHostsOriginValidator` → Cross-Site WebSocket Hijacking (CSWSH) risk. Wrap with `AllowedHostsOriginValidator`.
- 🟠 **P1 — Rate limiting not applied to OTP/login.** A solid `ratelimit` decorator exists in `main/utils.py` but **[RUNTIME]** appears not applied to OTP request/verify or login. Add `@ratelimit('otp', ...)`, `@ratelimit('login', ...)`.
- 🟠 **P1 — Upload validation gaps** (see 3.2): no MIME/type/size guard on most uploads; SVG/script-in-image risk.
- 🟡 **P2 — Production settings are correctly gated** behind `DEBUG=False` (HSTS, secure cookies, SSL redirect, SECRET_KEY required). `DEBUG` defaults to `True`; ensure `DJANGO_DEBUG=False` in prod. `ALLOWED_HOSTS=['*']` only in DEBUG. ✅ design is sound.
- 🟡 **P2 — Object ownership checks** present in `places` (`place_edit`/`delete` check `owner_id`/`is_staff`), and per prior audit in delivery/booking. **[RUNTIME]** spot-check every edit/delete/POST view for ownership.
- ✅ `CSRF_TRUSTED_ORIGINS`, CSRF middleware, `DATA_UPLOAD_MAX_MEMORY_SIZE` cap configured. Chat consumer enforces auth, membership, ban, 8 MB media cap.

### 3.5 Performance  → Phase 6
- 🟠 **P1 — `places.place_list` is unpaginated** and now returns ~210–290 rows; also `nearby` loads **all** active places into Python for Haversine sorting each request. Add pagination; cap/limit nearby candidates.
- 🟡 **P2 — `places_geojson`** returns all places + stores + taxists per call (fine at hundreds; cache for scale). `_taxi_points` has no `select_related` (only scalar fields → OK).
- 🟡 **P2 — N+1 risk** in list/detail templates iterating related objects (reviews, images, order items). Pagination exists in `main/views.py` and `delivery/views.py`; **[RUNTIME]** profile with `select_related/prefetch_related` audit on ad/job/resume/chat lists.
- ✅ Good practices already present: `prefetch_related('images')` in `place_detail`, `select_related` in favorites, indexed `status`/FK fields, locmem/Redis cache switch.

### 3.6 Map  → Phase 7
- ✅ Coordinate crash fixed; CDN hardened; clustering + category filters + search + locate + OSRM routing proxy with straight-line fallback + Nominatim reverse-geocode (cached).
- 🟠 **P1 — add lat/lng validators** (3.2) so bad coordinates can never reach the map again.
- 🟡 **P2** — `_taxi_points`/`_delivery_points` merged into `places_geojson`; consider a `?layers=` param + server cache for large datasets.

### 3.7 Chat / WebSocket  → Phase 8
- ✅ Feature-complete consumer: text/image/file/voice, reply, edit, soft-delete, reactions, @mentions→notifications, typing, presence/last-seen, read receipts, admin approve/kick/ban, per-message permission checks, 8 MB cap.
- 🔴 **P0** — origin validation (3.4).
- 🟡 **P2** — `notify_mentions` matches `username__in`; many demo users have null `username` → mentions only work for users with usernames (by design). Media stored to default storage with no AV/type scan.

### 3.8 Taxi  → Phase 9
- ✅ Models complete (Service, Taxist, Car 1:1, Route, Trip state machine, Payment with last-4 only). Views cover register/edit/manage/route add-del/trip/pay/track; `region` defaults to "Shofirkon".
- 🟡 **P2 [RUNTIME]** — verify trip status transitions and that only the trip's passenger/taxist can act; verify `TaxistReview.can_review` gate (only completed trips).

### 3.9 Delivery  → Phase 10
- ✅ Store/Product/Cart/CartItem/Order/OrderItem/DeliveryDriver/DriverLocation; explicit `ORDER_TRANSITIONS` + `can_transition()` state machine; realtime tracking; pagination present.
- 🟡 **P2 [RUNTIME]** — verify checkout edge cases (empty cart, sold-out, multi-store order shown to each store owner — known limitation), and ownership on store/product/order-status endpoints.

### 3.10 Booking  → Phase 11
- ✅ `Venue` + `VenueBooking` with status/event/subscription fields; conflict check (`_booking_conflict`) per prior audit; owner edit/delete.
- 🟡 **P2 [RUNTIME]** — confirm conflict logic blocks overlapping date/time precisely; confirm cancellation/refund status flow.

### 3.11 Ads / Marketplace  → Phase 12
- ✅ CRUD + favorites + reports + inquiries + contact-reveal + boost + search/autocomplete; admin rich.
- 🟡 **P2** — upload validation (3.2); **[RUNTIME]** ownership on edit/delete/toggle.

### 3.12 Notifications  → Phase 13
- ✅ Per-user WS group `notif_user_<id>`, `notify()` helper, stored notifications, unread count, mark-all-read, context processor wired in settings.
- 🟡 **P2** — origin validation (3.4) applies to this socket too.

---

## 4. Cross-cutting / dead code
- No `TODO`/`FIXME`/`NotImplemented`/placeholders found anywhere. ✅
- Stale debug logs in repo root: `errors.txt`, `errors_utf8.txt`, `check.txt` (pre-fix; safe to delete — could not delete: sandbox down).
- No unused/duplicate app logic detected; `payments` app exists and is fully wired (earlier false alarm from a flaky glob).

---

## 5. Blocked on a running environment **[RUNTIME]**
These need a live server (sandbox is out of disk):
`manage.py check`, `makemigrations --check`, login/registration/OTP end-to-end, websocket handshakes, per-view ownership/permission spot-checks, query profiling.
**Action:** free disk on the workspace, or run locally: `python manage.py check` and `python manage.py makemigrations --check --dry-run`.

---

## 6. Prioritized fix roadmap (next phases)

**Phase 2 (Auth):** wire admin `add_form`/`form` to `CustomUserCreationForm` (+ a `UserChangeForm`); confirm login/register/roles. *(small, low-risk)*

**Phase 3 (DB):** add lat/lng validators, rating `MaxValueValidator(5)`, phone `RegexValidator`, OTP single-use/expiry guard, file validators; generate the matching migrations.

**Phase 5 (Security, do early — has a P0):** `AllowedHostsOriginValidator` on the websocket router; apply `@ratelimit` to OTP/login; enforce `validate_file_type` on uploads.

**Phase 4/6/7–13:** templates localization sweep, pagination on `place_list`/nearby, then module-by-module runtime verification.

> Recommendation: tackle the **P0 websocket origin validation** and **Phase 3 validators** first — they are the highest-impact, lowest-regression-risk production fixes.
