# core/office_compressor.py
import zipfile
import tempfile
import shutil
import os
import logging

log = logging.getLogger(__name__)


def compress_office_to_target(input_path, output_path, target_bytes, update_callback):
    best_file = None
    best_size = float("inf")
    ext = os.path.splitext(input_path)[1].lower()

    for level in range(9, 0, -1):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=ext).name
        try:
            with zipfile.ZipFile(input_path, "r") as zin, zipfile.ZipFile(
                temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=level
            ) as zout:
                items = zin.infolist()
                for i, item in enumerate(items):
                    zout.writestr(item, zin.read(item.filename))
                    progress = 20 + (70 * (10 - level + i / len(items)) / 9)
                    update_callback(int(progress), f"Level {level}")

            size = os.path.getsize(temp)
            log.info(f"Level {level}: {size / (1024*1024):.2f} MB")

            if size <= target_bytes:
                shutil.move(temp, output_path)
                update_callback(100, "Done!")
                return True, size

            if size < best_size:
                best_size = size
                if best_file:
                    os.unlink(best_file)
                best_file = temp
            else:
                os.unlink(temp)

        except Exception as e:
            log.error(f"Level {level} failed: {e}")
            if os.path.exists(temp):
                os.unlink(temp)

    if best_file:
        shutil.move(best_file, output_path)
        update_callback(100, "Best!")
        return True, best_size

    update_callback(100, "No change")
    return False, os.path.getsize(input_path)
