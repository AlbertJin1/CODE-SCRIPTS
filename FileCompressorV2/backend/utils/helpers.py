# utils/helpers.py
import logging
import os


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[
            logging.FileHandler("compression.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logging.getLogger("PIL").setLevel(logging.WARNING)


def get_compressed_name(path):
    dir_name = os.path.dirname(path)
    name, ext = os.path.splitext(os.path.basename(path))
    return os.path.join(dir_name, f"{name}_compressed{ext}")
