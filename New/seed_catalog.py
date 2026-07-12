"""
SamCity — catalog seeder.

Place at:  catalog/management/commands/seed_catalog.py

Run:
    unzip catalog_images.zip -d media/            # -> media/catalog/*.webp
    python manage.py seed_catalog --json catalog_150_products.json

Idempotent: re-running updates existing rows instead of duplicating them.

Assumed models (adjust field names to match your app):

    class Category(models.Model):
        name = models.CharField(max_length=120, unique=True)
        slug = models.SlugField(max_length=120, unique=True)

    class Subcategory(models.Model):
        category = models.ForeignKey(Category, related_name="subcategories",
                                     on_delete=models.CASCADE)
        name = models.CharField(max_length=120)
        slug = models.SlugField(max_length=120)
        class Meta:
            unique_together = ("category", "slug")

    class Product(models.Model):
        name        = models.CharField(max_length=200)
        slug        = models.SlugField(max_length=200, unique=True)
        brand       = models.CharField(max_length=100, blank=True)
        subcategory = models.ForeignKey(Subcategory, related_name="products",
                                        on_delete=models.PROTECT)
        unit        = models.CharField(max_length=20)
        description = models.TextField(blank=True)
        image       = models.ImageField(upload_to="catalog/", blank=True)
"""
import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from catalog.models import Category, Product, Subcategory  # adjust import


class Command(BaseCommand):
    help = "Seed the SamCity product catalog from catalog_150_products.json"

    def add_arguments(self, parser):
        parser.add_argument("--json", default="catalog_150_products.json")
        parser.add_argument(
            "--media-root",
            default=None,
            help="Where catalog/*.webp live. Defaults to settings.MEDIA_ROOT.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Abort if any referenced image file is missing.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["json"]
        if not os.path.exists(path):
            raise CommandError(f"Not found: {path}")

        media_root = opts["media_root"] or settings.MEDIA_ROOT
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        # ---- categories / subcategories --------------------------------
        subs = {}
        for cat in data["categories"]:
            category, _ = Category.objects.update_or_create(
                slug=cat["slug"], defaults={"name": cat["name"]}
            )
            for sub in cat["subcategories"]:
                subcategory, _ = Subcategory.objects.update_or_create(
                    category=category,
                    slug=sub["slug"],
                    defaults={"name": sub["name"]},
                )
                subs[(cat["name"], sub["name"])] = subcategory

        # ---- pre-flight: every image must exist ------------------------
        missing = [
            p["image_path"]
            for p in data["products"]
            if not os.path.exists(os.path.join(media_root, p["image_path"]))
        ]
        if missing:
            msg = f"{len(missing)} image(s) missing under {media_root}, e.g. {missing[:3]}"
            if opts["strict"]:
                raise CommandError(msg + "  (did you unzip catalog_images.zip into MEDIA_ROOT?)")
            self.stderr.write(self.style.WARNING(msg))

        # ---- products ---------------------------------------------------
        created = updated = 0
        for p in data["products"]:
            key = (p["category"], p["subcategory"])
            if key not in subs:
                raise CommandError(f"Unknown category pair for {p['name']}: {key}")

            _, was_created = Product.objects.update_or_create(
                slug=slugify(p["name"]),
                defaults={
                    "name": p["name"],
                    "brand": p["brand"],
                    "subcategory": subs[key],
                    "unit": p["unit"],
                    "description": p["description"],
                    # image_path is already relative to MEDIA_ROOT, so assign
                    # it straight to the ImageField — no file copy needed.
                    "image": p["image_path"],
                },
            )
            created += was_created
            updated += not was_created

        self.stdout.write(
            self.style.SUCCESS(
                f"Categories: {Category.objects.count()} | "
                f"Subcategories: {Subcategory.objects.count()} | "
                f"Products created: {created}, updated: {updated}"
            )
        )
