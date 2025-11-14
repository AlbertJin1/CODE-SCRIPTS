# core/image_compressor.py
from PIL import Image
import os
import logging
from utils.helpers import get_compressed_name

log = logging.getLogger(__name__)


def compress_image(input_path, output_path, quality=75):
    try:
        with Image.open(input_path) as img:
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            img.save(output_path, "JPEG", quality=quality, optimize=True)
            log.info(f"Image compressed: {os.path.basename(input_path)} → {quality}%")
            return True, os.path.getsize(output_path)
    except Exception as e:
        log.error(f"Image compression failed: {e}")
        return False, os.path.getsize(input_path)
