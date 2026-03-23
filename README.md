# PICKSMART Elektronische Preisschilder

Python-Script zum Beschriften von PICKSMART E-Ink Preisschildern via Bluetooth (BLE) unter Windows.

## Voraussetzungen

- Windows 10/11 mit Bluetooth
- Python 3.12+
- Folgende Libraries:

```
pip install bleak pillow opencv-python
```

## Projektstruktur

| Datei | Beschreibung |
|---|---|
| `schilder.py` | Hauptprogramm — liest CSV und beschriftet alle Schilder parallel |
| `bitmap.py` | Konvertiert PNG-Bilder in das PICKSMART-Displayformat |
| `schilder.csv` | Konfiguration: welches Schild bekommt welchen Text |
| `logo.png` | Logo das auf allen Schildern links angezeigt wird |
| `scan.py` | Hilfstool: findet BLE-Geräte in der Nähe |
| `explore.py` | Hilfstool: zeigt BLE Services eines Geräts |

## Konfiguration

### schilder.csv

```csv
adresse,text,subtext
61.62.30.09,HALLO,willkommen
61.62.30.10,TSCHÜSS,auf wiedersehen
```

**Spalten:**

- `adresse` — Die letzten 4 Bytes der Geräte-ID, mit Punkten getrennt (steht auf dem Gerät)
- `text` — Haupttext (gross, max. ca. 6 Zeichen)
- `subtext` — Kleintext unterhalb (optional, kann leer gelassen werden)

### Logo

Das Logo wird in `schilder.py` oben als Konstante definiert:

```python
LOGO_PFAD = "einhorn.png"  # Pfad zum Logo
```

Das Logo wird automatisch auf max. 90×90 Pixel skaliert und links auf dem Schild platziert. PNG mit Transparenz (RGBA) wird unterstützt.

## Verwendung

### 1. Schilder in CSV eintragen

Öffne `schilder.csv` und trage die Geräte-IDs und Texte ein. Die Geräte-ID steht auf der Rückseite des Schildes (z.B. `61623009` → `61.62.30.09`).

### 2. Script starten

```
py schilder.py
```

### 3. Knöpfe drücken

Das Script wartet 3 Sekunden — drücke in dieser Zeit den Knopf auf der Rückseite **aller** Schilder um sie aufzuwecken.

Die Übertragung läuft dann **parallel** für alle Schilder gleichzeitig.

## Display-Layout

```
+---------------------------+
|        |                  |
|  LOGO  |   HAUPTTEXT      |
|        |   kleintext      |
+---------------------------+
```

- Display-Auflösung: 250×132 Pixel, schwarz/weiss
- Haupttext: Arial 48pt
- Subtext: Arial 22pt

## Geräte-ID herausfinden

Falls die ID nicht lesbar ist, kann `scan.py` helfen:

```
py scan.py
```

Es werden alle BLE-Geräte in der Nähe aufgelistet. PICKSMART-Schilder erscheinen als `NEMR` gefolgt von der ID (z.B. `NEMR61623009`).

## Technische Details

Die Schilder kommunizieren über BLE mit folgenden Characteristics:

| UUID | Funktion |
|---|---|
| `0000fef1-...` | Steuerkanal (Start/Stop Übertragung) |
| `0000fef2-...` | Datenkanal (Bilddaten blockweise) |
| `0000fef3-...` | Gerätekonfiguration (lesbar) |

Das Bildformat ist ein proprietäres 2-Bit-pro-Pixel Format: je zwei übereinanderliegende Pixel werden zu einem Bit-Paar kombiniert, 4 Pixel-Paare ergeben ein Byte.
