import cv2
import numpy as np
from bitmap import Bitmap

# Original bitmap laden wie updater.py es macht
bmp = Bitmap('test.png')
data = bmp.bitmap

print(f"Totale Bytes: {len(data)}")
print(f"Erste 32 Bytes (hex): {[hex(b) for b in data[:32]]}")
print(f"Bytes 4000-4032 (hex, zweiter Kanal): {[hex(b) for b in data[4000:4032]]}")

# Zurückrechnen: wie viele Pixel pro Zeile geht das Script von aus?
# test.png ist 250x122
print(f"\nRechnung:")
print(f"250 × 122 = {250*122} Pixel")
print(f"Aufgefüllt: {(122+7)&(-8)} Höhe → 250 × {(122+7)&(-8)} = {250*((122+7)&(-8))} Pixel")
print(f"/ 8 Bit = {250*((122+7)&(-8))//8} Bytes pro Kanal")
print(f"× 2 Kanäle = {250*((122+7)&(-8))//8*2} Bytes total")