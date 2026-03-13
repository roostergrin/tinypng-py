"""Smoke tests for tinypng.py — exercises resize/convert logic without hitting the TinyPNG API."""

import os
import shutil
import tempfile
import sys

# Make sure we can import the module
sys.path.insert(0, os.path.dirname(__file__))

from PIL import Image
import tinypng as tp


def make_test_image(directory, name="test.png", width=3000, height=2000, mode="RGB"):
    """Create a simple test image and save it."""
    img = Image.new(mode, (width, height), color="red")
    path = os.path.join(directory, name)
    img.save(path)
    img.close()
    return path


def test_is_image():
    """is_image correctly identifies image extensions."""
    assert tp.is_image("photo.jpg")
    assert tp.is_image("PHOTO.JPG")
    assert tp.is_image("pic.jpeg")
    assert tp.is_image("icon.png")
    assert tp.is_image("shot.webp")
    assert tp.is_image("scan.tiff")
    assert tp.is_image("raw.bmp")
    assert not tp.is_image("doc.pdf")
    assert not tp.is_image("readme.txt")
    assert not tp.is_image(".DS_Store")
    print("  PASS: is_image")


def test_resize_and_convert_default():
    """Default mode produces both 750w and 1920w in jpg and webp."""
    with tempfile.TemporaryDirectory() as tmpdir:
        make_test_image(tmpdir, "sample.png", width=3000, height=2000)
        files = tp.resize_and_convert(tmpdir, hero_mode=False)

        names = sorted(os.path.basename(f) for f in files)
        expected = sorted([
            "sample--750w.jpg",
            "sample--750w.webp",
            "sample--1920w.jpg",
            "sample--1920w.webp",
        ])
        assert names == expected, f"Expected {expected}, got {names}"

        # Verify all files exist
        for f in files:
            assert os.path.isfile(f), f"Missing: {f}"

        # Verify 750w image was actually resized to max 1200px wide
        img750 = Image.open([f for f in files if "750w.jpg" in f][0])
        assert img750.width == 1200, f"Expected 1200px, got {img750.width}"
        img750.close()

        # Verify 1920w image was actually resized to max 2560px wide
        img1920 = Image.open([f for f in files if "1920w.jpg" in f][0])
        assert img1920.width == 2560, f"Expected 2560px, got {img1920.width}"
        img1920.close()

        print("  PASS: resize_and_convert (default mode)")


def test_resize_and_convert_hero_mode():
    """Hero mode: 'hero' images get 1920w only, others get 750w only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        make_test_image(tmpdir, "hero-banner.png", width=4000, height=2000)
        make_test_image(tmpdir, "thumbnail.png", width=3000, height=1500)
        files = tp.resize_and_convert(tmpdir, hero_mode=True)

        names = sorted(os.path.basename(f) for f in files)
        expected = sorted([
            "hero-banner--1920w.jpg",
            "hero-banner--1920w.webp",
            "thumbnail--750w.jpg",
            "thumbnail--750w.webp",
        ])
        assert names == expected, f"Expected {expected}, got {names}"
        print("  PASS: resize_and_convert (hero mode)")


def test_resize_small_image_not_upscaled():
    """Images smaller than target width should not be upscaled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        make_test_image(tmpdir, "small.png", width=800, height=600)
        files = tp.resize_and_convert(tmpdir, hero_mode=False)

        # Both sizes should exist but none should be larger than original 800px
        for f in files:
            img = Image.open(f)
            assert img.width <= 800, f"{os.path.basename(f)} was upscaled to {img.width}px"
            img.close()

        print("  PASS: small images not upscaled")


def test_rgba_conversion():
    """RGBA images (e.g., PNGs with transparency) are converted to RGB for JPG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        make_test_image(tmpdir, "transparent.png", width=2000, height=1000, mode="RGBA")
        files = tp.resize_and_convert(tmpdir, hero_mode=False)

        jpg_files = [f for f in files if f.endswith(".jpg")]
        assert len(jpg_files) > 0, "No JPG files created"
        for f in jpg_files:
            img = Image.open(f)
            assert img.mode == "RGB", f"JPG {os.path.basename(f)} has mode {img.mode}"
            img.close()

        print("  PASS: RGBA to RGB conversion")


def test_copy_to_unoptimized():
    """copy_to_unoptimized copies files to the unoptimized folder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a fake file to copy
        src = os.path.join(tmpdir, "fake.jpg")
        with open(src, "w") as f:
            f.write("not a real image")

        # Temporarily override UNOPTIMIZED to a temp location
        original = tp.UNOPTIMIZED
        tp.UNOPTIMIZED = os.path.join(tmpdir, "unoptimized")
        try:
            tp.copy_to_unoptimized([src])
            dest = os.path.join(tp.UNOPTIMIZED, "fake.jpg")
            assert os.path.isfile(dest), f"File not copied to {dest}"
        finally:
            tp.UNOPTIMIZED = original

        print("  PASS: copy_to_unoptimized")


def test_no_images_returns_empty():
    """resize_and_convert returns empty list when no images found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a non-image file
        with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
            f.write("not an image")
        files = tp.resize_and_convert(tmpdir)
        assert files == [], f"Expected empty list, got {files}"
        print("  PASS: no images returns empty list")


def test_tinypng_api():
    """End-to-end: create an image, resize, and compress via TinyPNG API."""
    import tinify
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test image
        make_test_image(tmpdir, "api_test.png", width=2000, height=1000)

        # Resize it
        files = tp.resize_and_convert(tmpdir, hero_mode=False)
        assert len(files) > 0, "No files produced by resize"

        # Pick one file and compress it via TinyPNG
        test_file = files[0]
        original_size = os.path.getsize(test_file)

        compressed_path = os.path.join(tmpdir, "compressed_" + os.path.basename(test_file))
        source = tinify.from_file(test_file)
        source.to_file(compressed_path)

        assert os.path.isfile(compressed_path), "Compressed file not created"
        compressed_size = os.path.getsize(compressed_path)
        assert compressed_size > 0, "Compressed file is empty"
        assert compressed_size < original_size, (
            f"Compressed ({compressed_size}) not smaller than original ({original_size})"
        )

        print(f"  API compression: {original_size} → {compressed_size} bytes "
              f"({100 - compressed_size * 100 // original_size}% reduction)")
        print(f"  Compressions this month: {tinify.compression_count}/500")
        print("  PASS: TinyPNG API compression")


if __name__ == "__main__":
    print("Running smoke tests...\n")
    test_is_image()
    test_resize_and_convert_default()
    test_resize_and_convert_hero_mode()
    test_resize_small_image_not_upscaled()
    test_rgba_conversion()
    test_copy_to_unoptimized()
    test_no_images_returns_empty()
    test_tinypng_api()
    print("\nAll smoke tests passed!")
