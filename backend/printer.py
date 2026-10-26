import logging
import os
import socket
from pathlib import Path

from brother_ql.backends.helpers import send
from brother_ql.conversion import convert
from brother_ql.labels import FormFactor, LabelsManager
from brother_ql.raster import BrotherQLRaster
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageOps

load_dotenv()

MFC_IP = os.getenv("MFC_IP", default="192.168.88.21")
QL710_IP = os.getenv("QL710_IP", default="192.168.88.13")
QL1110_IP = os.getenv("QL1110_IP", default="")
# Margin around die-cut labels in dots (300 dpi, 36 dots ~ 3mm)
DIE_CUT_MARGIN = int(os.getenv("DIE_CUT_MARGIN", default="36"))


class BrotherMFC:
    def __init__(self, printer: str):
        self.printer = printer

    def print(self, pdf: bytes):
        try:
            # Port 9100 is the industry standard for raw printing (JetDirect)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.printer, 9100))
                s.sendall(pdf)
                logging.info("PDF successfully streamed to printer!")
        except Exception as e:
            logging.error(f"Network printing failed: {e}")


class BrotherQL:
    def __init__(
        self,
        model: str = "QL-710W",
        ip: str = QL710_IP,
        label_size: str = "38",
        rotate: str = "90",
    ):
        self.model = model
        self.ip = ip
        self.label_size = label_size
        self.rotate = rotate

    def _fit(self, image: Image.Image) -> Image.Image:
        """Crop white borders and, for die-cut labels, scale and pad the image
        to exactly the printable area (brother_ql rejects other sizes)"""
        if bbox := ImageOps.invert(image.convert("L")).getbbox():
            image = image.crop(bbox)
        label = LabelsManager().get_label_by_identifier(self.label_size)
        if label.form_factor not in (FormFactor.DIE_CUT, FormFactor.ROUND_DIE_CUT):
            return image
        width, height = label.dots_printable
        if (image.width > image.height) != (width > height):
            image = image.rotate(90, expand=True)
        # Keep a margin, the printer doesn't hit the die-cut label exactly
        margin = DIE_CUT_MARGIN
        image = ImageOps.contain(image, (width - 2 * margin, height - 2 * margin))
        canvas = Image.new("RGB", (width, height), "white")
        canvas.paste(image, ((width - image.width) // 2, (height - image.height) // 2))
        return canvas

    def print_label(
        self,
        path: Path,
    ):
        image = self._fit(Image.open(path).convert("RGB"))

        qlr = BrotherQLRaster(self.model)
        qlr.exception_on_warning = True

        instructions = convert(
            qlr=qlr, images=[image], label=self.label_size, rotate=self.rotate
        )

        status = send(
            instructions=instructions,
            printer_identifier=f"tcp://{self.ip}",
            backend_identifier="network",
        )

        logging.info(status)

        if status["outcome"] == "sent":
            logging.info(f"Successfully printed {path}")
            return True
        logging.error(f"Print for label {path} failed")
        return False


def print_shipping_label(path: Path, printer: str) -> bool:
    if printer == "ql1110":
        # DHL Warenpost on DK-11247 (103x164 die-cut)
        ql = BrotherQL("QL-1110NWB", QL1110_IP, "103x164", rotate="0")
    else:
        # Internetmarke on 38mm endless
        ql = BrotherQL("QL-710W", QL710_IP, "38", rotate="90")
    return ql.print_label(path)


def debug_label(path: Path, printer: str, lines: list[str]):
    """Placeholder label for dry runs, so it can't be mistaken for a real one"""
    size = (1200, 1822) if printer == "ql1110" else (1500, 413)
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline="black", width=12)
    font = ImageFont.load_default(size=54 if printer == "ql1110" else 72)
    draw.multiline_text(
        (40, 30), "\n".join(["DEBUG - NOT A LABEL", *lines]), fill="black", font=font
    )
    image.save(path)
