from pathlib import Path

from brother_ql.backends.helpers import send
from brother_ql.conversion import convert
from brother_ql.raster import BrotherQLRaster
from PIL import Image


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

        print(status)

        if status["outcome"] == "sent":
            print(f"Successfully printed {path}")
            return True
        return False
