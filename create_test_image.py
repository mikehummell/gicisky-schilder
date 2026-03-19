from PIL import Image, ImageDraw, ImageFont

img = Image.new("RGB", (250, 132), color="white")
draw = ImageDraw.Draw(img)

# Versuche eine grössere Systemschrift
try:
    font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 48)
except:
    font = ImageFont.load_default()

draw.text((10, 30), "SIMONE", fill="black", font=font)

img.save("test.png")
print("test.png erstellt")