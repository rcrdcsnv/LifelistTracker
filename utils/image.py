# utils/image.py
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
from PIL import Image
import piexif
import io
import base64
from datetime import datetime


def extract_exif_data(photo_path: Path) -> Tuple[Optional[float], Optional[float], Optional[datetime]]:
    """Extract EXIF data from a photo file"""
    try:
        exif_dict = piexif.load(str(photo_path))

        # Extract GPS data
        lat = lon = None
        if "GPS" in exif_dict and exif_dict["GPS"]:
            gps = exif_dict["GPS"]

            if all(tag in gps for tag in [piexif.GPSIFD.GPSLatitude, piexif.GPSIFD.GPSLatitudeRef]):
                lat_ref = gps[piexif.GPSIFD.GPSLatitudeRef].decode()
                lat_tuple = gps[piexif.GPSIFD.GPSLatitude]
                lat = _convert_to_degrees(lat_tuple)
                if lat_ref == 'S':
                    lat = -lat

            if all(tag in gps for tag in [piexif.GPSIFD.GPSLongitude, piexif.GPSIFD.GPSLongitudeRef]):
                lon_ref = gps[piexif.GPSIFD.GPSLongitudeRef].decode()
                lon_tuple = gps[piexif.GPSIFD.GPSLongitude]
                lon = _convert_to_degrees(lon_tuple)
                if lon_ref == 'W':
                    lon = -lon

        # Get date taken
        date_taken = None
        if "Exif" in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
            date_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode()
            try:
                date_taken = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            except ValueError:
                pass

        return lat, lon, date_taken

    except Exception as e:
        print(f"Error extracting EXIF data: {e}")
        return None, None, None


def _convert_to_degrees(dms_tuple: Tuple) -> float:
    """Convert EXIF GPS coordinate format to decimal degrees"""
    if not dms_tuple or len(dms_tuple) != 3:
        return 0.0

    degrees = dms_tuple[0][0] / dms_tuple[0][1] if dms_tuple[0][1] else 0
    minutes = dms_tuple[1][0] / dms_tuple[1][1] if dms_tuple[1][1] else 0
    seconds = dms_tuple[2][0] / dms_tuple[2][1] if dms_tuple[2][1] else 0

    return degrees + (minutes / 60.0) + (seconds / 3600.0)


def resize_image(image_path: Path, size: Tuple[int, int],
                 format: str = "JPEG", quality: int = 85) -> Optional[Image.Image]:
    """Create a resized copy of an image"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                img = bg

            # Create a copy to avoid modifying original
            img_copy = img.copy()
            img_copy.thumbnail(size)
            return img_copy
    except Exception as e:
        print(f"Error resizing image {image_path}: {e}")
        return None


def image_to_base64(image: Image.Image, format: str = "JPEG",
                    quality: int = 85) -> Optional[str]:
    """Convert a PIL Image to base64 string"""
    try:
        buffer = io.BytesIO()
        image.save(buffer, format=format, quality=quality)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None