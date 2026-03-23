import cv2
import numpy as np
from PIL import Image

class Bitmap:
    def __init__(self, filename: str, red_mask: Image.Image = None, farbe: str = "BW"):
        """
        farbe: "BW" = schwarz/weiss (250x128 intern)
               "BWR" = schwarz/weiss/rot (250x132 intern)
        """
        pil_image = Image.open(filename).convert("RGB")
        self._width = pil_image.width
        self._height = pil_image.height
        self._encoded_bitmap = self._convert(pil_image, red_mask, farbe)

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

    def _convert(self, pil_image, red_mask=None, farbe="BW") -> bytes:
        if pil_image.width != 250 or pil_image.height != 132:
            raise ValueError(f"Falsche Auflösung: {pil_image.width}x{pil_image.height}")

        img = pil_image.rotate(90, expand=True)
        img = img.transpose(Image.FLIP_LEFT_RIGHT)

        # BW: letzte 4 Zeilen abschneiden → 128 Zeilen → 8000 Bytes
        # BWR: alle 132 Zeilen behalten → 132 Zeilen → 8250 Bytes
        if farbe == "BW":
            img = img.crop((0, 0, img.width, 128))
        else:  # BWR — NEU
            img = img.crop((0, 0, img.width, 128))  # NEU

        # Red mask auch transformieren falls vorhanden
        if red_mask:
            red_img = red_mask.rotate(90, expand=True)
            red_img = red_img.transpose(Image.FLIP_LEFT_RIGHT)
            red_img = red_img.crop((0, 0, red_img.width, 128))  # NEU
            red_pixels = list(red_img.convert("L").getdata())
        else:
            red_pixels = None

        width = img.width    # 132
        height = img.height  # 250
        pixels = list(img.getdata())

        # Threshold berechnen
        gray_values = [((r * 38 + g * 75 + b * 15) >> 7) for r, g, b in pixels]
        threshold = sum(gray_values) // len(gray_values)

        # Zwei Ausgabe-Arrays
        total_pixels = width * height
        bArr_schwarz = bytearray(total_pixels // 8)
        bArr_rot     = bytearray(total_pixels // 8)

        def pack_kanal(pixel_werte, bArr, thresh):
            i3 = 0
            i4 = 0
            i5 = 0
            i6 = 0

            while i3 < height:
                i7 = i6
                i8 = i4
                for i9 in range(width):
                    v1 = pixel_werte[i3 * width + i9]
                    i11 = 128 if v1 > thresh else 0
                    v2 = pixel_werte[(i3 + 1) * width + i9]
                    i13 = 128 if v2 > thresh else 0

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

        # Schwarzkanal: dynamischer Threshold
        pack_kanal(gray_values, bArr_schwarz, threshold)

        # Rotkanal: fixer Threshold 128 (Maske ist schwarz/weiss)
        if red_pixels:
            pack_kanal(red_pixels, bArr_rot, 128)
        
        print(f"Schwarzkanal: {len(bArr_schwarz)} Bytes")
        print(f"Rotkanal:     {len(bArr_rot)} Bytes")
        print(f"Total:        {len(bArr_schwarz) + len(bArr_rot)} Bytes")
        return bytes(bArr_schwarz) + bytes(bArr_rot)