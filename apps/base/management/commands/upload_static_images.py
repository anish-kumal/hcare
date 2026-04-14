from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable

from cloudinary.uploader import upload as cloudinary_upload
from cloudinary.models import CloudinaryField
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db.models import FileField
from django.db.models.fields.files import ImageField
from django.utils.text import slugify


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg"}


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def list_image_files(source_dir: Path) -> list[Path]:
    return sorted(
        [path for path in source_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda p: p.name.lower(),
    )


class Command(BaseCommand):
    help = (
        "Upload local static images one-by-one to cloud storage and update a model image/file field. "
        "Useful for seeding model images from static directories."
    )

    def add_arguments(self, parser):
        parser.add_argument("--app", required=True, help="Django app label, e.g. hospitals")
        parser.add_argument("--model", required=True, help="Model class name, e.g. Hospital")
        parser.add_argument("--image-field", required=True, help="Model field to store uploaded cloud file")
        parser.add_argument("--name-field", default="name", help="Field used for name-based matching")
        parser.add_argument(
            "--source-dir",
            default="static/images",
            help="Local folder containing source images (default: static/images)",
        )
        parser.add_argument(
            "--match-mode",
            choices=["name", "index"],
            default="name",
            help="name: match by model name <-> file name; index: assign by order one-by-one",
        )
        parser.add_argument(
            "--cloud",
            choices=["cloudinary"],
            default="cloudinary",
            help="Cloud backend to use (currently supports cloudinary)",
        )
        parser.add_argument(
            "--cloud-folder",
            default="health_care/seeded_images",
            help="Remote cloud folder where images are uploaded",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing model images. Without this flag, non-empty fields are skipped.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Preview changes without uploading/saving")

    def handle(self, *args, **options):
        model = self._get_model(options["app"], options["model"])
        image_field_name = options["image_field"]
        name_field_name = options["name_field"]
        source_dir = Path(options["source_dir"])
        match_mode = options["match_mode"]
        cloud_folder = options["cloud_folder"].strip("/")
        dry_run = options["dry_run"]
        overwrite = options["overwrite"]

        if not source_dir.exists() or not source_dir.is_dir():
            raise CommandError(f"Source directory does not exist: {source_dir}")

        self._validate_image_field(model, image_field_name)
        if match_mode == "name":
            self._validate_name_field(model, name_field_name)

        images = list_image_files(source_dir)
        if not images:
            raise CommandError(f"No image files found in {source_dir}")

        queryset = model.objects.all().order_by("id")
        if not queryset.exists():
            raise CommandError(f"No records found in {model._meta.label}")

        self.stdout.write(self.style.NOTICE(f"Found {len(images)} image(s) in {source_dir}"))
        self.stdout.write(self.style.NOTICE(f"Target model: {model._meta.label}"))
        self.stdout.write(self.style.NOTICE(f"Target field: {image_field_name}"))
        self.stdout.write(self.style.NOTICE(f"Match mode: {match_mode}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Running in dry-run mode (no uploads, no database updates)."))

        if match_mode == "name":
            updated, skipped, failed = self._process_by_name(
                queryset=queryset,
                images=images,
                name_field=name_field_name,
                image_field=image_field_name,
                cloud_folder=cloud_folder,
                dry_run=dry_run,
                overwrite=overwrite,
            )
        else:
            updated, skipped, failed = self._process_by_index(
                queryset=queryset,
                images=images,
                image_field=image_field_name,
                cloud_folder=cloud_folder,
                dry_run=dry_run,
                overwrite=overwrite,
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Updated: {updated}"))
        self.stdout.write(self.style.WARNING(f"Skipped: {skipped}"))
        if failed:
            self.stdout.write(self.style.ERROR(f"Failed: {failed}"))
            raise CommandError("Completed with failures. See logs above.")

    def _get_model(self, app_label: str, model_name: str):
        try:
            return apps.get_model(app_label, model_name)
        except LookupError as exc:
            raise CommandError(f"Invalid model reference {app_label}.{model_name}") from exc

    def _validate_image_field(self, model, field_name: str) -> None:
        try:
            field = model._meta.get_field(field_name)
        except Exception as exc:
            raise CommandError(f"Field '{field_name}' does not exist on {model._meta.label}") from exc

        if not isinstance(field, (ImageField, FileField, CloudinaryField)):
            raise CommandError(
                f"Field '{field_name}' on {model._meta.label} must be ImageField/FileField/CloudinaryField-compatible."
            )

    def _validate_name_field(self, model, field_name: str) -> None:
        try:
            model._meta.get_field(field_name)
        except Exception as exc:
            raise CommandError(f"Name field '{field_name}' does not exist on {model._meta.label}") from exc

    def _upload_to_cloudinary(self, image_path: Path, cloud_folder: str, public_id_base: str) -> str:
        result = cloudinary_upload(
            str(image_path),
            folder=cloud_folder,
            public_id=public_id_base,
            overwrite=True,
            resource_type="image",
        )
        return result["public_id"]

    def _process_by_name(
        self,
        queryset,
        images: Iterable[Path],
        name_field: str,
        image_field: str,
        cloud_folder: str,
        dry_run: bool,
        overwrite: bool,
    ) -> tuple[int, int, int]:
        file_map = {normalize_text(path.stem): path for path in images}
        updated = skipped = failed = 0

        for obj in queryset:
            display_name = str(getattr(obj, name_field, "") or "")
            normalized_name = normalize_text(display_name)
            if not normalized_name:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"SKIP {obj.pk}: empty {name_field}"))
                continue

            image_path = file_map.get(normalized_name)
            if not image_path:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"SKIP {obj.pk}: no image matched '{display_name}'"))
                continue

            current_value = getattr(obj, image_field)
            if current_value and not overwrite:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"SKIP {obj.pk}: {image_field} already set"))
                continue

            try:
                public_id = f"{slugify(display_name) or 'record'}-{obj.pk}"
                if dry_run:
                    self.stdout.write(f"DRY-RUN {obj.pk}: {image_path.name} -> {cloud_folder}/{public_id}")
                else:
                    uploaded_public_id = self._upload_to_cloudinary(image_path, cloud_folder, public_id)
                    setattr(obj, image_field, uploaded_public_id)
                    obj.save(update_fields=[image_field])
                    self.stdout.write(self.style.SUCCESS(f"UPDATED {obj.pk}: {image_path.name} -> {uploaded_public_id}"))
                updated += 1
            except Exception as exc:
                failed += 1
                self.stdout.write(self.style.ERROR(f"FAIL {obj.pk}: {image_path.name} ({exc})"))

        return updated, skipped, failed

    def _process_by_index(
        self,
        queryset,
        images: list[Path],
        image_field: str,
        cloud_folder: str,
        dry_run: bool,
        overwrite: bool,
    ) -> tuple[int, int, int]:
        updated = skipped = failed = 0
        records = list(queryset)

        if len(images) < len(records):
            self.stdout.write(
                self.style.WARNING(
                    f"Only {len(images)} image(s) available for {len(records)} records. Remaining records will be skipped."
                )
            )

        for index, obj in enumerate(records):
            if index >= len(images):
                skipped += 1
                continue

            image_path = images[index]
            current_value = getattr(obj, image_field)
            if current_value and not overwrite:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"SKIP {obj.pk}: {image_field} already set"))
                continue

            try:
                public_id = f"{slugify(model_name := obj._meta.model_name)}-{obj.pk}-{index + 1}"
                if dry_run:
                    self.stdout.write(f"DRY-RUN {obj.pk}: {image_path.name} -> {cloud_folder}/{public_id}")
                else:
                    uploaded_public_id = self._upload_to_cloudinary(image_path, cloud_folder, public_id)
                    setattr(obj, image_field, uploaded_public_id)
                    obj.save(update_fields=[image_field])
                    self.stdout.write(self.style.SUCCESS(f"UPDATED {obj.pk}: {image_path.name} -> {uploaded_public_id}"))
                updated += 1
            except Exception as exc:
                failed += 1
                self.stdout.write(self.style.ERROR(f"FAIL {obj.pk}: {image_path.name} ({exc})"))

        return updated, skipped, failed
