# Git tozalash — venv/build/.dart_tool va maxfiy profilni olib tashlash

Repoga xato bilan ~260 MB axlat tushgan:
`venv/` (139MB), `mobile/build/` (111MB), `mobile/.dart_tool/` (10MB) va
`mobile/.dart_tool/chrome-device/` (haqiqiy Chrome profili — cookie/session/history).

> ⚠️ Bu buyruqlar **git tarixini qayta yozadi**. Avval zaxira (backup) qiling
> va jamoa bilan kelishing (hammaning push qilingan ishi bo'lmasin).

---

## 1. Joriy holatdan olib tashlash (tarix saqlanadi)

`.gitignore` allaqachon yangilangan. Endi kuzatuvdan chiqaramiz:

```bash
git rm -r --cached venv mobile/build mobile/.dart_tool .idea
git rm --cached --ignore-unmatch .env .env.production db.sqlite3   # maxfiy/baza
git rm --cached $(git ls-files '*.iml')          # *.iml fayllar (bo'lsa)
git commit -m "chore: stop tracking venv/build/.dart_tool/.env/db files"
```

> 💡 Eng oson yo'l — tayyor skript: `cleanup.ps1` (Windows) yoki `cleanup.sh` (Linux/macOS).
> U yuqoridagilarni avtomatik bajaradi va hisobotlarni `docs/` ga ko'chiradi.

> 🔴 `.env` yoki `SECRET_KEY` GitHub'ga chiqqan bo'lsa — tarixdan o'chirish ham
> yetarli emas. **Kalitni darhol ALMASHTIRING** (yangi generatsiya qiling):
> `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

Endi `git ls-files | grep -E 'venv/|mobile/build/|\.dart_tool/'` **bo'sh** chiqishi kerak.

## 2. Maxfiy Chrome profilini tasdiqlab o'chirish

`mobile/.dart_tool/chrome-device/` — bu Flutter web debug Chrome profili,
**cookie / sessiya / tarix** bo'lishi mumkin. Diskdan ham o'chiring:

```bash
# Windows (PowerShell):
Remove-Item -Recurse -Force mobile\.dart_tool\chrome-device
# Linux/macOS:
rm -rf mobile/.dart_tool/chrome-device
```

(Yuqoridagi `git rm -r --cached mobile/.dart_tool` uni kuzatuvdan ham chiqaradi.)

## 3. Tarixdan butunlay tozalash (hajmni kichraytirish)

Faqat 1-qadam fayllarni keyingi commitlardan chiqaradi, lekin ular **tarixda**
qoladi (repo hajmi katta). To'liq tozalash uchun `git filter-repo` (tavsiya etiladi):

```bash
# O'rnatish:  pip install git-filter-repo
git filter-repo --force \
  --path venv --path mobile/build --path mobile/.dart_tool --path .idea \
  --path-glob '*.iml' --invert-paths
```

`git filter-repo` bo'lmasa, **BFG** bilan:

```bash
# bfg.jar yuklab oling: https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --delete-folders "{venv,build,.dart_tool,.idea}" --no-blob-protection
git reflog expire --expire=now --all && git gc --prune=now --aggressive
```

## 4. Remote'ni majburan yangilash

```bash
git push origin --force --all
git push origin --force --tags
```

> Maxfiy ma'lumot (chrome-device cookie/sessiya) tarixda bo'lgani uchun, agar
> repo ommaviy bo'lsa — har qanday sessiya/token'ni **bekor qiling** (rotate).

## 5. Tekshirish (bajarildi mezoni)

```bash
git ls-files | grep -E 'venv/|mobile/build/|\.dart_tool/|\.iml$'   # bo'sh bo'lsin
du -sh .git                                                        # hajm keskin kichrayadi
```

Toza klondan keyin ishga tushirish uchun → `README.md`, 1 va 4 bo'limlar.
