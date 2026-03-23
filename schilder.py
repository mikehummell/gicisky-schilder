import asyncio
import csv
from PIL import Image, ImageDraw, ImageFont
from bleak import BleakClient, BleakScanner
import struct

LOGO_PFAD = "einhorn.png"  # Immer dasselbe Logo für alle Schilder

SCAN_TIMEOUT = 30
CONNECT_TIMEOUT = 30
CHAR_CONTROL = "0000fef1-0000-1000-8000-00805f9b34fb"
CHAR_DATA    = "0000fef2-0000-1000-8000-00805f9b34fb"

# def erstelle_bild(text: str) -> Image.Image:
#     """Erstellt ein 250x132 Bild mit dem gegebenen Text"""
#     img = Image.new("RGB", (250, 132), color="white")
#     draw = ImageDraw.Draw(img)
    
#     try:
#         font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 48)
#     except:
#         font = ImageFont.load_default()
    
#     # Text zentrieren
#     bbox = draw.textbbox((0, 0), text, font=font)
#     text_width  = bbox[2] - bbox[0]
#     text_height = bbox[3] - bbox[1]
#     x = (250 - text_width) // 2
#     y = (132 - text_height) // 2
    
#     draw.text((x, y), text, fill="black", font=font)
#     return img
def erstelle_bild(text: str, subtext: str = "", logo_pfad: str = "") -> Image.Image:
    """Erstellt ein 250x132 Bild mit Logo links und Text rechts"""
    img = Image.new("RGB", (250, 132), color="white")
    draw = ImageDraw.Draw(img)

    # --- Logo ---
    logo_breite = 0
    if logo_pfad:
        try:
            #logo = Image.open(logo_pfad).convert("RGB")
            # Neu:
            logo_raw = Image.open(logo_pfad)
            # Falls Transparenz vorhanden (RGBA oder P), auf weissem Hintergrund zusammenführen
            if logo_raw.mode in ("RGBA", "P", "LA"):
                hintergrund = Image.new("RGB", logo_raw.size, "white")
                if logo_raw.mode == "P":
                    logo_raw = logo_raw.convert("RGBA")
                hintergrund.paste(logo_raw, mask=logo_raw.split()[-1])  # Alpha als Maske
                logo = hintergrund
            else:
                logo = logo_raw.convert("RGB")
            # Logo auf max 90x90 skalieren, Seitenverhältnis beibehalten
            logo.thumbnail((90, 90))
            # Logo vertikal zentrieren
            logo_y = (132 - logo.height) // 2
            img.paste(logo, (5, logo_y))
            logo_breite = logo.width + 10  # 5px Abstand links + Logo + 5px Abstand rechts
        except Exception as e:
            print(f"  ⚠ Logo konnte nicht geladen werden: {e}")

    # --- Text ---
    text_x = logo_breite + 5
    text_bereich_breite = 250 - text_x - 5

    try:
        font_gross = ImageFont.truetype("C:\\Windows\\Fonts\\gigi.ttf", 48)
        font_klein = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 20)
    except:
        font_gross = ImageFont.load_default()
        font_klein = ImageFont.load_default()

    # Haupttext zentrieren im rechten Bereich
    if subtext:
        # Mit Subtext: Haupttext etwas höher
        bbox = draw.textbbox((0, 0), text, font=font_gross)
        text_h = bbox[3] - bbox[1]
        bbox2 = draw.textbbox((0, 0), subtext, font=font_klein)
        sub_h = bbox2[3] - bbox2[1]
        abstand = 8

        gesamt_h = text_h + abstand + sub_h
        start_y = (132 - gesamt_h) // 2

        # Haupttext horizontal zentrieren
        bbox = draw.textbbox((0, 0), text, font=font_gross)
        tw = bbox[2] - bbox[0]
        x = text_x + (text_bereich_breite - tw) // 2
        draw.text((x, start_y), text, fill="black", font=font_gross)

        # Subtext horizontal zentrieren
        bbox2 = draw.textbbox((0, 0), subtext, font=font_klein)
        sw = bbox2[2] - bbox2[0]
        x2 = text_x + (text_bereich_breite - sw) // 2
        draw.text((x2, start_y + text_h + abstand), subtext, fill="black", font=font_klein)

    else:
        # Nur Haupttext, vertikal und horizontal zentrieren
        bbox = draw.textbbox((0, 0), text, font=font_gross)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = text_x + (text_bereich_breite - tw) // 2
        y = (132 - th) // 2
        draw.text((x, y), text, fill="black", font=font_gross)

    return img

