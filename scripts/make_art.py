"""Draws the pictures on the README pages: the cover, the section headings and the install steps in Spanish and
English, the social preview GitHub shows when someone shares the link, and the framed screenshots.

Everything is drawn from Pawdori's own art and fonts (Baloo 2 for titles, Nunito Sans for text), read from a checkout
of the game. The screenshots come from the game's proof simulation at 2x, one folder per language:

    python3 -I scripts/make_art.py --source /path/to/Pawdori --shots /path/to/shots

`--shots` holds `es/` and `en/`, each with desktop.png and the phone captures named in SHOTS. Text is dark ink on
cream, checked against WCAG's enhanced contrast (7:1) before a picture is written.
"""
import argparse
import base64
import io
import os
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")

# CSS pixels; pictures are drawn at twice that for sharp text on high-density screens.
WIDTH = 880
SCALE = 2
RADIUS = 22
CONTRAST = 7.0
PREVIEW = (1280, 640)

# Pawdori's design tokens (client/web/src/styles/tokens.css).
INK = (37, 18, 11)
INK_SOFT = (71, 50, 60)
INK_MUTED = (106, 90, 82)
CREAM = (255, 250, 242)
CREAM_DEEP = (255, 241, 220)
HONEY = (251, 185, 63)
HONEY_LIGHT = (254, 211, 113)
CORAL = (255, 101, 77)
CORAL_DARK = (138, 32, 25)
LAVENDER = (141, 127, 214)
LAVENDER_LIGHT = (233, 228, 255)
WHITE = (255, 255, 255)

PETS = ["mochi_bun", "nori_fox", "honey_hamster", "puddin_cat", "bubble_axolotl", "starlight_dragon", "cloud_sheep",
        "maple_bear", "pebble_penguin", "taro_panda", "sprout_frog", "cocoa_otter", "biscuit_pup", "pepper_pup"]

# Each section: its title and the line under it, in Spanish and English.
HEADINGS = {
    "overview": (("¿Qué es Pawdori?", "Una mascota virtual para cuidar en familia"),
                 ("What is Pawdori", "A cozy virtual pet you raise with the people you love")),
    "showcase": (("Así se ve", "Inicio, minijuegos, tienda, ropa, familia y más"),
                 ("Showcase", "Home, mini games, the shop, outfits, family and more")),
    "features": (("Qué hay adentro", "Todo lo que puedes hacer con tu mascota"),
                 ("Features", "Everything you can do with your pet")),
    "requirements": (("Requisitos", "Lo que necesita tu teléfono"),
                     ("Requirements", "What your phone needs")),
    "installation": (("Instalación", "Del enlace a tu mascota en cuatro pasos"),
                     ("Installation", "From the link to your pet in four steps")),
    "updating": (("Actualizaciones", "Pawdori se actualiza solita"),
                 ("Updates", "Pawdori updates itself")),
    "security": (("Seguridad", "Firmado, verificado y con tu progreso en el servidor"),
                 ("Security", "Signed, verified, and your progress lives on the server")),
    "releases": (("Versiones", "Qué trae cada versión"),
                 ("Releases", "What each version brings")),
    "faq": (("Preguntas frecuentes", "Lo que la gente pregunta"),
            ("FAQ", "Questions people ask")),
    "repository": (("Este repositorio", "Qué guarda y cómo se arma esta página"),
                   ("This repository", "What it holds and how this page is made")),
    "credits": (("Créditos", "Quién lo hace y de quién es"),
                ("Credits", "Who makes it and who owns it")),
}

COVER = (("Una mascota virtual para cuidar", "en familia y jugar con amigos", "Hecho por xt0n1"),
         ("A cozy virtual pet to raise", "with family and play with friends", "Developed by xt0n1"))

STEPS = (
    [("Abre la última versión", "Desde tu teléfono, en la página de Releases de este repositorio."),
     ("Descarga el APK", "Toca pawdori-<versión>.apk: pesa unos 28 MB."),
     ("Permite instalarlo", "Android pide permiso para esta fuente: acéptalo solo para Pawdori."),
     ("Adopta tu mascota", "Abre Pawdori, crea tu cuenta y elige a tu nuevo mejor amigo.")],
    [("Open the latest release", "From your phone, on this repository's Releases page."),
     ("Download the APK", "Tap pawdori-<version>.apk: it is about 28 MB."),
     ("Allow the install", "Android asks to trust this source: allow it for Pawdori only."),
     ("Adopt your pet", "Open Pawdori, create your account and pick your new best friend.")],
)

