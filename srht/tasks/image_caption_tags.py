import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import magic
from sqlalchemy import func

from srht.database import db
from srht.objects import Job, Tag, Upload
from srht.tasks import Task, TaskType

logger = logging.getLogger(__name__)

# Set HF_HOME to use pre-cached models in Docker, or default to user home
if not os.environ.get("HF_HOME"):
    os.environ["HF_HOME"] = os.path.expanduser("~/.cache/huggingface")

_HAS_ML_DEPS: bool | None = None
_ML_IMPORT_ERROR: str | None = None
_PIL_IMAGE: Any = None
_KEYBERT_CLASS: Any = None
_AUTO_MODEL_CLASS: Any = None
_AUTO_TOKENIZER_CLASS: Any = None

_MOONDREAM_MODEL = None
_MOONDREAM_TOKENIZER = None
_KEYBERT_MODEL = None


class _CaptionTagTaskBase(Task):
    """Shared caption and tag helpers for image processing tasks."""

    ALLOWED_IMAGE_MIME_TYPES = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    }
    ALLOWED_VIDEO_MIME_TYPES = {
        "video/mp4",
        "video/quicktime",
        "video/x-msvideo",
        "video/x-matroska",
        "video/webm",
    }
    ALLOWED_MIME_TYPES = ALLOWED_IMAGE_MIME_TYPES | ALLOWED_VIDEO_MIME_TYPES
    COMMIT_CHUNK_SIZE = 20

    def _resolve_caption_source(self, uploaded_file: Upload) -> tuple[Path | None, str | None]:
        uploaded_file_path = uploaded_file.get_storage_path()
        guessed_mimetype = magic.from_file(uploaded_file_path, mime=True)
        if guessed_mimetype not in self.ALLOWED_MIME_TYPES:
            return None, guessed_mimetype

        if guessed_mimetype in self.ALLOWED_VIDEO_MIME_TYPES:
            if uploaded_file.thumbnail is None:
                return None, guessed_mimetype
            uploaded_file_path = uploaded_file.get_storage_path().parent / uploaded_file.thumbnail

        return uploaded_file_path, guessed_mimetype

    def _insert_missing_tags(
        self, uploadid: int, normalized_tags_with_scores: dict[str, float]
    ) -> int:
        normalized_tags = list(normalized_tags_with_scores.keys())
        if not normalized_tags:
            return 0

        existing_tags = {
            row[0]
            for row in db.session.query(Tag.tag)
            .filter(Tag.uploadid == uploadid)
            .filter(func.lower(Tag.tag).in_(normalized_tags))
            .all()
        }

        to_insert = [tag for tag in normalized_tags if tag not in existing_tags]
        for tag in to_insert:
            db.session.add(
                Tag(
                    uploadid=uploadid,
                    tag=tag,
                    relevance=normalized_tags_with_scores[tag],
                )
            )
        return len(to_insert)

    def _get_moondream_model(self):
        global _MOONDREAM_MODEL, _MOONDREAM_TOKENIZER

        if not self._ensure_ml_dependencies():
            raise RuntimeError("ML dependencies are not available")

        if _MOONDREAM_MODEL is None or _MOONDREAM_TOKENIZER is None:
            _MOONDREAM_MODEL = _AUTO_MODEL_CLASS.from_pretrained(
                "vikhyatk/moondream2",
                trust_remote_code=True,
                attn_implementation="eager",
            )
            _MOONDREAM_TOKENIZER = _AUTO_TOKENIZER_CLASS.from_pretrained(
                "vikhyatk/moondream2",
                trust_remote_code=True,
            )

        return _MOONDREAM_MODEL, _MOONDREAM_TOKENIZER

    def _get_keybert_model(self):
        global _KEYBERT_MODEL

        if not self._ensure_ml_dependencies():
            raise RuntimeError("ML dependencies are not available")

        if _KEYBERT_MODEL is None:
            _KEYBERT_MODEL = _KEYBERT_CLASS()

        return _KEYBERT_MODEL

    def _generate_caption(self, uploaded_file_path: Path) -> str:
        model, tokenizer = self._get_moondream_model()
        with _PIL_IMAGE.open(uploaded_file_path) as image:
            if hasattr(model, "caption"):
                caption = model.caption(image)
                if isinstance(caption, dict):
                    return str(caption.get("caption") or caption.get("text") or "").strip()
                return str(caption).strip()

        return ""

    def _ensure_ml_dependencies(self) -> bool:
        global _HAS_ML_DEPS, _ML_IMPORT_ERROR
        global _PIL_IMAGE, _KEYBERT_CLASS, _AUTO_MODEL_CLASS, _AUTO_TOKENIZER_CLASS

        if _HAS_ML_DEPS is not None:
            return _HAS_ML_DEPS

        try:
            from PIL import Image
            from keybert import KeyBERT
            from transformers import AutoModelForCausalLM, AutoTokenizer

            _PIL_IMAGE = Image
            _KEYBERT_CLASS = KeyBERT
            _AUTO_MODEL_CLASS = AutoModelForCausalLM
            _AUTO_TOKENIZER_CLASS = AutoTokenizer
            _HAS_ML_DEPS = True
            _ML_IMPORT_ERROR = None
        except Exception as exc:
            _HAS_ML_DEPS = False
            _ML_IMPORT_ERROR = str(exc)

        return _HAS_ML_DEPS

    def _extract_tags(self, caption: str) -> list[tuple[str, float]]:
        keybert_model = self._get_keybert_model()
        keyphrases = keybert_model.extract_keywords(
            caption,
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            top_n=12,
        )
        return [
            (str(item[0]), float(item[1]))
            for item in keyphrases
            if item and len(item) >= 2 and item[0]
        ]

    def _normalize_tags(self, tags: list[tuple[str, float]]) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for tag, relevance in tags:
            cleaned = re.sub(r"\s+", " ", tag.strip().lower())
            cleaned = re.sub(r"[^a-z0-9\- ]", "", cleaned)
            cleaned = cleaned.strip()
            if len(cleaned) < 2:
                continue
            if len(cleaned) > 64:
                cleaned = cleaned[:64].strip()
            if not cleaned:
                continue
            current = normalized.get(cleaned)
            if current is None or relevance > current:
                normalized[cleaned] = relevance
        return normalized


