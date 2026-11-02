"""Image/video helpers shared by the employees (pure functions, no file-lane access)."""
import io
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

try:  # iPhone HEIC photos
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".3gp", ".webm"}


def kind_of(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    return "other"


def open_image(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)  # fix phone rotation
    return img.convert("RGB")


def video_frame(video_path: Path) -> bytes:
    """Grab one frame (1s in) as JPEG for the AI to look at."""
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "f.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", str(video_path),
                        "-frames:v", "1", "-vf", "scale=1080:-2", str(out)], check=True)
        if not out.exists():  # very short clip
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path),
                            "-frames:v", "1", "-vf", "scale=1080:-2", str(out)], check=True)
        return out.read_bytes()


def fit_canvas(img: Image.Image, w: int, h: int) -> Image.Image:
    """Fit the whole photo into w×h without cutting the product: blurred photo as background."""
    bg = ImageOps.fit(img, (w, h)).filter(ImageFilter.GaussianBlur(28))
    bg = Image.blend(bg, Image.new("RGB", (w, h), (12, 30, 45)), 0.35)
    fg = ImageOps.contain(img, (w, h))
    bg.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
    return bg


def _font(size: int):
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def brand(img: Image.Image, logo_path: Path | None, strip_text: str, strip_color=(11, 42, 74),
          accent=(255, 199, 44)) -> Image.Image:
    """Add a slim brand strip at the bottom + logo in the corner."""
    img = img.copy()
    w, h = img.size
    sh = max(44, h // 22)
    d = ImageDraw.Draw(img)
    d.rectangle([0, h - sh, w, h], fill=strip_color)
    d.rectangle([0, h - sh, w, h - sh + 4], fill=accent)
    f = _font(int(sh * 0.45))
    tw = d.textlength(strip_text, font=f)
    d.text(((w - tw) / 2, h - sh + (sh - sh * 0.45) / 2), strip_text, font=f, fill=(255, 255, 255))
    if logo_path and logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        lw = w // 6
        logo = ImageOps.contain(logo, (lw, lw))
        pad = w // 40
        img.paste(logo, (w - logo.width - pad, pad), logo)
    return img


def to_jpeg(img: Image.Image, quality=90, max_side=None) -> bytes:
    if max_side and max(img.size) > max_side:
        img = ImageOps.contain(img, (max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True, progressive=False)
    return buf.getvalue()


def prepare_video(src: Path, dst: Path, w: int, h: int, max_seconds: int):
    """Re-encode to vertical H.264/AAC so Instagram/WhatsApp accept it."""
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x0B2A4A,fps=30")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-t", str(max_seconds),
                    "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-movflags", "+faststart", str(dst)], check=True)
