# core/pdf_compressor.py
import tempfile
import shutil
import os
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import NameObject, NumberObject
from PIL import Image
from io import BytesIO
import logging

log = logging.getLogger(__name__)


def compress_pdf_to_target(input_path, output_path, target_bytes, update_callback):
    best_file = None
    best_size = float("inf")
    log.info(f"PDF → ≤{target_bytes / (1024*1024):.2f} MB")

    total_qualities = len(range(95, 5, -10))
    quality_idx = 0

    for quality in range(95, 5, -10):
        quality_idx += 1
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
        try:
            reader = PdfReader(input_path)
            writer = PdfWriter()
            total_pages = len(reader.pages)
            processed = 0

            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    page.compress_content_streams()
                    if "/Resources" in page and "/XObject" in page["/Resources"]:
                        xobj_dict = (
                            page["/Resources"]["/XObject"].get_object()
                            if hasattr(page["/Resources"]["/XObject"], "get_object")
                            else page["/Resources"]["/XObject"]
                        )
                        for obj_name in list(xobj_dict.keys()):
                            obj = (
                                xobj_dict[obj_name].get_object()
                                if hasattr(xobj_dict[obj_name], "get_object")
                                else xobj_dict[obj_name]
                            )
                            if obj.get("/Subtype") != "/Image":
                                continue

                            try:
                                data = obj.get_data()
                                if not data:
                                    continue
                                img = Image.open(BytesIO(data))
                                if img.format not in ("JPEG", "PNG", "BMP", "TIFF"):
                                    continue
                                if img.mode not in ("RGB", "L"):
                                    img = img.convert("RGB")

                                buf = BytesIO()
                                img.save(buf, "JPEG", quality=quality, optimize=True)
                                new_data = buf.getvalue()

                                obj._data = new_data
                                obj.update(
                                    {
                                        NameObject("/Filter"): NameObject("/DCTDecode"),
                                        NameObject("/ColorSpace"): NameObject(
                                            "/DeviceRGB"
                                        ),
                                        NameObject("/BitsPerComponent"): NumberObject(
                                            8
                                        ),
                                        NameObject("/Length"): NumberObject(
                                            len(new_data)
                                        ),
                                    }
                                )
                            except Exception:
                                pass  # Keep original

                    writer.add_page(page)
                    processed += 1
                    progress = 20 + (
                        70
                        * (quality_idx - 1 + processed / total_pages)
                        / total_qualities
                    )
                    update_callback(
                        int(progress), f"Q{quality} | P{page_num}/{total_pages}"
                    )

                except Exception as e:
                    log.error(f"Page {page_num} error: {e}")
                    writer.add_page(page)

            with open(temp, "wb") as f:
                writer.write(f)

            size = os.path.getsize(temp)
            log.info(f"Quality {quality}: {size / (1024*1024):.2f} MB")

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
            log.error(f"Quality {quality} failed: {e}")
            if os.path.exists(temp):
                os.unlink(temp)

    if best_file:
        shutil.move(best_file, output_path)
        update_callback(100, "Best!")
        return True, best_size

    update_callback(100, "No change")
    return False, os.path.getsize(input_path)
