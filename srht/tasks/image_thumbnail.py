import time
from pathlib import Path

import magic
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image

from srht.database import db
from srht.objects import Upload
from srht.tasks import Task, TaskType


class GenerateImageThumbnail(Task):
    """An executable task"""

    def __init__(self, uploadid: int):
        super().__init__()
        self.uploadid = uploadid
        self.type = TaskType.THUMBNAIL

    def execute(self):
        uploaded_file = Upload.query.filter(Upload.id == self.uploadid).one()
        thumbnail = self.generate_thumbnail(
            uploaded_file.get_storage_path(), uploaded_file.get_thumbnail_path()
        )
        uploaded_file.thumbnail = "thumbnails" + "/" + thumbnail.name
        db.session.add(uploaded_file)

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
        thumbnail_file_path = thumbnail_path.joinpath(uploaded_file_path.name)
        guessed_mimetype = magic.from_file(uploaded_file_path, mime=True)
        if guessed_mimetype is not None:
            type, extension = guessed_mimetype.split("/")
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
        # Unknown file type, just leave it as a blank image
        thumbnail_file_path = thumbnail_path.joinpath(uploaded_file_path.stem + ".png")
        return self.generate_blank_thumbnail(uploaded_file_path, thumbnail_file_path, size)

    def generate_blank_thumbnail(
        self, uploaded_file_path: Path, thumbnail_file_path: Path, size=(128, 128)  #
    ) -> Path:
        color = (255, 255, 255, 0)
        image = Image.new("RGBA", (size[0], size[1]), color)
        image.save(thumbnail_file_path)
        return thumbnail_file_path

    def generate_video_thumbnail(
        self, uploaded_file_path: Path, thumbnail_file_path: Path, size=(128, 128)
    ) -> Path:
        print(f"Generating video thumbnail to {thumbnail_file_path}")
        video = VideoFileClip(uploaded_file_path.as_posix())
        video.save_frame(thumbnail_file_path, t=min(0.25, video.duration / 3))
        # Now we defer to the thumbnail generation
        self.generate_image_thumbnail(thumbnail_file_path, thumbnail_file_path, size)
        return thumbnail_file_path

    def generate_image_thumbnail(
        self, uploaded_file_path: Path, thumbnail_file_path: Path, size=(128, 128)
    ) -> Path:
        with Image.open(uploaded_file_path) as img:
            img.thumbnail(size)
            img.save(thumbnail_file_path)
            return thumbnail_file_path
