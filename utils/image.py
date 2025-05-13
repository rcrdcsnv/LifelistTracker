# utils/image.py
from pathlib import Path
from typing import Tuple, Optional
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


from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np


def extract_fits_data(file_path):
    """Extract data from FITS file"""
    try:
        with fits.open(file_path) as hdul:
            # Extract header information
            header = hdul[0].header

            # Extract key information
            info = {
                'object': header.get('OBJECT', None),
                'telescope': header.get('TELESCOP', None),
                'instrument': header.get('INSTRUME', None),
                'filter': header.get('FILTER', None),
                'exposure': header.get('EXPTIME', None),
                'date_obs': header.get('DATE-OBS', None),
                'ra': header.get('RA', None),
                'dec': header.get('DEC', None)
            }

            return info
    except Exception as e:
        print(f"Error extracting FITS data: {e}")
        return None


def fits_to_image(file_path, output_path=None):
    """Convert FITS file to a viewable image"""
    try:
        with fits.open(file_path) as hdul:
            # Get image data
            data = hdul[0].data

            # Apply log scaling which is common for astronomical images
            data = np.log1p(data - np.min(data))

            # Normalize between 0 and 1
            data = data / np.max(data)

            # Create image
            plt.figure(figsize=(8, 8))
            plt.imshow(data, cmap='gray')
            plt.axis('off')

            if output_path:
                plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
                plt.close()
                return output_path
            else:
                # Convert to PIL image
                from io import BytesIO
                buf = BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
                plt.close()
                buf.seek(0)
                from PIL import Image
                return Image.open(buf)
    except Exception as e:
        print(f"Error converting FITS to image: {e}")
        return None

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