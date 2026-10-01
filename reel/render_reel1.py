"""15s 1080x1920 30fps Reel: motion graphics via Pillow -> ffmpeg."""
import math, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 15
BLUE, YELLOW, WHITE = (11, 61, 145), (255, 212, 0), (255, 255, 255)
DEEP = (7, 40, 98)
FONT = sys.argv[1]
MUSIC = sys.argv[2]
OUT = sys.argv[3]
f = lambda s: ImageFont.truetype(FONT, s)

def ease_out(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def ease_back(t):
    t = min(max(t, 0), 1); c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
def clamp01(t): return min(max(t, 0), 1)

def bg(t):
    """Blue gradient with a slow drifting yellow glow."""
    img = Image.new("RGB", (W, H), BLUE)
    d = ImageDraw.Draw(img)
    for y in range(0, H, 8):
        k = y / H
        c = tuple(int(BLUE[i] * (1 - k) + DEEP[i] * k) for i in range(3))
        d.rectangle([0, y, W, y + 8], fill=c)
    cx = W * (0.5 + 0.25 * math.sin(t * 0.6)); cy = H * 0.78
    from PIL import ImageFilter
    glow = Image.new("RGB", (W // 8, H // 8), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r = 380 // 8; gd.ellipse([cx // 8 - r, cy // 8 - r, cx // 8 + r, cy // 8 + r], fill=(46, 38, 0))
    glow = glow.filter(ImageFilter.GaussianBlur(26)).resize((W, H), Image.BICUBIC)
    from PIL import ImageChops
    return ImageChops.add(img, glow)

def text_layer(lines, size, colors, gap=1.12):
    """Centered multi-line text on transparent layer."""
    fnt = f(size); lh = int(size * gap)
    lay = Image.new("RGBA", (W, lh * len(lines) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i, (ln, col) in enumerate(zip(lines, colors)):
        w = d.textlength(ln, font=fnt)
        d.text(((W - w) / 2, i * lh), ln, font=fnt, fill=col)
    return lay

HOOK = text_layer(["Stop texting", "5 people", "to find a court."], 124, [WHITE, YELLOW, WHITE])

def paste_center(base, lay, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        lay = lay.resize((max(1, int(lay.width * scale)), max(1, int(lay.height * scale))), Image.BICUBIC)
    if alpha < 1.0:
        a = lay.getchannel("A").point(lambda p: int(p * alpha)); lay = lay.copy(); lay.putalpha(a)
    base.paste(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)), lay)

def card(label, num, yellow=False, check=False):
    cw, ch = 880, 250
    lay = Image.new("RGBA", (cw + 40, ch + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([26, 36, cw + 26, ch + 36], 48, fill=(0, 0, 0, 70))      # shadow
    d.rounded_rectangle([20, 20, cw + 20, ch + 20], 48, fill=YELLOW if yellow else WHITE)
    bc = BLUE if yellow else YELLOW
    d.ellipse([60, 20 + (ch - 130) / 2, 190, 20 + (ch + 130) / 2], fill=bc)
    cy = 20 + ch / 2
    if check:
        d.line([(92, cy), (118, cy + 28), (162, cy - 28)], fill=YELLOW, width=18, joint="curve")
    else:
        fn = f(76); w = d.textlength(str(num), font=fn)
        d.text((125 - w / 2, cy - 46), str(num), font=fn, fill=BLUE)
    d.text((240, cy - 52), label, font=f(104), fill=BLUE)
    return lay

CARDS = [(3.3, 700, card("Pick time", 1)), (5.3, 990, card("Pick club", 2)), (7.3, 1280, card("Done", 3, True, True))]

CAPS = [(3.3, 5.3, "Pick a time."), (5.3, 7.3, "Pick a club."), (7.3, 10, "Done. Court booked."), (10.3, 15, "Book free.")]

def caption(img, text, a=1.0):
    d = ImageDraw.Draw(img, "RGBA"); fn = f(58)
    w = d.textlength(text, font=fn); x0 = (W - w) / 2
    d.rounded_rectangle([x0 - 36, 1530, x0 + w + 36, 1630], 30, fill=(0, 0, 0, int(150 * a)))
    d.text((x0, 1544), text, font=fn, fill=(255, 255, 255, int(255 * a)))

LOGO = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
_d = ImageDraw.Draw(LOGO)
_d.rounded_rectangle([0, 0, 299, 299], 80, fill=YELLOW)
_d.text((150 - _d.textlength("P", font=f(210)) / 2, 18), "P", font=f(210), fill=BLUE)
CTA = Image.new("RGBA", (760, 190), (0, 0, 0, 0))
_c = ImageDraw.Draw(CTA)
_c.rounded_rectangle([0, 14, 759, 189], 95, fill=(0, 0, 0, 80))
_c.rounded_rectangle([0, 0, 759, 175], 88, fill=YELLOW)
_c.text((380 - _c.textlength("Book free", font=f(100)) / 2, 30), "Book free", font=f(100), fill=BLUE)
SUB = text_layer(["Courts in seconds."], 64, [WHITE])

def frame(i):
    t = i / FPS
    img = bg(t).convert("RGBA")
    # Scene 1: hook, fast zoom-in settle then slow push; exits by ~3.0s
    if t < 3.0:
        z = 1.7 - 0.7 * ease_out(t / 0.45) + 0.06 * t
        a = 1.0 if t < 2.7 else 1 - (t - 2.7) / 0.3
        paste_center(img, HOOK, W / 2, 900, z, clamp01(a) * clamp01(t / 0.12))
    # Scene 2: cards slide in from the right
    if 3.0 <= t < 10.0:
        hd = clamp01((t - 3.0) / 0.4)
        paste_center(img, text_layer(["Book in 3 taps"], 76, [YELLOW]), W / 2, 430, 1.0, hd * (1 if t < 9.7 else (10 - t) / 0.3))
        for st, y, lay in CARDS:
            if t >= st:
                p = ease_back((t - st) / 0.55)
                x = W / 2 + (1 - p) * 1000
                a = clamp01((t - st) / 0.15) * (1 if t < 9.7 else (10 - t) / 0.3)
                paste_center(img, lay, x, y, 1.0, a)
    # Scene 3: logo + CTA
    if t >= 10.0:
        s = ease_back((t - 10.0) / 0.5)
        paste_center(img, LOGO, W / 2, 640, max(s, 0.01))
        paste_center(img, SUB, W / 2, 900, 1.0, clamp01((t - 10.5) / 0.4))
        pulse = 1 + 0.05 * math.sin((t - 11.0) * 2 * math.pi * 1.6) if t > 11.0 else 1.0
        paste_center(img, CTA, W / 2, 1180, max(ease_back((t - 10.8) / 0.5), 0.01) * pulse)
    for a0, a1, txt in CAPS:
        if a0 <= t < a1:
            caption(img, txt, clamp01((t - a0) / 0.15))
    return img.convert("RGB")

cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
       "-ss", "0", "-t", str(DUR), "-i", MUSIC,
       "-af", f"afade=t=in:d=0.4,afade=t=out:st={DUR-1}:d=1,volume=0.9",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "18", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for i in range(FPS * DUR):
    p.stdin.write(frame(i).tobytes())
p.stdin.close(); p.wait()
