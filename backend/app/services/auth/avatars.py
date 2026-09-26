"""Bounded avatar decoding and metadata-free image normalization."""

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_AVATAR_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_AVATAR_PIXELS = 20_000_000
AVATAR_SIZE = 256


class InvalidAvatar(ValueError):
    pass


def normalize_avatar(content: bytes) -> bytes:
    if not content or len(content) > MAX_AVATAR_UPLOAD_BYTES:
        raise InvalidAvatar("Choose an image smaller than 4 MB.")

    try:
        with Image.open(BytesIO(content)) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise InvalidAvatar("Only JPEG, PNG and WebP images are supported.")
            if (
                image.width < 1
                or image.height < 1
                or image.width * image.height > MAX_AVATAR_PIXELS
                or getattr(image, "n_frames", 1) != 1
            ):
                raise InvalidAvatar("The image dimensions are not supported.")
            image.load()
            oriented = ImageOps.exif_transpose(image)
            mode = (
                "RGBA"
                if "A" in oriented.getbands() or "transparency" in oriented.info
                else "RGB"
            )
            square = ImageOps.fit(
                oriented.convert(mode),
                (AVATAR_SIZE, AVATAR_SIZE),
                method=Image.Resampling.LANCZOS,
            )
            output = BytesIO()
            square.save(output, format="WEBP", quality=85, method=4)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidAvatar("The image could not be decoded.") from exc