# Phone captures, in the order the showcase shows them.
SHOTS = ["home", "pets", "daily-gift", "games", "bubble-pop", "shop", "wardrobe", "family", "sign-in"]


def font(path, size, weight):
    face = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    axes = face.get_variation_axes()
    face.set_variation_by_axes([weight] + [axis["default"] for axis in axes[1:]])
    return face


class Fonts:
    def __init__(self, source):
        self.display = os.path.join(source, "content/fonts/Baloo2-Variable.ttf")
        self.body = os.path.join(source, "content/fonts/NunitoSans-Variable.ttf")

    def title(self, size, weight=800):
        return font(self.display, size * SCALE, weight)

    def text(self, size, weight=600):
        return font(self.body, size * SCALE, weight)


def luminance(rgb):
    def linear(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (linear(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(image, box, colour):
    """`colour`'s contrast against the darkest 2 % of `box`, the part that limits dark text's legibility."""
    pixels = sorted(luminance(p) for p in image.convert("RGB").crop(tuple(map(int, box))).resize((64, 16)).get_flattened_data())
    dark = pixels[int(len(pixels) * 0.02)]
    text = luminance(colour)
    return (max(dark, text) + 0.05) / (min(dark, text) + 0.05)


def require(value, name):
    if value < CONTRAST:
        raise SystemExit(f"{name}: text contrast {value:.1f}:1 is under {CONTRAST}:1")
    print(f"  {name}: contrast {value:.1f}:1")


def pet(source, species, height):
    image = Image.open(os.path.join(source, f"client/web/public/pets/pet_{species}_hero.webp")).convert("RGBA")
    image = image.crop(image.getbbox())
    return image.resize((round(image.width * height / image.height), height), Image.LANCZOS)


def ground_shadow(size, box, strength=70):
    """A soft oval shadow under a sitting pet, like the game's room."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse(box, fill=INK + (strength,))
    return layer.filter(ImageFilter.GaussianBlur(6 * SCALE))


def dots(image, colour, step, radius, offset=0):
    draw = ImageDraw.Draw(image)
    for row, y in enumerate(range(-step, image.height + step, step)):
        shift = (step // 2 if row % 2 else 0) + offset
        for x in range(-step + shift, image.width + step, step):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=colour)


def gradient(size, left, right):
    width, height = size
    strip = Image.new("RGB", (width, 1))
    for x in range(width):
        t = x / max(1, width - 1)
        strip.putpixel((x, 0), tuple(round(a + (b - a) * t) for a, b in zip(left, right)))
    return strip.resize(size)


def svg(image, alt, outline=True):
    """`image` (2x) as an SVG with rounded corners and the game's ink outline."""
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, "JPEG", quality=90, optimize=True, progressive=True)
    data = base64.b64encode(buffer.getvalue()).decode()
    width, height = image.width // SCALE, image.height // SCALE
    label = escape(alt, {'"': "&quot;"})
    stroke = (f'<rect x="1.5" y="1.5" width="{width - 3}" height="{height - 3}" rx="{RADIUS - 1.5}" fill="none" '
              f'stroke="#25120b" stroke-width="3"/>\n') if outline else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="{label}">\n<title>{label}</title>\n'
            f'<defs><clipPath id="r"><rect width="{width}" height="{height}" rx="{RADIUS}"/></clipPath></defs>\n'
            f'<image width="{width}" height="{height}" href="data:image/jpeg;base64,{data}" clip-path="url(#r)"/>\n'
            f'{stroke}</svg>\n')


def write(path, content):
    path = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"{os.path.relpath(path, ROOT)}: {len(content) // 1024} KB")


def centred(draw, text, face, centre_x, y, fill):
    left, _, right, _ = draw.textbbox((0, 0), text, font=face)
    draw.text((centre_x - (right - left) / 2 - left, y), text, font=face, fill=fill)


