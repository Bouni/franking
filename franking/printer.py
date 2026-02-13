from pathlib import Path

from brother_ql.backends.helpers import send
from brother_ql.brother_ql_create import convert
from brother_ql.raster import BrotherQLRaster
from PIL import Image


class BrotherQL:
    def __init__(
        self,
        model: str = "QL-710W",
        ip: str = "192.168.88.13",
        port: str = "9100",
        label_size: str = "38",
    ):
        self.model = model
        self.ip = ip
        self.port = port
        self.label_size = label_size

    def print_label(
        self,
        path: Path,
        threshold: int = 70,
        dither: bool = False,
        compress: bool = False,
    ):
        img = Image.open(path)
        qlr = BrotherQLRaster(self.model)
        instructions = convert(
            qlr=qlr,
            images=[img],
            label=self.label_size,
            rotate="90",
            threshold=threshold,
            dither=dither,
            compress=compress,
        )

        status = send(
            instructions=instructions,
            printer_identifier=f"tcp://{self.ip}:{self.port}",
            backend_identifier="network",
            blocking=True,
        )

        if status['did_print'] and status['ready_for_next_job']:
            print(f"Successfully printed {path}")
            return True
        return False