class BatchGenerateImageCaptions(_CaptionTagTaskBase):
    """Batch caption generation task that loads moondream once per job."""

    type = TaskType.BATCH_CAPTIONS

    def __init__(
        self,
        upload_ids: list[int] | None = None,
        job: Job | None = None,
        failure_count: int = 0,
    ):
        self.upload_ids = upload_ids or []
        super().__init__(job=job, failure_count=failure_count)

    def get_as_json(self) -> dict:
        data = super().get_as_json()
        data.update({"upload_ids": self.upload_ids})
        return data

    def execute(self):
        if not self.upload_ids:
            self.log_message("No uploads selected for caption batch, skipping")
            return

        if not self._ensure_ml_dependencies():
            self.log_message(
                f"Caption dependencies are unavailable, skipping batch: {_ML_IMPORT_ERROR}",
                log_level=logging.WARNING,
            )
            return

        # Warm once so the model is loaded a single time for this batch.
        self._get_moondream_model()

        attempted = 0
        succeeded = 0
        skipped = 0
        failed = 0
        started_at = time.perf_counter()

        for idx, upload_id in enumerate(self.upload_ids, start=1):
            attempted += 1
            try:
                uploaded_file = Upload.query.filter(Upload.id == upload_id).one_or_none()
                self.log_message(f"Processing caption for upload {upload_id}: {uploaded_file}")
                if uploaded_file is None:
                    skipped += 1
                    continue

                if uploaded_file.caption:
                    skipped += 1
                    continue

                uploaded_file_path, guessed_mimetype = self._resolve_caption_source(uploaded_file)
                if uploaded_file_path is None:
                    skipped += 1
                    if guessed_mimetype in self.ALLOWED_VIDEO_MIME_TYPES:
                        self.log_message(
                            f"Skipping upload {upload_id} in caption batch: thumbnail not ready"
                        )
                    else:
                        self.log_message(
                            (
                                f"Skipping upload {upload_id} in caption batch: unsupported mimetype "
                                f"{guessed_mimetype!r}"
                            )
                        )
                    continue

                caption = self._generate_caption(uploaded_file_path)
                self.log_message(f"Generated caption for upload {upload_id}: {caption!r}")
                if not caption:
                    skipped += 1
                    continue

                uploaded_file.caption = caption
                db.session.add(uploaded_file)
                succeeded += 1

                if idx % self.COMMIT_CHUNK_SIZE == 0:
                    db.session.commit()
            except Exception as exc:
                failed += 1
                db.session.rollback()
                self.log_message(
                    f"Caption batch failed for upload {upload_id}: {exc}",
                    log_level=logging.ERROR,
                )

        db.session.commit()
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        self.log_message(
            (
                "Caption batch completed: "
                f"attempted={attempted}, succeeded={succeeded}, skipped={skipped}, "
                f"failed={failed}, elapsed_ms={elapsed_ms}"
            )
        )


