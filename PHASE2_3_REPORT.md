# Phase 2 (Auth) + Phase 3 (DB Integrity) — Implementation Report

> Scope as approved: **P0 security → Phase 2 (complete) → Phase 3**. No UI/map/taxi/delivery/booking/chat *feature* work. Only auth + DB-integrity (validators, constraints, indexes) touched.
> **Constraint:** sandbox out of disk → changes are static-verified, not run live. Migration commands below must be run locally.

---

## 1. Files changed

| File | Phase | What |
|---|---|---|
| `sdev/asgi.py` | P0 security | Wrapped websocket router in `AllowedHostsOriginValidator` (CSWSH protection) |
| `main/utils.py` | Phase 2 | `ratelimit()` gained optional `methods=` arg (limit only chosen HTTP methods); backward compatible |
| `main/forms.py` | Phase 2 | Rewrote to proper `CustomUserCreationForm` + new `CustomUserChangeForm` (custom-user admin forms) |
| `main/admin.py` | Phase 2 | `UserAdmin` now uses `add_form`/`form` → admin Add/Change user works with phone-based User |
| `main/views.py` | Phase 2 | Rate-limited `register`, `verify_otp`, `user_login`; added OTP brute-force protection (uses `attempts`) |
| `main/models.py` | Phase 3 | Validators: phone regex, `User.rating` 0–5, `OTPCode.code` 6-digit, `User.avatar`/`AdImage.image` file; Ad composite indexes |
| `places/models.py` | Phase 3 | lat/lng range validators, `PlaceReview.rating` 1–5, `Place.image` file validator, Place index |
| `delivery/models.py` | Phase 3 | `Store` lat/lng validators, `Store.logo` file validator |
| `taxi/models.py` | Phase 3 | `Taxist` + `Trip` (pickup/dest) lat/lng validators |

---

## 2. Exact code modifications

### P0 — `sdev/asgi.py`
```python
from channels.security.websocket import AllowedHostsOriginValidator
...
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
    ),
})
```
*(In DEBUG, `ALLOWED_HOSTS=['*']` → validator allows all, so local dev/demo is unaffected; production enforces real hosts.)*

### Phase 2 — `main/utils.py`
```python
def ratelimit(key, limit=60, window=60, methods=None):
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if methods and request.method not in methods:
                return view_func(request, *args, **kwargs)
            ...
```

### Phase 2 — `main/forms.py`
```python
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=False)
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("phone", "name", "email", "role")

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
```

### Phase 2 — `main/admin.py`
```python
from .forms import CustomUserCreationForm, CustomUserChangeForm
...
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    ...
```

### Phase 2 — `main/views.py`
```python
from .utils import validate_file_type, ratelimit
OTP_MAX_ATTEMPTS = 5

@ratelimit('register', limit=5, window=3600, methods=('POST',))
def register(request): ...

@ratelimit('otp_verify', limit=10, window=600, methods=('POST',))
def verify_otp(request):
    # latest active OTP; lock after OTP_MAX_ATTEMPTS wrong tries; single-use; increments attempts
    ...

@ratelimit('login', limit=10, window=300, methods=('POST',))
def user_login(request): ...
```

### Phase 3 — validators (representative)
```python
# main/models.py
phone_validator = RegexValidator(r'^\+?\d{9,15}$', "Telefon raqamini to'g'ri kiriting ...")
phone   = models.CharField(max_length=15, unique=True, validators=[phone_validator])
rating  = models.DecimalField(..., validators=[MinValueValidator(0), MaxValueValidator(5)])
code    = models.CharField(max_length=6, validators=[RegexValidator(r'^\d{6}$', ...)])
avatar  = models.ImageField(..., validators=[validate_file_type])
image   = models.ImageField(upload_to='ads/%Y/%m/', validators=[validate_file_type])  # AdImage

# places/models.py
latitude  = models.FloatField(..., validators=[MinValueValidator(-90),  MaxValueValidator(90)])
longitude = models.FloatField(..., validators=[MinValueValidator(-180), MaxValueValidator(180)])
rating    = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
image     = models.ImageField(..., validators=[validate_file_type])

# delivery/models.py — Store.latitude/longitude (+/-90, +/-180), Store.logo -> validate_file_type
# taxi/models.py    — Taxist.latitude/longitude, Trip.pickup_lat/lng, Trip.dest_lat/lng (same ranges)
```

### Phase 3 — indexes
```python
# main/models.py  Ad.Meta
indexes = [
    models.Index(fields=['status', '-is_boosted', '-created_at'], name='ad_status_boost_created_idx'),
    models.Index(fields=['user', 'status'], name='ad_user_status_idx'),
]
# places/models.py  Place.Meta
indexes = [ models.Index(fields=['is_active', 'category'], name='place_active_cat_idx') ]
```

---

## 3. Required migration commands

Run locally (sandbox can't):

```bash
# generate migrations for the new validators + indexes
python manage.py makemigrations main places delivery taxi

# review the generated files, then apply
python manage.py migrate

# code-only changes (asgi/admin/forms/views) need a server restart, no migration
python manage.py check          # should pass with no auth (E304) errors
```

Notes:
- Validator additions produce **state-only `AlterField`** migrations (no column change) → instant, safe.
- The two index additions produce `AddIndex` (real `CREATE INDEX`) → fast on current data volume.
- **No new migration is required for Phase 2** — the auth model/migration graph is already consistent (`user_permissions` related_name was fixed earlier by `0014`/`0016`).

---

## 4. Consistency checks performed (static)

- ✅ No direct `django.contrib.auth.models.User` references anywhere (all `get_user_model()` / `AUTH_USER_MODEL`).
- ✅ E304 groups/user_permissions clash resolved: model `related_name` distinct (`main_user_set` / `main_user_permissions`) **and** migrations `0014`/`0016` align — model == migration state.
- ✅ All FK/O2O/M2M `related_name`s are unique per target; no duplicate/conflicting reverse accessors found.
- ✅ `ratelimit` signature change is backward compatible (existing `delivery/views.py @ratelimit('driver_loc', ...)` unaffected).
- ✅ New cross-app import `from main.utils import validate_file_type` is safe: `main/__init__.py` is empty and `main/utils.py` imports no models (no circular import).
- ✅ File validator never runs on empty/blank fields (Django skips validators for `empty_values`), so blank avatars/logos still save.
- ✅ `AllowedHostsOriginValidator` won't block local dev (DEBUG `ALLOWED_HOSTS=['*']`).

---

## 5. Remaining blockers before Phase 4

1. **[RUNTIME] Run the migrations + `manage.py check`** locally and confirm green. This is the gate before Phase 4. (I cannot run it — sandbox disk full.)
2. **Verify end-to-end** (needs a running server): register → OTP → login flow, admin Add/Change user page, and that rate-limit/`attempts` lockout behave as intended.
3. Minor (non-blocking): `user_login` has a redundant 2nd `authenticate(request, phone=...)` fallback (no-op with `ModelBackend`); left in place to avoid behavior change — can be removed in a later cleanup.
4. Not in scope yet (Phase 5+): wiring `validate_file_type` into remaining upload fields (chat/product images), applying `@ratelimit` to other sensitive POST endpoints, pagination on `place_list`/`nearby`, and the systemic decimal-localization sweep for non-map numeric template output.

**Phase 2 and Phase 3 are complete pending your local `migrate` + `check`. Awaiting your approval to start Phase 4.**