def heading(fonts, source, title, line, index):
    """A section heading: a cream card with lavender dots, the title and its line, and two pets at the sides."""
    size = (WIDTH * SCALE, 128 * SCALE)
    image = gradient(size, LAVENDER_LIGHT, CREAM_DEEP).convert("RGBA")
    dots(image, WHITE + (255,), 28 * SCALE, 3 * SCALE)
    # A honey floor along the bottom, as in the pet's room.
    floor = 22 * SCALE
    ImageDraw.Draw(image).rectangle((0, size[1] - floor, size[0], size[1]), fill=HONEY_LIGHT)
    ImageDraw.Draw(image).line((0, size[1] - floor, size[0], size[1] - floor), fill=INK, width=SCALE * 2)
    left_pet = pet(source, PETS[index % len(PETS)], 96 * SCALE)
    right_pet = pet(source, PETS[(index + 7) % len(PETS)], 96 * SCALE).transpose(Image.FLIP_LEFT_RIGHT)
    base = size[1] - 10 * SCALE
    for sprite, x in ((left_pet, 34 * SCALE), (right_pet, size[0] - 34 * SCALE - right_pet.width)):
        image.alpha_composite(ground_shadow(size, (x + 8 * SCALE, base - 8 * SCALE, x + sprite.width - 8 * SCALE,
                                                   base + 4 * SCALE)))
        image.alpha_composite(sprite, (x, base - sprite.height))
    draw = ImageDraw.Draw(image)
    big, small = fonts.title(44), fonts.text(17, 650)
    title_box = draw.textbbox((0, 0), title, font=big)
    line_box = draw.textbbox((0, 0), line, font=small)
    block = (title_box[3] - title_box[1]) + 12 * SCALE + (line_box[3] - line_box[1])
    top = (size[1] - floor - block) / 2
    title_y = top - title_box[1]
    line_y = top + (title_box[3] - title_box[1]) + 12 * SCALE - line_box[1]
    text_area = (size[0] / 2 - max(title_box[2], line_box[2]) / 2, top, size[0] / 2 + max(title_box[2], line_box[2]) / 2,
                 top + block)
    worst = min(contrast(image, text_area, INK), contrast(image, text_area, INK_SOFT))
    centred(draw, title, big, size[0] / 2, title_y, INK)
    centred(draw, line, small, size[0] / 2, line_y, INK_SOFT)
    return image, worst


def keyart(source):
    return Image.open(os.path.join(source, "client/web/public/art/auth/auth-keyart-wide-1200.webp")).convert("RGBA")


def mark(source, height):
    image = Image.open(os.path.join(source, "client/web/public/art/brand/pawdori-mark.webp")).convert("RGBA")
    image = image.crop(image.getbbox())
    return image.resize((round(image.width * height / image.height), height), Image.LANCZOS)


