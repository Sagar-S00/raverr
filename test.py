from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
from io import BytesIO

TEMPLATE = "glassuiround.png"
OUTPUT = "profile_correct.png"

user = {
    "name": "Krish",
    "id": "74307746",
    "country": "IN",
    "status": "Not in Rave",
    "state": "Not Friends",
    "language": "EN",
    "online": True,
    "avatar": "https://avatars2.prod.hilljam.com/kVpX8K/c68bf782-large.jpeg"
}

img = Image.open(TEMPLATE).convert("RGBA")
draw = ImageDraw.Draw(img)

# ---------------- FONTS ----------------
FONT_NAME = ImageFont.truetype("arialbd.ttf", 52)
FONT_ID = ImageFont.truetype("arial.ttf", 26)
FONT_ROW = ImageFont.truetype("arial.ttf", 30)

# ---------------- AVATAR (PERFECT CIRCLE) ----------------
# Circle center and radius from template
CIRCLE_CENTER_X = 133  # Center of the outer circle
CIRCLE_CENTER_Y = 127
INNER_RADIUS = 75      # Radius of inner circle (half of 150)

# Calculate top-left corner for paste
INNER_SIZE = INNER_RADIUS * 2  # 150px
INNER_X = CIRCLE_CENTER_X - INNER_RADIUS
INNER_Y = CIRCLE_CENTER_Y - INNER_RADIUS

avatar = Image.open(
    BytesIO(requests.get(user["avatar"]).content)
).convert("RGBA").resize((INNER_SIZE, INNER_SIZE), Image.LANCZOS)

# Create perfect circular mask
mask = Image.new("L", (INNER_SIZE, INNER_SIZE), 0)
ImageDraw.Draw(mask).ellipse((0, 0, INNER_SIZE, INNER_SIZE), fill=255)

# Paste avatar centered
img.paste(avatar, (INNER_X, INNER_Y), mask)

# ---------------- TEXT SHADOW FUNCTION ----------------
def text_with_shadow(x, y, text, font):
    draw.text((x+2, y+2), text, font=font, fill=(0,0,0,120))
    draw.text((x, y), text, font=font, fill=(255,255,255,255))

# ---------------- HEADER ----------------
TEXT_X = 255  # Adjusted to align better with "Krish"
TEXT_Y = 60   # Adjusted vertical position

text_with_shadow(TEXT_X, TEXT_Y, user["name"], FONT_NAME)
draw.text((TEXT_X, TEXT_Y + 66), f"ID: {user['id']}",
          font=FONT_ID, fill=(200,200,200,255))

# ---------------- ONLINE DOT ----------------
if user["online"]:
    dot_x = img.width - 115
    dot_y = TEXT_Y + 20
    draw.ellipse((dot_x, dot_y, dot_x+20, dot_y+20), fill=(0,255,118,255))

# ---------------- ROW ALIGNMENT (CENTERED VERTICALLY) ----------------
# More precise divider positions
DIVIDERS = [235, 310, 385, 460, 540]

rows = [
    ("Country", user["country"]),
    ("Status", user["status"]),
    ("State", user["state"]),
    ("Language", user["language"]),
]

LABEL_X = 120
VALUE_X = 520

for i, (label, value) in enumerate(rows):
    # Center text vertically between dividers
    y = (DIVIDERS[i] + DIVIDERS[i+1]) // 2 - 15  # -15 to center 30px font
    draw.text((LABEL_X, y), label, font=FONT_ROW, fill=(255,255,255,255))
    draw.text((VALUE_X, y), value, font=FONT_ROW, fill=(220,220,220,255))

# ---------------- SAVE ----------------
img.save(OUTPUT)
print("✅ PERFECTLY ALIGNED:", OUTPUT)