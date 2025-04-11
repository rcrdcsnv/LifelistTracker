"""
PhotoUtils - Utilities for working with photos and images
"""
import os
from datetime import datetime
from PIL import Image, ImageTk
import exifread


class PhotoUtils:
    """
    Static utility class for photo manipulation and EXIF data extraction
    """

    @staticmethod
    def extract_exif_data(photo_path):
        """
        Extract EXIF data from a photo file

        Args:
            photo_path (str): Path to the photo file

        Returns:
            tuple: (latitude, longitude, date_taken) or (None, None, None) if extraction fails
        """
        try:
            with open(photo_path, 'rb') as f:
                tags = exifread.process_file(f)

            # Extract GPS coordinates if available
            lat = None
            lon = None
            date_taken = None

            if 'GPS GPSLatitude' in tags and 'GPS GPSLatitudeRef' in tags:
                lat_ref = tags['GPS GPSLatitudeRef'].values
                lat_values = tags['GPS GPSLatitude'].values
                lat = PhotoUtils._convert_to_degrees(lat_values)
                if lat_ref == 'S':
                    lat = -lat

            if 'GPS GPSLongitude' in tags and 'GPS GPSLongitudeRef' in tags:
                lon_ref = tags['GPS GPSLongitudeRef'].values
                lon_values = tags['GPS GPSLongitude'].values
                lon = PhotoUtils._convert_to_degrees(lon_values)
                if lon_ref == 'W':
                    lon = -lon

            # Get date taken
            if 'EXIF DateTimeOriginal' in tags:
                date_str = str(tags['EXIF DateTimeOriginal'])
                try:
                    date_taken = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                except ValueError:
                    date_taken = None

            return lat, lon, date_taken
        except Exception as e:
            print(f"Error extracting EXIF data: {e}")
            return None, None, None

    @staticmethod
    def _convert_to_degrees(values):
        """
        Helper method to convert GPS coordinates from EXIF to decimal degrees

        Args:
            values: EXIF coordinate values

        Returns:
            float: Decimal degrees
        """
        d = float(values[0].num) / float(values[0].den)
        m = float(values[1].num) / float(values[1].den)
        s = float(values[2].num) / float(values[2].den)
        return d + (m / 60.0) + (s / 3600.0)

    @staticmethod
    def resize_image_for_thumbnail(img_path, size=(100, 100)):
        """
        Resize an image to create a thumbnail

        Args:
            img_path (str): Path to the image file
            size (tuple): Desired thumbnail size as (width, height)

        Returns:
            ImageTk.PhotoImage: Thumbnail image ready for display in Tkinter
            or None if creation fails
        """
        try:
            img = Image.open(img_path)
            img.thumbnail(size)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return None

    @staticmethod
    def image_to_base64(img_path, max_size=(200, 150), is_pin=False):
        """
        Convert an image to a base64-encoded string with optimal quality

        Args:
            img_path (str): Path to the image file
            max_size (tuple): Maximum size as (width, height)
            is_pin (bool): Whether this image is for a map pin (needs different processing)

        Returns:
            tuple: (base64_string, format) or (None, None) if conversion fails
        """
        try:
            import base64
            from io import BytesIO

            # Open the image
            img = Image.open(img_path)

            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                img = background

            # For pins, use a different approach - crop to square first for better pins
            if is_pin:
                # Get dimensions
                width, height = img.size

                # Determine the crop box for a center square crop
                if width > height:
                    left = (width - height) / 2
                    top = 0
                    right = (width + height) / 2
                    bottom = height
                else:
                    left = 0
                    top = (height - width) / 2
                    right = width
                    bottom = (height + width) / 2

                # Crop the image to a square
                img = img.crop((left, top, right, bottom))

                # Now resize to exact dimensions (not thumbnail which preserves aspect ratio)
                # Use a fixed size for pins to ensure consistency
                pin_size = (max_size[0], max_size[0])  # Make it square
                img = img.resize(pin_size, Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)

                # Save as PNG for better quality
                buffered = BytesIO()
                img.save(buffered, format="PNG", optimize=True)
            else:
                # For popup images, use the thumbnail approach
                img.thumbnail(max_size, Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)

                # Save as high-quality JPEG
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=95, optimize=True)

            # Get base64 encoding
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            return img_str, "png" if is_pin else "jpeg"
        except Exception as e:
            print(f"Error encoding image: {e}")
            return None, None