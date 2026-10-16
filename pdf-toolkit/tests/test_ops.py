import io
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import ops  # noqa: E402


def photo(width=2400, height=1600, seed=0) -> Image.Image:
    """A photo-like image: smooth gradients plus fine noise, so JPEG has work to do."""
    base = Image.linear_gradient("L").resize((width, height)).convert("RGB")
    noise = Image.effect_noise((width, height), 40 + seed).convert("RGB")
    img = Image.blend(base, noise, 0.35)
    draw = ImageDraw.Draw(img)
    draw.ellipse((width * 0.2, height * 0.2, width * 0.6, height * 0.8), fill=(200, 80, 40))
    return img.filter(ImageFilter.GaussianBlur(0.6))


class OpsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls._tmp.name)
        d = cls.dir

        cls.jpg = d / "photo.jpg"
        photo().save(cls.jpg, "JPEG", quality=98)

        cls.png = d / "graphic.png"
        rgba = photo(1200, 900, seed=5).convert("RGBA")
        rgba.putalpha(Image.linear_gradient("L").resize(rgba.size))
        rgba.save(cls.png, "PNG")

        cls.rotated = d / "rotated.jpg"
        exif = Image.Exif()
        exif[0x0112] = 6  # rotate 90° clockwise on display
        photo(800, 400).save(cls.rotated, "JPEG", quality=90, exif=exif)

        # Image-heavy PDF: three pages with high-resolution photos.
        cls.heavy_pdf = d / "heavy.pdf"
        doc = pymupdf.open()
        for i in range(3):
            page = doc.new_page()
            buf = io.BytesIO()
            photo(2400, 3200, seed=i).save(buf, "JPEG", quality=95)
            page.insert_image(page.rect, stream=buf.getvalue())
            page.insert_text((50, 50), f"Page {i + 1}", fontsize=24)
        doc.save(cls.heavy_pdf)
        doc.close()

        cls.text_pdf = d / "text.pdf"
        doc = pymupdf.open()
        for i in range(5):
            doc.new_page().insert_text((72, 72), f"Hello page {i + 1}")
        doc.save(cls.text_pdf, garbage=4, deflate=True)
        doc.close()

        cls.locked_pdf = d / "locked.pdf"
        doc = pymupdf.open()
        doc.new_page().insert_text((72, 72), "secret")
        doc.save(cls.locked_pdf, encryption=pymupdf.PDF_ENCRYPT_AES_256,
                 user_pw="pw", owner_pw="pw")
        doc.close()

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def out(self, name):
        p = self.dir / name
        p.mkdir(exist_ok=True)
        return str(p)

    # --- compress PDF ------------------------------------------------------ #

    def test_compress_pdf_shrinks_image_heavy_file(self):
        sizes = {}
        for level in ("light", "recommended", "extreme"):
            r = ops.compress_pdf(str(self.heavy_pdf), self.out(f"cp_{level}"), level)
            self.assertTrue(r["ok"])
            self.assertLess(r["after"], r["before"])
            with pymupdf.open(r["output"]) as doc:
                self.assertEqual(doc.page_count, 3)
                self.assertIn("Page 2", doc[1].get_text())
            sizes[level] = r["after"]
        self.assertLessEqual(sizes["extreme"], sizes["recommended"])
        self.assertLessEqual(sizes["recommended"], sizes["light"])

    def test_compress_pdf_never_grows(self):
        r = ops.compress_pdf(str(self.text_pdf), self.out("cp_text"))
        self.assertLessEqual(r["after"], r["before"])

    def test_compress_pdf_grayscale(self):
        r = ops.compress_pdf(str(self.heavy_pdf), self.out("cp_gray"), grayscale=True)
        self.assertTrue(r["ok"])
        self.assertLess(r["after"], r["before"])

    def test_locked_pdf_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "password"):
            ops.compress_pdf(str(self.locked_pdf), self.out("cp_locked"))

    def test_outputs_do_not_overwrite(self):
        d = self.out("cp_twice")
        a = ops.compress_pdf(str(self.heavy_pdf), d)
        b = ops.compress_pdf(str(self.heavy_pdf), d)
        self.assertNotEqual(a["output"], b["output"])
        self.assertTrue(b["output"].endswith("heavy_compressed (1).pdf"))

    # --- compress images --------------------------------------------------- #

    def test_compress_jpeg(self):
        r = ops.compress_image(str(self.jpg), self.out("ci_jpg"), quality=70)
        self.assertLess(r["after"], r["before"])
        self.assertTrue(r["output"].endswith(".jpg"))

    def test_compress_png_keeps_alpha(self):
        r = ops.compress_image(str(self.png), self.out("ci_png"), quality=70)
        self.assertLess(r["after"], r["before"])
        with Image.open(r["output"]) as img:
            self.assertEqual(img.format, "PNG")
            self.assertTrue(ops._has_alpha(img))

    def test_compress_resize_and_convert_to_webp(self):
        r = ops.compress_image(str(self.jpg), self.out("ci_webp"), quality=75,
                               max_dim=1280, fmt="webp")
        with Image.open(r["output"]) as img:
            self.assertEqual(img.format, "WEBP")
            self.assertEqual(max(img.size), 1280)

    def test_png_to_jpg_flattens_alpha(self):
        r = ops.compress_image(str(self.png), self.out("ci_flat"), fmt="jpg")
        with Image.open(r["output"]) as img:
            self.assertEqual(img.mode, "RGB")

    def test_compress_respects_exif_rotation(self):
        r = ops.compress_image(str(self.rotated), self.out("ci_rot"))
        with Image.open(r["output"]) as img:
            self.assertEqual(img.size, (400, 800))

    # --- merge ------------------------------------------------------------- #

    def test_merge_pdfs_in_order(self):
        out = self.dir / "merged.pdf"
        r = ops.merge_pdfs([str(self.text_pdf), str(self.heavy_pdf)], str(out))
        self.assertEqual(r["pages"], 8)
        with pymupdf.open(out) as doc:
            self.assertIn("Hello page 1", doc[0].get_text())
            self.assertIn("Page 1", doc[5].get_text())

    def test_merge_needs_two(self):
        with self.assertRaises(ValueError):
            ops.merge_pdfs([str(self.text_pdf)], str(self.dir / "x.pdf"))

    # --- images to pdf ----------------------------------------------------- #

    def test_images_to_pdf_fit(self):
        out = self.dir / "imgs_fit.pdf"
        r = ops.images_to_pdf([str(self.jpg), str(self.png), str(self.rotated)], str(out))
        self.assertEqual(r["pages"], 3)
        with pymupdf.open(out) as doc:
            self.assertAlmostEqual(doc[0].rect.width, 2400 * 0.75)
            # rotated.jpg is 800x400 stored, displayed 400x800 -> portrait page
            self.assertLess(doc[2].rect.width, doc[2].rect.height)

    def test_images_to_pdf_a4_auto_orientation_with_margin(self):
        out = self.dir / "imgs_a4.pdf"
        ops.images_to_pdf([str(self.jpg), str(self.rotated)], str(out),
                          page_size="a4", margin=20)
        with pymupdf.open(out) as doc:
            self.assertGreater(doc[0].rect.width, doc[0].rect.height)  # landscape photo
            self.assertLess(doc[1].rect.width, doc[1].rect.height)
            bbox = doc[0].get_image_info()[0]["bbox"]
            self.assertGreaterEqual(bbox[0], 19.9)

    def test_jpeg_embedded_without_recompression(self):
        out = self.dir / "imgs_raw.pdf"
        ops.images_to_pdf([str(self.jpg)], str(out))
        with pymupdf.open(out) as doc:
            xref = doc[0].get_images()[0][0]
            self.assertEqual(doc.extract_image(xref)["image"], self.jpg.read_bytes())

    # --- pdf to images ----------------------------------------------------- #

    def test_pdf_to_png(self):
        r = ops.pdf_to_images(str(self.heavy_pdf), self.out("p2i"), dpi=72)
        files = sorted(Path(r["output"]).iterdir())
        self.assertEqual([f.name for f in files],
                         ["heavy_page_001.png", "heavy_page_002.png", "heavy_page_003.png"])
        with Image.open(files[0]) as img:
            self.assertEqual(img.size, (595, 842))  # A4 at 72 dpi

    def test_pdf_to_jpg_page_range(self):
        r = ops.pdf_to_images(str(self.text_pdf), self.out("p2i_range"), fmt="jpg",
                              dpi=100, pages="2, 4-")
        names = sorted(f.name for f in Path(r["output"]).iterdir())
        self.assertEqual(names, ["text_page_002.jpg", "text_page_004.jpg", "text_page_005.jpg"])

    def test_parse_page_spec(self):
        self.assertEqual(ops.parse_page_spec("", 3), [0, 1, 2])
        self.assertEqual(ops.parse_page_spec("1-2,2,9", 10), [0, 1, 8])
        self.assertEqual(ops.parse_page_spec("-2", 5), [0, 1])
        self.assertEqual(ops.parse_page_spec("3-100", 4), [2, 3])
        for bad in ("abc", "0", "5-2", "20"):
            with self.assertRaises(ValueError):
                ops.parse_page_spec(bad, 10)

    def test_cancel(self):
        with self.assertRaises(ops.OperationCancelled):
            ops.pdf_to_images(str(self.heavy_pdf), self.out("p2i_cancel"),
                              cancelled=lambda: True)

    # --- helpers ----------------------------------------------------------- #

    def test_thumbnail_and_expand(self):
        data, pages = ops.thumbnail_png(str(self.heavy_pdf))
        self.assertTrue(data.startswith(b"\x89PNG"))
        self.assertEqual(pages, 3)
        data, pages = ops.thumbnail_png(str(self.jpg))
        self.assertTrue(data.startswith(b"\x89PNG"))
        self.assertIsNone(ops.thumbnail_png(str(self.locked_pdf))[0])
        found = ops.expand_paths([str(self.dir)])
        self.assertIn(str(self.jpg), found)


if __name__ == "__main__":
    unittest.main()
