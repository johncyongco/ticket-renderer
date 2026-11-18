from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
import json
import re

from PIL import Image, ImageDraw, ImageFont
import ctypes as c

HEADER = Image.open(Path(__file__).with_name("header.png")).convert("RGB").resize((936, 234), Image.Resampling.LANCZOS)
class QrCode(c.Structure):
    _fields_ = [("version", c.c_int), ("width", c.c_int), ("data", c.POINTER(c.c_ubyte))]

qr_library = c.CDLL("libqrencode.so.4")
qr_library.QRcode_encodeString8bit.argtypes = [c.c_char_p, c.c_int, c.c_int]
qr_library.QRcode_encodeString8bit.restype = c.POINTER(QrCode)
qr_library.QRcode_free.argtypes = [c.POINTER(QrCode)]
qr_library.QRcode_free.restype = None

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def render_ticket(name, code):
    image = Image.new("RGB", (1000, 1030), "#0e1010")
    draw = ImageDraw.Draw(image)
    image.paste(HEADER, (32, 32))
    draw.rounded_rectangle((32, 287, 968, 998), radius=20, fill="#191a18", outline="#514437", width=2)

    def label(x, y, text, size, face="Sans", color="#f3e9d8"):
        font = ImageFont.truetype(str(FONT_DIR / f"DejaVu{face}.ttf"), size)
        draw.text((x, y), text, font=font, fill=color, anchor="lt")

    label(68, 326, "REGULAR ADMISSION", 21, "Sans-Bold", "#e4a28f")
    label(68, 397, "November 21, 2026", 52, "Serif")
    label(70, 477, "6:00 PM  ·  AULGA Sports Gym", 27)
    label(70, 520, "Lawa-an II, Talisay City, Cebu", 25, color="#bfb2a1")
    for x in range(52, 950, 21):
        draw.line((x, 590, x + 10, 590), fill="#675748", width=2)
    label(70, 635, "ATTENDEE", 18, "Sans-Bold", "#bfb2a1")
    size = 43
    while size > 19:
        font = ImageFont.truetype(str(FONT_DIR / "DejaVuSerif.ttf"), size)
        if font.getlength(name) <= 548:
            break
        size -= 1
    font = ImageFont.truetype(str(FONT_DIR / "DejaVuSerif.ttf"), size)
    if font.getlength(name) > 548:
        while font.getlength(name + "…") > 548:
            name = name[:-1]
        name = name.rstrip() + "…"
    label(68, 677, name, size, "Serif")
    label(70, 770, "TICKET CODE", 18, "Sans-Bold", "#bfb2a1")
    label(68, 810, code, 31, "SansMono-Bold")
    label(70, 938, "Show this ticket at the entrance.", 22, color="#bfb2a1")
    qr = qr_library.QRcode_encodeString8bit(code.encode("ascii"), 0, 1)
    if not qr:
        raise RuntimeError("Could not encode ticket QR")
    try:
        width = qr.contents.width
        qr_image = Image.new("RGB", (width + 8, width + 8), "white")
        for row in range(width):
            for column in range(width):
                if qr.contents.data[row * width + column] & 1:
                    qr_image.putpixel((column + 4, row + 4), (0, 0, 0))
        qr_image = qr_image.resize((qr_image.width * 8, qr_image.height * 8), Image.Resampling.NEAREST)
    finally:
        qr_library.QRcode_free(qr)
    draw.rounded_rectangle((640, 614, 941, 915), radius=18, fill="white")
    image.paste(qr_image, (790 - qr_image.width // 2, 764 - qr_image.height // 2))
    label(716, 942, "SCAN AT ENTRY", 18, "Sans-Bold", "#bfb2a1")
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/ticket":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 4096:
                raise ValueError("Invalid request length")
            body = json.loads(self.rfile.read(length))
            name = " ".join(body["name"].split())
            code = body["code"]
            if not name or len(name) > 200 or not re.fullmatch(r"UNF-[0-9A-F]{16}", code):
                raise ValueError("Invalid name or code")
        except (ValueError, TypeError, KeyError, AttributeError):
            self.send_error(400, "Expected attendee name and a valid ticket code")
            return
        png = render_ticket(name, code)
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(png)))
        self.send_header("Content-Disposition", f'attachment; filename="{code}.png"')
        self.end_headers()
        self.wfile.write(png)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
