import logging
import socket
from pathlib import Path

from brother_ql.backends.helpers import send
from brother_ql.conversion import convert
from brother_ql.raster import BrotherQLRaster
from PIL import Image


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
        ip: str = "192.168.88.13",
        label_size: str = "38",
    ):
        self.model = model
        self.ip = ip
        self.label_size = label_size

    def print_label(
        self,
        path: Path,
    ):
        image = Image.open(path).convert("RGB")

        qlr = BrotherQLRaster(self.model)
        qlr.exception_on_warning = True

        instructions = convert(
            qlr=qlr, images=[image], label=self.label_size, rotate="90"
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
