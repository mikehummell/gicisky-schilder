from PIL import Image
from PIL import ImageDraw

# Komplett rot AUSSER einem weissen Streifen ganz links (5px)
bild      = Image.new("RGB", (250, 132), color="white")
rot_maske = Image.new("RGB", (250, 132), color="black")

# Weissen Streifen links in der Rotmaske setzen

draw = ImageDraw.Draw(rot_maske)
draw.rectangle([100, 0, 249, 131], fill="white")  # nur rechts rot

bild.save("test.png")
rot_maske.save("test_rot.png")