class BatchGenerateImageTags(_CaptionTagTaskBase):
    """Batch tag generation task that loads KeyBERT once per job."""

    type = TaskType.BATCH_TAGS

    def __init__(
        self,
        upload_ids: list[int] | None = None,
        job: Job | None = None,
        failure_count: int = 0,
    ):
        self.upload_ids = upload_ids or []
        super().__init__(job=job, failure_count=failure_count)

    def get_as_json(self) -> dict:
        data = super().get_as_json()
        data.update({"upload_ids": self.upload_ids})
        return data

    def execute(self):
        if not self.upload_ids:
            self.log_message("No uploads selected for tag batch, skipping")
            return

        if not self._ensure_ml_dependencies():
            self.log_message(
                f"Tag dependencies are unavailable, skipping batch: {_ML_IMPORT_ERROR}",
                log_level=logging.WARNING,
            )
            return

        # Warm once so the keyphrase model is loaded a single time for this batch.
        self._get_keybert_model()

        attempted = 0
        succeeded = 0
        skipped = 0
        failed = 0
        inserted_total = 0
        started_at = time.perf_counter()

        for idx, upload_id in enumerate(self.upload_ids, start=1):
            attempted += 1
            try:
                uploaded_file = Upload.query.filter(Upload.id == upload_id).one_or_none()
                if uploaded_file is None or not uploaded_file.caption:
                    skipped += 1
                    continue

                tags = self._extract_tags(uploaded_file.caption)
                if not tags:
                    skipped += 1
                    continue

                normalized_tags = self._normalize_tags(tags)
                if not normalized_tags:
                    skipped += 1
                    continue

                inserted_count = self._insert_missing_tags(upload_id, normalized_tags)
                inserted_total += inserted_count
                if inserted_count == 0:
                    skipped += 1
                else:
                    succeeded += 1
                self.log_message(f"Processed tags for upload {upload_id}: {normalized_tags}")
                if idx % self.COMMIT_CHUNK_SIZE == 0:
                    db.session.commit()
            except Exception as exc:
                failed += 1
                db.session.rollback()
                self.log_message(
                    f"Tag batch failed for upload {upload_id}: {exc}",
                    log_level=logging.ERROR,
                )

        db.session.commit()
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        self.log_message(
            (
                "Tag batch completed: "
                f"attempted={attempted}, succeeded={succeeded}, skipped={skipped}, "
                f"failed={failed}, inserted_tags={inserted_total}, elapsed_ms={elapsed_ms}"
            )
        )
