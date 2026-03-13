from datetime import datetime
from PIL import Image
import tinify
import os
import shutil
import sys

# https://tinypng.com/developers GET YOUR API KEY HERE
tinify.key = "6GN097Srn5p20YJmdfgcSxFDcz2V8tvY"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
UNOPTIMIZED = os.path.join(SCRIPT_DIR, "unoptimized")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".webp"}

SIZES = [
    (1200, "750w"),   # mogrify -resize 1200 → "750px" folder
    (2560, "1920w"),  # mogrify -resize 2560 → "1920px" folder
]
FORMATS = ["jpg", "webp"]


def is_image(filename):
    return os.path.splitext(filename)[1].lower() in IMAGE_EXTS


def resize_and_convert(source_dir, hero_mode=False):
    """Resize all images in source_dir and convert to jpg/webp.

    hero_mode: when True, "hero" images get 1920w only, everything else gets 750w only.
               when False (default), all images get both sizes.
    """
    images = [f for f in os.listdir(source_dir) if is_image(f)]
    if not images:
        print("No images found in " + source_dir)
        return []

    resize_dir = os.path.join(source_dir, "resize")
    os.makedirs(resize_dir, exist_ok=True)

    output_files = []

    for filename in images:
        filepath = os.path.join(source_dir, filename)
        name = os.path.splitext(filename)[0]

        try:
            img = Image.open(filepath)
        except Exception as e:
            print(f"Skipping {filename}: {e}")
            continue

        # Convert to RGB if needed (for saving as JPG)
        if img.mode in ("RGBA", "P"):
            rgb_img = img.convert("RGB")
        else:
            rgb_img = img

        if hero_mode:
            if "hero" in name.lower():
                sizes = [(2560, "1920w")]
                print(f"  {filename} → hero → 1920w only")
            else:
                sizes = [(1200, "750w")]
                print(f"  {filename} → 750w only")
        else:
            sizes = SIZES

        for max_width, suffix in sizes:
            # Resize proportionally by width
            if img.width > max_width:
                ratio = max_width / img.width
                new_size = (max_width, int(img.height * ratio))
                resized = rgb_img.resize(new_size, Image.LANCZOS)
            else:
                resized = rgb_img

            for fmt in FORMATS:
                out_name = f"{name}--{suffix}.{fmt}"
                out_path = os.path.join(resize_dir, out_name)

                if fmt == "webp":
                    resized.save(out_path, "WEBP", quality=90)
                else:
                    resized.save(out_path, "JPEG", quality=90)

                output_files.append(out_path)
                print(f"  Created: {out_name}")

        img.close()

    return output_files


def copy_to_unoptimized(files):
    """Copy all resized files to the unoptimized folder for TinyPNG."""
    os.makedirs(UNOPTIMIZED, exist_ok=True)
    for f in files:
        shutil.copy2(f, UNOPTIMIZED)
    print(f"\nCopied {len(files)} files to {UNOPTIMIZED}")


def tinypng_compress():
    """Compress all files in unoptimized/ via TinyPNG API."""
    now = datetime.now()
    output = now.strftime("%m-%d-%Y--%H:%M:%S")
    output_path = os.path.join(SCRIPT_DIR, "output", output)
    os.makedirs(output_path, exist_ok=True)

    for file in os.listdir(UNOPTIMIZED):
        if file.startswith("."):
            continue
        src = os.path.join(UNOPTIMIZED, file)
        if not os.path.isfile(src):
            continue
        print(f"Compressing: {file}")
        fileSrc = tinify.from_file(src)
        fileSrc.to_file(os.path.join(output_path, file))
        os.remove(src)
        compressions_this_month = tinify.compression_count
        if compressions_this_month is not None:
            print(f"  {compressions_this_month}/500")

    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    # Usage: python tinypng.py [--hero] [image_folder]
    #   --hero: "hero" images → 1920w only, everything else → 750w only
    #   No flag: all images get both 750w and 1920w

    hero_mode = "--hero" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--hero"]

    if args:
        source_dir = os.path.abspath(args[0])
    else:
        source_dir = os.getcwd()

    # Check if there are images in the source directory (and it's not the script dir)
    source_images = [f for f in os.listdir(source_dir) if is_image(f)]

    if source_images and source_dir != SCRIPT_DIR:
        print(f"Found {len(source_images)} images in {source_dir}")
        print("Resizing and converting...\n")
        if hero_mode:
            print("Hero mode: 'hero' → 1920w, others → 750w\n")
        files = resize_and_convert(source_dir, hero_mode=hero_mode)
        if files:
            copy_to_unoptimized(files)
            print("\nCompressing with TinyPNG...\n")
            tinypng_compress()
    elif os.listdir(UNOPTIMIZED) if os.path.exists(UNOPTIMIZED) else False:
        print("No source images found. Compressing files already in unoptimized/...\n")
        tinypng_compress()
    else:
        print("No images found to process.")
        print(f"  Either run from a folder with images, or place files in {UNOPTIMIZED}")
