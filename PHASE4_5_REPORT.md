# Phase 4 (Templates/UI) + Phase 5 (Security Hardening) — Report

> Constraint: sandbox out of disk → static-verified, not run live. Changes are non-breaking by design (invalid files are skipped with a user message; flow is preserved).

---

## Phase 4 — Template & UI stability  → VERIFIED CLEAN (no code changes needed)

- ✅ Every `{% include %}` resolves: `_map_assets.html`, `taxi/_review_form.html`, `notifications/_bell.html`, `delivery/_order_timeline.html`.
- ✅ All ~379 `{% url %}` references resolve (names + namespaces).
- ✅ Filters healthy: `som`/`stars` always preceded by `{% load taxi_extras %}`; `split` registered; the old `Invalid filter: split` is gone (offending templates removed).
- ✅ No remaining decimal-localization **crash** risk:
  - Map float embeds (lat/lng) already use `|unlocalize`.
  - `type=number` inputs bind **integer** fields (price/salary/capacity/stock/year/seats) — Django does not comma-localize integers.
  - `{{ avg_rating }}` etc. are display-only text (a comma is cosmetic, not parsed → no crash).
- **[RUNTIME]** "every page loads / context vars present" needs a running server to confirm.

No template files required modification in Phase 4.

---

## Phase 5 — Security Hardening

### Already done in P0 / Phase 2 (recap)
- 🔴→✅ WebSocket `AllowedHostsOriginValidator` (CSWSH).
- ✅ Rate limiting on `register` (5/h), `verify_otp` (10/10min), `user_login` (10/5min) — POST only.
- ✅ OTP brute-force lockout via `attempts` (5 tries).
- ✅ ALLOWED_HOSTS / CSRF / secure cookies / HSTS / SSL-redirect gated on `DEBUG=False` (settings already correct).
- ✅ Model-level validators (phone, lat/lng, rating, OTP, file) added in Phase 3.

### New in this phase
**1. Upload (file/image) validation enforced at every view upload point** (was only in `ad_create` + `chat_upload_image`). Pattern: validate with `validate_file_type` (image ext + 5 MB), and on failure **skip the file + show a message** — the create/edit flow is never broken.

| File | Upload point | Added |
|---|---|---|
| `main/views.py` | `profile_edit` avatar | validate → error+redirect on bad file |
| `main/views.py` | `ad_edit` images | validate → skip bad image (warning) |
| `delivery/views.py` | `store_create` + `store_edit` logo | validate → error message |
| `delivery/views.py` | `product_create` + `product_edit` image | validate → skip (warning) |
| `places/views.py` | `_apply` place image + gallery | validate each → skip bad (warning) |
| `taxi/views.py` | taxist `photo` | validate → error message |
| `booking/views.py` | venue `image` | validate → error message |
| `main/community_views.py` | help-request `image` | validate → error message |

Each of these modules now imports `validate_file_type` from `main.utils` (no circular import — `main.utils` imports no models; `main/__init__.py` empty).

**2. Audit logging** (`main/views.py`): new `logging.getLogger('shofirkon.security')`; logs
- failed login attempts (`Failed login: phone=… ip=…`),
- OTP lockouts (`OTP lockout: phone=… ip=…`).
These flow into the existing `LOGGING` root handlers (console + rotating file `logs/samcity.log`).

---

## Files changed (Phase 4 + 5)
- `main/views.py` — audit logger; avatar + ad_edit upload validation
- `delivery/views.py` — import + store logo & product image validation
- `places/views.py` — import + place image/gallery validation
- `taxi/views.py` — import + taxist photo validation
- `booking/views.py` — import + venue image validation
- `main/community_views.py` — import + help image validation

(No new migrations — these are view-layer only.)

## Required commands
```bash
# No new migrations from Phase 4/5. Just restart the server to load the code:
python manage.py runserver
# (Phase 3 migrations from the previous step still need: makemigrations + migrate)
```

## Consistency checks (static)
- ✅ Upload validation uses the existing `except Exception` style already used by `ad_create`/`chat_upload_image`; all touched views already import `messages`.
- ✅ `validate_file_type` skips empty/blank uploads (Django skips validators on empty values) → no false errors on optional images.
- ✅ Cross-app imports safe (no model imports in `main.utils`).
- ✅ Rate-limit decorator unchanged behavior for existing `delivery` usage.

## Remaining blockers / not-yet-done
1. **[RUNTIME]** run `manage.py check` + the Phase 3 `migrate`, then click through upload forms to confirm messages render.
2. Object-ownership: verified present in places/delivery store-edit; **[RUNTIME]** spot-check every edit/delete/POST across modules (Phases 9–13).
3. Not started: Phase 6 (performance — pagination on `place_list`/nearby, query profiling), Phases 7–13 module runtime completion.
4. Optional: extend audit logging to successful logins / admin actions; wire `validate_file_type` into chat WS uploads (currently size-capped only).

**Phase 4 + 5 complete. Awaiting approval to start Phase 6 (Performance Optimization).**