def scene(source, size, art_left, columns):
    """The meadow key art from `art_left` to the right edge, fading into cream on the left where the words go.
    `columns` is the part of the key art's width to show (fractions), so the pets stay whole."""
    art = keyart(source)
    art = art.crop((round(art.width * columns[0]), 0, round(art.width * columns[1]), art.height))
    width = size[0] - art_left
    scale = max(width / art.width, size[1] / art.height)
    art = art.resize((round(art.width * scale), round(art.height * scale)), Image.LANCZOS)
    art = art.crop(((art.width - width) // 2, art.height - size[1], (art.width - width) // 2 + width, art.height))
    image = Image.new("RGBA", size, CREAM + (255,))
    image.alpha_composite(art, (art_left, 0))
    fade = Image.new("L", size, 0)
    fade_draw = ImageDraw.Draw(fade)
    start, end = art_left, art_left + 110 * SCALE
    for x in range(size[0]):
        t = 255 if x < start else max(0, round(255 * (1 - (x - start) / (end - start)))) if x < end else 0
        fade_draw.line((x, 0, x, size[1]), fill=t)
    cream = Image.new("RGBA", size, CREAM + (255,))
    dots(cream, CREAM_DEEP + (255,), 30 * SCALE, 3 * SCALE)
    return Image.composite(cream, image, fade)


def cover(fonts, source, lines):
    size = (WIDTH * SCALE, 380 * SCALE)
    image = scene(source, size, 440 * SCALE, (0.18, 0.82))
    x = 48 * SCALE
    logo = mark(source, 80 * SCALE)
    image.alpha_composite(logo, (x, 64 * SCALE))
    draw = ImageDraw.Draw(image)
    name = fonts.title(80)
    name_box = draw.textbbox((0, 0), "Pawdori", font=name)
    name_x = x + logo.width + 14 * SCALE
    name_y = 64 * SCALE + logo.height / 2 - (name_box[1] + name_box[3]) / 2
    draw.text((name_x, name_y), "Pawdori", font=name, fill=INK)
    tagline, credit = fonts.text(22, 700), fonts.text(16, 800)
    y = 190 * SCALE
    rows = [(lines[0], tagline, INK, 6), (lines[1], tagline, INK_SOFT, 24), (lines[2], credit, CORAL_DARK, 0)]
    boxes = []
    for text, face, colour, gap in rows:
        box = draw.textbbox((x, y), text, font=face)
        boxes.append((box, text, face, colour))
        y = box[3] + gap * SCALE
    area = (x, boxes[0][0][1], max(b[0][2] for b in boxes), boxes[-1][0][3])
    worst = min(contrast(image, area, colour) for *_, colour in boxes)
    for box, text, face, colour in boxes:
        draw.text((x, box[1] - (draw.textbbox((0, 0), text, font=face)[1])), text, font=face, fill=colour)
    return image, worst


def steps(fonts, source, rows):
    """The four install steps down a dotted path of paw prints, each named beside its number."""
    size = (WIDTH * SCALE, 430 * SCALE)
    image = gradient(size, CREAM, CREAM_DEEP).convert("RGBA")
    dots(image, WHITE + (255,), 30 * SCALE, 3 * SCALE)
    draw = ImageDraw.Draw(image)
    top, gap = 70, 96
    centres = [(96 * SCALE, (top + i * gap) * SCALE) for i in range(len(rows))]
    for (ax, ay), (bx, by) in zip(centres, centres[1:]):
        for t in range(1, 6):
            y = ay + (by - ay) * t / 6
            draw.ellipse((ax - 4 * SCALE, y - 4 * SCALE, ax + 4 * SCALE, y + 4 * SCALE), fill=HONEY)
    number, title, body = fonts.title(26), fonts.title(24, 700), fonts.text(16, 600)
    radius = 28 * SCALE
    text_x = 150 * SCALE
    worst = 99.0
    for index, ((cx, cy), (name, line)) in enumerate(zip(centres, rows), start=1):
        draw.ellipse((cx - radius + 3 * SCALE, cy - radius + 5 * SCALE, cx + radius + 3 * SCALE, cy + radius + 5 * SCALE),
                     fill=(201, 128, 26))
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=HONEY, outline=INK, width=3 * SCALE)
        left, upper, right, lower = draw.textbbox((0, 0), str(index), font=number)
        draw.text((cx - (right - left) / 2 - left, cy - (lower - upper) / 2 - upper), str(index), font=number, fill=INK)
        area = (text_x, cy - 34 * SCALE, size[0] - 40 * SCALE, cy + 30 * SCALE)
        worst = min(worst, contrast(image, area, INK_SOFT))
        draw.text((text_x, cy - 4 * SCALE), name, font=title, fill=INK, anchor="ls")
        draw.text((text_x, cy + 22 * SCALE), line, font=body, fill=INK_SOFT, anchor="ls")
    mochi = pet(source, "mochi_bun", 150 * SCALE).transpose(Image.FLIP_LEFT_RIGHT)
    x, base = size[0] - mochi.width - 40 * SCALE, size[1] - 26 * SCALE
    image.alpha_composite(ground_shadow(size, (x + 10 * SCALE, base - 10 * SCALE, x + mochi.width - 10 * SCALE,
                                               base + 6 * SCALE)))
    image.alpha_composite(mochi, (x, base - mochi.height))
    return image, worst


def rounded(image, radius, outline):
    """`image` with transparent rounded corners and an ink outline `outline` pixels wide."""
    image = image.convert("RGBA")
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius, fill=255)
    image.putalpha(mask)
    ImageDraw.Draw(image).rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius, outline=INK,
                                            width=outline)
    return image


def save_webp(image, path, quality=88):
    path = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, "WEBP", quality=quality, method=6)
    print(f"{os.path.relpath(path, ROOT)}: {image.size[0]}x{image.size[1]}, {os.path.getsize(path) // 1024} KB")


def screenshots(shots):
    for language in ("es", "en"):
        desktop = Image.open(os.path.join(shots, language, "desktop.png")).resize((1920, 1200), Image.LANCZOS)
        save_webp(rounded(desktop, 28, 4), f"screenshots/{language}/desktop.webp")
        for name in SHOTS:
            phone = Image.open(os.path.join(shots, language, f"{name}.png"))
            phone = phone.resize((600, round(phone.height * 600 / phone.width)), Image.LANCZOS)
            save_webp(rounded(phone, 44, 4), f"screenshots/{language}/{name}.webp")