def parse_adresse(adresse: str) -> str:
    """Konvertiert 61.62.30.09 → FF:FF:61:62:30:09"""
    if "." in adresse:
        teile = adresse.split(".")
        return f"FF:FF:{teile[0]}:{teile[1]}:{teile[2]}:{teile[3]}"
    return adresse  # bereits im richtigen Format

async def sende_bild(adresse: str, bild: Image.Image):
    """Sendet ein Bild an ein Schild via BLE"""
    from bitmap import Bitmap
    import tempfile, os

    # Bild temporär speichern (Bitmap-Klasse braucht eine Datei)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    bild.save(tmp.name)
    tmp.close()

    try:
        bmp = Bitmap(tmp.name)
        data = bmp.bitmap

        notification_queue = asyncio.Queue(maxsize=1)

        def callback(sender, d):
            asyncio.get_event_loop().call_soon_threadsafe(
                notification_queue.put_nowait, d)

        print(f"  Verbinde mit {adresse}...")
        async with BleakClient(adresse, timeout=CONNECT_TIMEOUT) as client:
            await client.start_notify(CHAR_CONTROL, callback)
            await asyncio.sleep(0.5)

            # Block size anfragen
            await client.write_gatt_char(CHAR_CONTROL, bytes([0x01]), response=False)
            resp = await notification_queue.get()
            block_size = (resp[2] & 0xff) << 8 | (resp[1] & 0xff)

            # Übertragung starten
            cmd = bytes([0x02]) + struct.pack("<I", len(data)) + bytes([0x01])
            await client.write_gatt_char(CHAR_CONTROL, cmd, response=False)
            await notification_queue.get()
            await asyncio.sleep(0.2)

            await client.write_gatt_char(CHAR_CONTROL, bytes([0x03]), response=False)
            await notification_queue.get()

            # Daten senden
            payload_size = block_size - 4
            curr_pos = 0
            block_num = 0
            while curr_pos < len(data) - 1:
                chunk = data[curr_pos:curr_pos + payload_size]
                packet = struct.pack("<I", block_num) + chunk
                await client.write_gatt_char(CHAR_DATA, packet, response=False)
                await asyncio.sleep(0.01)
                curr_pos += len(chunk)
                block_num += 1

            await notification_queue.get()
            print(f"  ✓ Fertig!")

    finally:
        os.unlink(tmp.name)


async def main():
    # CSV einlesen
    schilder = []
    with open("schilder.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            schilder.append(row)

    print(f"{len(schilder)} Schild(er) gefunden in CSV\n")
    print("Drücke jetzt ALLE Knöpfe und warte 3 Sekunden...")
    await asyncio.sleep(3)

    # Alle Schilder gleichzeitig beschriften
    tasks = []
    for schild in schilder:
        adresse = parse_adresse(schild["adresse"])
        text    = schild["text"]
        #logo_pfad = schild["image"]
        print(f"Starte: {adresse} → '{text}'")
        # bild = erstelle_bild(text)

        bild = erstelle_bild(
            text      = schild["text"],
            subtext   = schild.get("subtext", ""),
            #logo_pfad = LOGO_PFAD
            logo_pfad = schild["image"]
        )
        tasks.append(sende_bild(adresse, bild))

    await asyncio.gather(*tasks)
    print("\n✓ Alle Schilder fertig!")

asyncio.run(main())
