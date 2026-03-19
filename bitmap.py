import cv2
import numpy as np
from PIL import Image

class Bitmap:
    def __init__(self, filename: str):
        # Mit PIL laden (wie Android Bitmap)
        pil_image = Image.open(filename).convert("RGB")
        self._width = pil_image.width
        self._height = pil_image.height
        self._encoded_bitmap = self._convert(pil_image)

    @property
    def bitmap(self) -> bytes:
        return self._encoded_bitmap

    @property
    def size(self) -> int:
        return len(self._encoded_bitmap)

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def _convert(self, pil_image: Image.Image) -> bytes:
        if pil_image.width != 250 or pil_image.height != 132:
            raise ValueError(f"Bild hat falsche Auflösung (250x132): ({pil_image.width}x{pil_image.height})")

        # Rotation: -90° dann horizontal spiegeln (postScale(-1, 1))
        img = pil_image.rotate(90, expand=True)   # -90° = 90° gegen Uhrzeigersinn... 
        img = img.transpose(Image.FLIP_LEFT_RIGHT) # horizontal spiegeln

        width = img.width    # 132
        height = img.height  # 250

        # Pixel als Array holen
        pixels = list(img.getdata())  # [(r,g,b), ...]

        # Threshold berechnen (Durchschnitt aller Grauwerte)
        gray_values = [((r * 38 + g * 75 + b * 15) >> 7) for r, g, b in pixels]
        threshold = sum(gray_values) // len(gray_values)

        # Ausgabe-Array: width * height / 8 Bytes
        total_pixels = width * height
        bArr = bytearray(total_pixels // 8)

        i3 = 0   # Zeile (springt +2)
        i4 = 0   # Bit-Position im Byte (0-3)
        i5 = 0   # aktuelles Byte (wird aufgebaut)
        i6 = 0   # Byte-Index in bArr

        while i3 < height:
            i7 = i6
            i8 = i4
            for i9 in range(width):
                # Pixel aus Zeile i3
                r, g, b = pixels[i3 * width + i9]
                i11 = 128 if ((r * 38 + g * 75 + b * 15) >> 7) > threshold else 0

                # Pixel aus Zeile i3+1
                r2, g2, b2 = pixels[(i3 + 1) * width + i9]
                i13 = 128 if ((r2 * 38 + g2 * 75 + b2 * 15) >> 7) > threshold else 0

                i14 = i8 * 2
                i5 = i5 | (i11 >> i14) | (i13 >> (i14 + 1))
                i8 += 1

                if i8 == 4:
                    bArr[i7] = i5 & 255
                    i5 = 0
                    i7 += 1
                    i8 = 0

            i3 += 2
            i4 = i8
            i6 = i7

        return bytes(bArr)