def social_preview(fonts, source, shots):
    """The picture of a shared link: the name and what it is on the left, the game on a phone on the right.
    GitHub asks for 1280x640 under 1 MB; it is drawn at twice that and scaled down."""
    size = (PREVIEW[0] * SCALE, PREVIEW[1] * SCALE)
    image = scene(source, size, 700 * SCALE, (0.2, 0.8))
    phone = Image.open(os.path.join(shots, "en", "home.png")).convert("RGBA")
    height = 560 * SCALE
    phone = phone.resize((round(phone.width * height / phone.height), height), Image.LANCZOS)
    phone = rounded(phone, 40 * SCALE, 5 * SCALE)
    x, y = size[0] - phone.width - 90 * SCALE, (size[1] - phone.height) // 2
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x + 10 * SCALE, y + 18 * SCALE, x + phone.width + 10 * SCALE,
                                              y + phone.height + 18 * SCALE), 40 * SCALE, fill=INK + (90,))
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18 * SCALE)))
    image.alpha_composite(phone, (x, y))
    text_x = 70 * SCALE
    logo = mark(source, 120 * SCALE)
    image.alpha_composite(logo, (text_x, 120 * SCALE))
    draw = ImageDraw.Draw(image)
    name = fonts.title(120)
    box = draw.textbbox((0, 0), "Pawdori", font=name)
    draw.text((text_x + logo.width + 20 * SCALE, 120 * SCALE + logo.height / 2 - (box[1] + box[3]) / 2), "Pawdori",
              font=name, fill=INK)
    rows = [("A cozy virtual pet to raise", fonts.text(36, 750), INK, 8),
            ("with family and play with friends", fonts.text(36, 750), INK_SOFT, 30),
            ("Android  ·  Español / English", fonts.text(26, 800), CORAL_DARK, 0)]
    y = 300 * SCALE
    placed = []
    for text, face, colour, gap in rows:
        b = draw.textbbox((text_x, y), text, font=face)
        placed.append((text, face, colour, y))
        y = b[3] + gap * SCALE
    area = (text_x, 300 * SCALE, text_x + 600 * SCALE, y)
    worst = min(contrast(image, area, colour) for _, _, colour, _ in placed)
    for text, face, colour, top in placed:
        draw.text((text_x, top), text, font=face, fill=colour)
    result = image.convert("RGB").resize(PREVIEW, Image.LANCZOS)
    buffer = io.BytesIO()
    result.save(buffer, "JPEG", quality=90, optimize=True, progressive=True)
    if buffer.tell() >= 1_000_000:
        raise SystemExit(f"social-preview.jpg is {buffer.tell()} bytes; GitHub takes under 1 MB")
    require(worst, "social-preview.jpg")
    with open(os.path.join(OUT, "readme/social-preview.jpg"), "wb") as f:
        f.write(buffer.getvalue())
    print(f"assets/readme/social-preview.jpg: {buffer.tell() // 1024} KB")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="a checkout of the Pawdori game")
    parser.add_argument("--shots", required=True, help="the proof captures, with es/ and en/ folders")
    arguments = parser.parse_args()
    fonts = Fonts(arguments.source)
    for language, index in (("es", 0), ("en", 1)):
        image, worst = cover(fonts, arguments.source, COVER[index])
        require(worst, f"{language}/cover.svg")
        alt = f"Pawdori: {COVER[index][0]} {COVER[index][1]}. {COVER[index][2]}."
        write(f"readme/{language}/cover.svg", svg(image, alt))
        for number, (name, words) in enumerate(HEADINGS.items()):
            title, line = words[index]
            image, worst = heading(fonts, arguments.source, title, line, number)
            require(worst, f"{language}/heading-{name}.svg")
            write(f"readme/{language}/heading-{name}.svg", svg(image, f"{title}: {line}"))
        image, worst = steps(fonts, arguments.source, STEPS[index])
        require(worst, f"{language}/install-steps.svg")
        alt = "; ".join(f"{i}. {name}: {line}" for i, (name, line) in enumerate(STEPS[index], 1))
        write(f"readme/{language}/install-steps.svg", svg(image, alt))
    social_preview(fonts, arguments.source, arguments.shots)
    screenshots(arguments.shots)


if __name__ == "__main__":
    main()
