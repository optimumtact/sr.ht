import logging
import time
from pathlib import Path
from xml.sax.saxutils import escape

import magic
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image

from srht.database import db
from srht.objects import Job, Upload
from srht.tasks import Task, TaskType
from srht.tasks.image_caption_tags import GenerateImageCaptionTags

logger = logging.getLogger(__name__)


class GenerateImageThumbnail(Task):
    """An executable task"""

    type = TaskType.THUMBNAIL
    ALLOWED_IMAGE_EXTENSIONS = {
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "tif",
        "tiff",
        "webp",
        "dmi",
    }
    ALLOWED_VIDEO_EXTENSIONS = {
        "mp4",
        "m4v",
        "mov",
        "webm",
        "avi",
        "mkv",
        "mpg",
        "mpeg",
        "quicktime",
    }

    def __init__(self, uploadid: int, job: Job | None = None, failure_count: int = 0):
        self.uploadid = uploadid
        super().__init__(job=job, failure_count=failure_count)

    def get_as_json(self) -> dict:
        data = super().get_as_json()
        data.update({"uploadid": self.uploadid})
        return data

    def execute(self):
        uploaded_file = Upload.query.filter(Upload.id == self.uploadid).one()
        thumbnail = self.generate_thumbnail(
            uploaded_file.get_storage_path(), uploaded_file.get_thumbnail_path()
        )
        uploaded_file.thumbnail = "thumbnails" + "/" + thumbnail.name
        db.session.add(uploaded_file)
        db.session.commit()

        # Queue caption/tag generation after thumbnail is ready
        caption_task = GenerateImageCaptionTags(self.uploadid)
        caption_task.queue()

    def is_valid_image_pillow(self, file_name: Path) -> bool:
        """Check if an image is a valid iamge

        Args:
            file_name (Path): The file path to check

        Returns:
            bool: True if the image is a valid image
        """
        try:
            with Image.open(file_name) as img:
                img.verify()
                return True
        except (IOError, SyntaxError):
            return False

    def allowed_extension(self, extension: str) -> bool:
        """Check if an extension is allowed

        Args:
            extension (str): The file extension to check
        """
        normalized_extension = extension.lower().lstrip(".")
        return normalized_extension in (
            self.ALLOWED_IMAGE_EXTENSIONS | self.ALLOWED_VIDEO_EXTENSIONS
        )

    def generate_thumbnail(
        self, uploaded_file_path: Path, thumbnail_path: Path, size=(500, 500)
    ) -> Path:
        """Generate a thumbnail from a given file path
        will attempt to guess the media type and use PIL or pyvideo as needed

        Args:
            image_path (Path): The image path
            thumbnail_path (Path): The thumbnail directory
            size (tuple, optional): The image size. Defaults to (128, 128).

        Returns:
            bool: True if the thumbnail was created successfully.
        """

        guessed_mimetype = magic.from_file(uploaded_file_path, mime=True)
        if guessed_mimetype is not None:
            type, extension = guessed_mimetype.split("/")
            if type not in ["image", "video"]:
                return self.generate_unknown_thumbnail(
                    uploaded_file_path,
                    thumbnail_path.joinpath(uploaded_file_path.stem + ".svg"),
                    extension=uploaded_file_path.suffix.lstrip("."),
                    size=size,
                )

            if not self.allowed_extension(extension):
                # Fall back rather than feeding uncommon formats into Pillow/moviepy.
                return self.generate_unknown_thumbnail(
                    uploaded_file_path,
                    thumbnail_path.joinpath(uploaded_file_path.stem + ".svg"),
                    extension=extension,
                    size=size,
                )

            # Use the extension from the mimetype. This is because some files may have the wrong extension, and we want to be able to handle that. We also want to be able to handle files with no extension.
            thumbnail_file_path = thumbnail_path.joinpath(uploaded_file_path.stem + f".{extension}")
            if type == "image":
                # Does pillow recognise it, otherwise fall through to the default
                if self.is_valid_image_pillow(uploaded_file_path):
                    return self.generate_image_thumbnail(
                        uploaded_file_path, thumbnail_file_path, size
                    )
            if type == "video":
                # We want to save the first frame as a png
                thumbnail_file_path = thumbnail_path.joinpath(uploaded_file_path.stem + ".png")
                return self.generate_video_thumbnail(uploaded_file_path, thumbnail_file_path, size)
        # Not sure how you got here.
        self.log_message(
            f"Could not determine file type for {uploaded_file_path}, generating file thumbnail",
            log_level=logging.WARNING,
        )
        thumbnail_file_path = thumbnail_path.joinpath(uploaded_file_path.stem + ".svg")
        return self.generate_unknown_thumbnail(
            uploaded_file_path,
            thumbnail_file_path,
            extension=uploaded_file_path.suffix.lstrip("."),
            size=size,
        )

    def generate_unknown_thumbnail(
        self,
        uploaded_file_path: Path,
        thumbnail_file_path: Path,
        extension: str = "",
        size=(128, 128),
    ) -> Path:
        self.log_message(f"Generating file thumbnail to {thumbnail_file_path}")
        width, height = size
        display_extension = (extension or uploaded_file_path.suffix.lstrip(".") or "file").upper()
        display_extension = escape(display_extension[:8])
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{display_extension} file thumbnail">
  <rect width="100%" height="100%" rx="18" fill="#f4f4f4"/>
  <path d="M{width * 0.28:.2f} {height * 0.16:.2f}h{width * 0.28:.2f}l{width * 0.16:.2f} {height * 0.16:.2f}v{height * 0.48:.2f}a{width * 0.04:.2f} {height * 0.04:.2f} 0 0 1 -{width * 0.04:.2f} {height * 0.04:.2f}H{width * 0.32:.2f}a{width * 0.04:.2f} {height * 0.04:.2f} 0 0 1 -{width * 0.04:.2f} -{height * 0.04:.2f}V{height * 0.20:.2f}a{width * 0.04:.2f} {height * 0.04:.2f} 0 0 1 {width * 0.04:.2f} -{height * 0.04:.2f}z" fill="#ffffff" stroke="#bfc3c9" stroke-width="2"/>
  <path d="M{width * 0.56:.2f} {height * 0.16:.2f}v{height * 0.16:.2f}h{width * 0.16:.2f}" fill="#e7eaf0" stroke="#bfc3c9" stroke-width="2"/>
  <rect x="{width * 0.20:.2f}" y="{height * 0.66:.2f}" width="{width * 0.60:.2f}" height="{height * 0.16:.2f}" rx="10" fill="#2f6fed"/>
  <text x="50%" y="{height * 0.77:.2f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="{max(14, int(height * 0.12))}" font-weight="700" fill="#ffffff">{display_extension}</text>
</svg>"""
        thumbnail_file_path.write_text(svg, encoding="utf-8")
        return thumbnail_file_path

    def generate_video_thumbnail(
        self, uploaded_file_path: Path, thumbnail_file_path: Path, size=(128, 128)
    ) -> Path:
        self.log_message(f"Generating video thumbnail to {thumbnail_file_path}")
        video = VideoFileClip(uploaded_file_path.as_posix())
        # Either get the 25th second, or if the video is smaller than that, 1/3rd of whatever it's duration is
        frame = min(25, video.duration / 3)
        video.save_frame(thumbnail_file_path, t=frame)
        # Now we defer to the thumbnail generation
        self.generate_image_thumbnail(thumbnail_file_path, thumbnail_file_path, size)
        return thumbnail_file_path

    def generate_image_thumbnail(
        self, uploaded_file_path: Path, thumbnail_file_path: Path, size=(128, 128)
    ) -> Path:
        self.log_message(f"Generating image thumbnail to {thumbnail_file_path}")
        with Image.open(uploaded_file_path) as img:
            img.thumbnail(size)
            img.save(thumbnail_file_path)
            return thumbnail_file_path
