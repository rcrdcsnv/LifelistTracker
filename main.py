import os
import json
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import folium
from folium.plugins import MarkerCluster
import webbrowser
import exifread
from datetime import datetime
import shutil
import re

# Set appearance mode and default theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class Database:
    def __init__(self, db_path="lifelists.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Create tables for lifelists, observations, photos, tags, and custom fields
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS lifelists (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            taxonomy TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_fields (
            id INTEGER PRIMARY KEY,
            lifelist_id INTEGER,
            field_name TEXT,
            field_type TEXT,
            FOREIGN KEY (lifelist_id) REFERENCES lifelists (id) ON DELETE CASCADE
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY,
            lifelist_id INTEGER,
            species_name TEXT,
            observation_date TIMESTAMP,
            location TEXT,
            latitude REAL,
            longitude REAL,
            tier TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lifelist_id) REFERENCES lifelists (id) ON DELETE CASCADE
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS observation_custom_fields (
            id INTEGER PRIMARY KEY,
            observation_id INTEGER,
            field_id INTEGER,
            value TEXT,
            FOREIGN KEY (observation_id) REFERENCES observations (id) ON DELETE CASCADE,
            FOREIGN KEY (field_id) REFERENCES custom_fields (id) ON DELETE CASCADE
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY,
            observation_id INTEGER,
            file_path TEXT,
            is_primary INTEGER DEFAULT 0,
            latitude REAL,
            longitude REAL,
            taken_date TIMESTAMP,
            FOREIGN KEY (observation_id) REFERENCES observations (id) ON DELETE CASCADE
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS observation_tags (
            observation_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (observation_id, tag_id),
            FOREIGN KEY (observation_id) REFERENCES observations (id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
        )
        ''')

        self.conn.commit()

    def create_lifelist(self, name, taxonomy=None):
        try:
            self.cursor.execute(
                "INSERT INTO lifelists (name, taxonomy) VALUES (?, ?)",
                (name, taxonomy)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None  # Lifelist with this name already exists

    def get_lifelists(self):
        self.cursor.execute("SELECT id, name, taxonomy FROM lifelists ORDER BY name")
        return self.cursor.fetchall()

    def delete_lifelist(self, lifelist_id):
        # First, get the lifelist data for potential export
        self.cursor.execute("SELECT name FROM lifelists WHERE id = ?", (lifelist_id,))
        lifelist = self.cursor.fetchone()

        if lifelist:
            self.cursor.execute("DELETE FROM lifelists WHERE id = ?", (lifelist_id,))
            self.conn.commit()
            return True
        return False

    def add_custom_field(self, lifelist_id, field_name, field_type):
        try:
            self.cursor.execute(
                "INSERT INTO custom_fields (lifelist_id, field_name, field_type) VALUES (?, ?, ?)",
                (lifelist_id, field_name, field_type)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_custom_fields(self, lifelist_id):
        self.cursor.execute(
            "SELECT id, field_name, field_type FROM custom_fields WHERE lifelist_id = ?",
            (lifelist_id,)
        )
        return self.cursor.fetchall()

    def add_observation(self, lifelist_id, species_name, observation_date=None,
                        location=None, latitude=None, longitude=None, tier="wild", notes=None):
        try:
            self.cursor.execute(
                """INSERT INTO observations 
                (lifelist_id, species_name, observation_date, location, latitude, longitude, tier, notes) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (lifelist_id, species_name, observation_date, location, latitude, longitude, tier, notes)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None

    def get_observations(self, lifelist_id, tier=None, tag_ids=None, search_term=None):
        query = "SELECT id, species_name, observation_date, location, tier FROM observations WHERE lifelist_id = ?"
        params = [lifelist_id]

        if tier:
            query += " AND tier = ?"
            params.append(tier)

        if search_term:
            query += " AND (species_name LIKE ? OR notes LIKE ? OR location LIKE ?)"
            search_param = f"%{search_term}%"
            params.extend([search_param, search_param, search_param])

        if tag_ids and len(tag_ids) > 0:
            placeholders = ','.join(['?' for _ in tag_ids])
            query = f"""
            SELECT o.id, o.species_name, o.observation_date, o.location, o.tier
            FROM observations o
            JOIN observation_tags ot ON o.id = ot.observation_id
            WHERE o.lifelist_id = ? AND ot.tag_id IN ({placeholders})
            GROUP BY o.id
            HAVING COUNT(DISTINCT ot.tag_id) = ?
            """
            params = [lifelist_id] + tag_ids + [len(tag_ids)]

        query += " ORDER BY observation_date DESC"

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_observations_by_species(self, lifelist_id, species_name):
        """Get all observations of a specific species in a lifelist"""
        self.cursor.execute(
            "SELECT id FROM observations WHERE lifelist_id = ? AND species_name = ?",
            (lifelist_id, species_name)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def get_primary_photo_for_species(self, lifelist_id, species_name):
        """Get the primary photo for a species across all observations"""
        query = """
        SELECT p.id, p.file_path, p.is_primary, p.latitude, p.longitude, p.taken_date
        FROM photos p
        JOIN observations o ON p.observation_id = o.id
        WHERE o.lifelist_id = ? AND o.species_name = ? AND p.is_primary = 1
        """
        self.cursor.execute(query, (lifelist_id, species_name))
        result = self.cursor.fetchone()

        if result:
            return result

        # If no primary photo is set, find any photo for this species
        query = """
        SELECT p.id, p.file_path, p.is_primary, p.latitude, p.longitude, p.taken_date
        FROM photos p
        JOIN observations o ON p.observation_id = o.id
        WHERE o.lifelist_id = ? AND o.species_name = ?
        LIMIT 1
        """
        self.cursor.execute(query, (lifelist_id, species_name))
        return self.cursor.fetchone()

    def get_observation_details(self, observation_id):
        self.cursor.execute(
            """SELECT id, lifelist_id, species_name, observation_date, location, 
            latitude, longitude, tier, notes FROM observations WHERE id = ?""",
            (observation_id,)
        )
        observation = self.cursor.fetchone()

        if observation:
            # Get custom field values
            self.cursor.execute(
                """SELECT cf.field_name, cf.field_type, ocf.value
                FROM observation_custom_fields ocf
                JOIN custom_fields cf ON ocf.field_id = cf.id
                WHERE ocf.observation_id = ?""",
                (observation_id,)
            )
            custom_fields = self.cursor.fetchall()

            # Get tags
            self.cursor.execute(
                """SELECT t.id, t.name
                FROM tags t
                JOIN observation_tags ot ON t.id = ot.tag_id
                WHERE ot.observation_id = ?""",
                (observation_id,)
            )
            tags = self.cursor.fetchall()

            return observation, custom_fields, tags
        return None, None, None

    def update_observation(self, observation_id, species_name, observation_date=None,
                           location=None, latitude=None, longitude=None, tier="wild", notes=None):
        try:
            self.cursor.execute(
                """UPDATE observations SET
                species_name = ?, observation_date = ?, location = ?, 
                latitude = ?, longitude = ?, tier = ?, notes = ?
                WHERE id = ?""",
                (species_name, observation_date, location, latitude, longitude, tier, notes, observation_id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False

    def delete_observation(self, observation_id):
        try:
            # First, get all photos to delete the files
            self.cursor.execute("SELECT file_path FROM photos WHERE observation_id = ?", (observation_id,))
            photos = self.cursor.fetchall()

            # Delete the observation (cascades to other tables)
            self.cursor.execute("DELETE FROM observations WHERE id = ?", (observation_id,))
            self.conn.commit()

            return True, photos
        except sqlite3.Error:
            return False, None

    def add_photo(self, observation_id, file_path, is_primary=0, latitude=None, longitude=None, taken_date=None):
        try:
            # Get the species and lifelist for this observation
            self.cursor.execute(
                "SELECT species_name, lifelist_id FROM observations WHERE id = ?",
                (observation_id,)
            )
            species_name, lifelist_id = self.cursor.fetchone()

            # If this is being set as primary, reset all other photos for this species
            if is_primary:
                # Get all observations for this species
                self.cursor.execute(
                    "SELECT id FROM observations WHERE lifelist_id = ? AND species_name = ?",
                    (lifelist_id, species_name)
                )
                species_obs_ids = [row[0] for row in self.cursor.fetchall()]

                # Reset all primary photos for this species
                for obs_id in species_obs_ids:
                    self.cursor.execute(
                        "UPDATE photos SET is_primary = 0 WHERE observation_id = ?",
                        (obs_id,)
                    )

            # Insert the new photo
            self.cursor.execute(
                """INSERT INTO photos 
                (observation_id, file_path, is_primary, latitude, longitude, taken_date) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (observation_id, file_path, is_primary, latitude, longitude, taken_date)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding photo: {e}")
            return None

    def get_photos(self, observation_id):
        self.cursor.execute(
            "SELECT id, file_path, is_primary, latitude, longitude, taken_date FROM photos WHERE observation_id = ?",
            (observation_id,)
        )
        return self.cursor.fetchall()

    def set_primary_photo(self, photo_id, observation_id):
        try:
            # First get the species name and lifelist_id for this observation
            self.cursor.execute(
                "SELECT species_name, lifelist_id FROM observations WHERE id = ?",
                (observation_id,)
            )
            result = self.cursor.fetchone()
            if not result:
                return False

            species_name, lifelist_id = result

            # Get all observations for this species in the lifelist
            observation_ids = self.get_observations_by_species(lifelist_id, species_name)

            # Reset primary status for ALL photos of ALL observations of this species
            for obs_id in observation_ids:
                self.cursor.execute(
                    "UPDATE photos SET is_primary = 0 WHERE observation_id = ?",
                    (obs_id,)
                )

            # Set the selected photo as primary
            self.cursor.execute(
                "UPDATE photos SET is_primary = 1 WHERE id = ?",
                (photo_id,)
            )

            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error setting primary photo: {e}")
            return False

    def delete_photo(self, photo_id):
        try:
            # First, get the photo details
            self.cursor.execute("SELECT file_path, is_primary, observation_id FROM photos WHERE id = ?", (photo_id,))
            photo = self.cursor.fetchone()

            if not photo:
                return False, None

            # Delete the photo
            self.cursor.execute("DELETE FROM photos WHERE id = ?", (photo_id,))

            # If this was the primary photo, set another as primary
            if photo[1]:  # is_primary
                self.cursor.execute(
                    "UPDATE photos SET is_primary = 1 WHERE observation_id = ? AND id = (SELECT MIN(id) FROM photos WHERE observation_id = ?)",
                    (photo[2], photo[2])
                )

            self.conn.commit()
            return True, photo[0]  # Return the file path
        except sqlite3.Error as e:
            print(f"Error deleting photo: {e}")
            return False, None

    def get_all_tiers(self, lifelist_id):
        self.cursor.execute(
            "SELECT DISTINCT tier FROM observations WHERE lifelist_id = ?",
            (lifelist_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def add_tag(self, tag_name):
        try:
            self.cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            # Tag already exists, get its ID
            self.cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            return self.cursor.fetchone()[0]

    def get_all_tags(self):
        self.cursor.execute("SELECT id, name FROM tags ORDER BY name")
        return self.cursor.fetchall()

    def add_tag_to_observation(self, observation_id, tag_id):
        try:
            self.cursor.execute(
                "INSERT INTO observation_tags (observation_id, tag_id) VALUES (?, ?)",
                (observation_id, tag_id)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Tag already associated with this observation

    def remove_tag_from_observation(self, observation_id, tag_id):
        self.cursor.execute(
            "DELETE FROM observation_tags WHERE observation_id = ? AND tag_id = ?",
            (observation_id, tag_id)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_observation_tags(self, observation_id):
        self.cursor.execute(
            """SELECT t.id, t.name FROM tags t
            JOIN observation_tags ot ON t.id = ot.tag_id
            WHERE ot.observation_id = ?""",
            (observation_id,)
        )
        return self.cursor.fetchall()

    def export_lifelist(self, lifelist_id, export_path, include_photos=True):
        """Export a lifelist to a portable format (JSON + photos)"""
        try:
            # Get lifelist info
            self.cursor.execute("SELECT id, name, taxonomy FROM lifelists WHERE id = ?", (lifelist_id,))
            lifelist = self.cursor.fetchone()

            if not lifelist:
                return False

            lifelist_data = {
                "id": lifelist[0],
                "name": lifelist[1],
                "taxonomy": lifelist[2],
                "custom_fields": [],
                "observations": []
            }

            # Get custom fields
            self.cursor.execute(
                "SELECT id, field_name, field_type FROM custom_fields WHERE lifelist_id = ?",
                (lifelist_id,)
            )
            for field in self.cursor.fetchall():
                lifelist_data["custom_fields"].append({
                    "id": field[0],
                    "name": field[1],
                    "type": field[2]
                })

            # Get observations
            self.cursor.execute(
                """SELECT id, species_name, observation_date, location, 
                latitude, longitude, tier, notes FROM observations 
                WHERE lifelist_id = ?""",
                (lifelist_id,)
            )

            observations = self.cursor.fetchall()
            photos_dir = os.path.join(export_path, "photos")
            os.makedirs(photos_dir, exist_ok=True)

            for obs in observations:
                obs_data = {
                    "id": obs[0],
                    "species_name": obs[1],
                    "observation_date": obs[2],
                    "location": obs[3],
                    "latitude": obs[4],
                    "longitude": obs[5],
                    "tier": obs[6],
                    "notes": obs[7],
                    "custom_fields": [],
                    "tags": [],
                    "photos": []
                }

                # Get custom field values
                self.cursor.execute(
                    """SELECT cf.field_name, ocf.value
                    FROM observation_custom_fields ocf
                    JOIN custom_fields cf ON ocf.field_id = cf.id
                    WHERE ocf.observation_id = ?""",
                    (obs[0],)
                )

                for field_val in self.cursor.fetchall():
                    obs_data["custom_fields"].append({
                        "field_name": field_val[0],
                        "value": field_val[1]
                    })

                # Get tags
                self.cursor.execute(
                    """SELECT t.name
                    FROM tags t
                    JOIN observation_tags ot ON t.id = ot.tag_id
                    WHERE ot.observation_id = ?""",
                    (obs[0],)
                )

                obs_data["tags"] = [tag[0] for tag in self.cursor.fetchall()]

                # Get photos
                self.cursor.execute(
                    """SELECT id, file_path, is_primary, latitude, longitude, taken_date
                    FROM photos WHERE observation_id = ?""",
                    (obs[0],)
                )

                for photo in self.cursor.fetchall():
                    photo_file = os.path.basename(photo[1])
                    photo_data = {
                        "id": photo[0],
                        "file_name": photo_file,
                        "is_primary": bool(photo[2]),
                        "latitude": photo[3],
                        "longitude": photo[4],
                        "taken_date": photo[5]
                    }

                    obs_data["photos"].append(photo_data)

                    # Copy the photo file if it exists and if include_photos is True
                    if include_photos and os.path.exists(photo[1]):
                        shutil.copy2(photo[1], os.path.join(photos_dir, photo_file))

                lifelist_data["observations"].append(obs_data)

            # Write the JSON file
            with open(os.path.join(export_path, f"{lifelist_data['name']}.json"), 'w') as f:
                json.dump(lifelist_data, f, indent=2)

            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False

    def import_lifelist(self, json_path, photos_dir=None):
        """Import a lifelist from a JSON file"""
        try:
            with open(json_path, 'r') as f:
                lifelist_data = json.load(f)

            # Create the lifelist
            lifelist_name = lifelist_data["name"]
            taxonomy = lifelist_data.get("taxonomy")

            # Check if lifelist already exists
            self.cursor.execute("SELECT id FROM lifelists WHERE name = ?", (lifelist_name,))
            existing = self.cursor.fetchone()

            if existing:
                return False, f"Lifelist '{lifelist_name}' already exists"

            lifelist_id = self.create_lifelist(lifelist_name, taxonomy)

            # Create custom fields
            field_id_mapping = {}
            for field in lifelist_data.get("custom_fields", []):
                new_id = self.add_custom_field(lifelist_id, field["name"], field["type"])
                field_id_mapping[field["id"]] = new_id

            # Import observations
            for obs in lifelist_data.get("observations", []):
                obs_id = self.add_observation(
                    lifelist_id,
                    obs["species_name"],
                    obs.get("observation_date"),
                    obs.get("location"),
                    obs.get("latitude"),
                    obs.get("longitude"),
                    obs.get("tier", "wild"),
                    obs.get("notes")
                )

                # Add custom field values
                for field in obs.get("custom_fields", []):
                    field_name = field["field_name"]
                    # Find the field ID
                    self.cursor.execute(
                        "SELECT id FROM custom_fields WHERE lifelist_id = ? AND field_name = ?",
                        (lifelist_id, field_name)
                    )
                    field_result = self.cursor.fetchone()
                    if field_result:
                        field_id = field_result[0]
                        self.cursor.execute(
                            "INSERT INTO observation_custom_fields (observation_id, field_id, value) VALUES (?, ?, ?)",
                            (obs_id, field_id, field["value"])
                        )

                # Add tags
                for tag_name in obs.get("tags", []):
                    tag_id = self.add_tag(tag_name)
                    self.add_tag_to_observation(obs_id, tag_id)

                # Add photos
                if photos_dir:
                    for photo in obs.get("photos", []):
                        photo_path = os.path.join(photos_dir, photo["file_name"])
                        if os.path.exists(photo_path):
                            self.add_photo(
                                obs_id,
                                photo_path,
                                photo.get("is_primary", 0),
                                photo.get("latitude"),
                                photo.get("longitude"),
                                photo.get("taken_date")
                            )

            self.conn.commit()
            return True, f"Successfully imported lifelist '{lifelist_name}'"
        except Exception as e:
            print(f"Import error: {e}")
            return False, f"Error importing lifelist: {str(e)}"

    def close(self):
        self.conn.close()


class PhotoUtils:
    @staticmethod
    def extract_exif_data(photo_path):
        """Extract EXIF data from a photo file"""
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
        """Helper method to convert GPS coordinates from EXIF to decimal degrees"""
        d = float(values[0].num) / float(values[0].den)
        m = float(values[1].num) / float(values[1].den)
        s = float(values[2].num) / float(values[2].den)
        return d + (m / 60.0) + (s / 3600.0)

    @staticmethod
    def resize_image_for_thumbnail(img_path, size=(100, 100)):
        """Resize an image to create a thumbnail"""
        try:
            img = Image.open(img_path)
            img.thumbnail(size)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return None


class MapGenerator:
    @staticmethod
    def create_observation_map(observations, db, output_path="observation_map.html"):
        """Create a map showing all observation locations"""
        # Create a map centered on the first observation with coordinates
        map_center = [0, 0]
        has_coords = False
        valid_markers = 0

        # First pass - check if any observations have coordinates
        for obs in observations:
            obs_id = obs[0]
            obs_details = db.get_observation_details(obs_id)[0]

            # Check observation coordinates
            if obs_details and obs_details[5] is not None and obs_details[6] is not None:
                map_center = [obs_details[5], obs_details[6]]
                has_coords = True
                valid_markers += 1
                continue

            # Check photo coordinates
            photos = db.get_photos(obs_id)
            for photo in photos:
                if photo[3] is not None and photo[4] is not None:  # lat and lon
                    map_center = [photo[3], photo[4]]
                    has_coords = True
                    valid_markers += 1
                    break

        # If no coordinates found, return error
        if not has_coords:
            return None, "No coordinates available in any observations or photos"

        # Create map
        m = folium.Map(location=map_center, zoom_start=5)

        # Add markers for each observation
        marker_cluster = MarkerCluster().add_to(m)

        for obs in observations:
            obs_id, species_name, obs_date, location, tier = obs

            # Try to get coordinates from observation
            lat, lon = None, None

            obs_details = db.get_observation_details(obs_id)[0]
            if obs_details and obs_details[5] is not None and obs_details[6] is not None:
                lat, lon = obs_details[5], obs_details[6]

            # If no coordinates in observation, try photos
            if lat is None or lon is None:
                photos = db.get_photos(obs_id)
                for photo in photos:
                    if photo[3] is not None and photo[4] is not None:  # lat and lon
                        lat, lon = photo[3], photo[4]
                        break

            if lat is not None and lon is not None:
                popup_content = f"""
                <strong>{species_name}</strong><br>
                Date: {obs_date or 'Unknown'}<br>
                Location: {location or 'Unknown'}<br>
                Tier: {tier or 'Unknown'}
                """

                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=species_name
                ).add_to(marker_cluster)

        # Save the map
        m.save(output_path)
        return output_path, f"{valid_markers} location(s) plotted on map"


class LifelistApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lifelist Manager")
        self.root.geometry("1200x800")

        # Initialize database
        self.db = Database()

        # Set up the main container
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create sidebar
        self.sidebar = ctk.CTkFrame(self.main_container, width=250)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Create content area
        self.content = ctk.CTkFrame(self.main_container)
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create welcome screen
        self.welcome_frame = ctk.CTkFrame(self.content)
        self.welcome_frame.pack(fill=tk.BOTH, expand=True)

        welcome_label = ctk.CTkLabel(
            self.welcome_frame,
            text="Welcome to Lifelist Manager",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        welcome_label.pack(pady=20)

        intro_text = """
        Lifelist Manager helps you track and catalog your observations.

        - Create different lifelists for birds, reptiles, astronomical objects, etc.
        - Add custom fields to track specific information for each observation
        - Attach photos to observations and select primary thumbnails
        - Filter observations by tags and tiers
        - View locations on an interactive map

        Get started by selecting or creating a lifelist from the sidebar.
        """

        intro_label = ctk.CTkLabel(
            self.welcome_frame,
            text=intro_text,
            font=ctk.CTkFont(size=14),
            justify="left",
            wraplength=600
        )
        intro_label.pack(pady=10)

        # Current lifelist and observation state
        self.current_lifelist_id = None
        self.current_observation_id = None

        # Set up the sidebar with lifelists
        self.setup_sidebar()

    def setup_sidebar(self):
        # Clear existing widgets
        for widget in self.sidebar.winfo_children():
            widget.destroy()

        # Add title
        sidebar_title = ctk.CTkLabel(
            self.sidebar,
            text="My Lifelists",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        sidebar_title.pack(pady=10)

        # Add lifelists
        lifelists = self.db.get_lifelists()

        if lifelists:
            for lifelist in lifelists:
                lifelist_btn = ctk.CTkButton(
                    self.sidebar,
                    text=lifelist[1],
                    command=lambda lid=lifelist[0], lname=lifelist[1]: self.open_lifelist(lid, lname)
                )
                lifelist_btn.pack(pady=5, padx=10, fill=tk.X)

        # Add buttons for creating, importing, and exporting lifelists
        separator = ctk.CTkFrame(self.sidebar, height=2, fg_color="gray70")
        separator.pack(fill=tk.X, padx=10, pady=15)

        create_btn = ctk.CTkButton(
            self.sidebar,
            text="Create New Lifelist",
            command=self.show_create_lifelist_dialog
        )
        create_btn.pack(pady=5, padx=10, fill=tk.X)

        import_btn = ctk.CTkButton(
            self.sidebar,
            text="Import Lifelist",
            command=self.import_lifelist
        )
        import_btn.pack(pady=5, padx=10, fill=tk.X)

        # Only show export if a lifelist is selected
        if self.current_lifelist_id:
            export_btn = ctk.CTkButton(
                self.sidebar,
                text="Export Current Lifelist",
                command=self.export_lifelist
            )
            export_btn.pack(pady=5, padx=10, fill=tk.X)

            delete_btn = ctk.CTkButton(
                self.sidebar,
                text="Delete Current Lifelist",
                fg_color="red3",
                hover_color="red4",
                command=self.delete_current_lifelist
            )
            delete_btn.pack(pady=5, padx=10, fill=tk.X)

    def show_create_lifelist_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Create New Lifelist")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        # Add form fields
        ctk.CTkLabel(dialog, text="Lifelist Name:").pack(pady=(20, 5))
        name_entry = ctk.CTkEntry(dialog, width=300)
        name_entry.pack(pady=5)

        ctk.CTkLabel(dialog, text="Taxonomy Reference (optional):").pack(pady=(10, 5))
        taxonomy_entry = ctk.CTkEntry(dialog, width=300)
        taxonomy_entry.pack(pady=5)

        # Custom fields section
        ctk.CTkLabel(dialog, text="Custom Fields:").pack(pady=(15, 5))

        custom_fields_frame = ctk.CTkFrame(dialog)
        custom_fields_frame.pack(pady=5, fill=tk.X, padx=20)

        custom_fields = []

        def add_custom_field_row():
            row_frame = ctk.CTkFrame(custom_fields_frame)
            row_frame.pack(pady=2, fill=tk.X)

            field_name = ctk.CTkEntry(row_frame, width=150, placeholder_text="Field Name")
            field_name.pack(side=tk.LEFT, padx=5)

            field_type = ctk.CTkComboBox(row_frame, values=["text", "number", "date", "boolean"])
            field_type.pack(side=tk.LEFT, padx=5)

            remove_btn = ctk.CTkButton(
                row_frame,
                text="✕",
                width=30,
                command=lambda: remove_field_row(row_frame)
            )
            remove_btn.pack(side=tk.LEFT, padx=5)

            custom_fields.append((field_name, field_type, row_frame))

        def remove_field_row(row):
            for i, (_, _, frame) in enumerate(custom_fields):
                if frame == row:
                    custom_fields.pop(i)
                    break
            row.destroy()

        # Add the first custom field row
        add_custom_field_row()

        # Button to add more custom fields
        add_field_btn = ctk.CTkButton(
            dialog,
            text="+ Add Another Field",
            command=add_custom_field_row
        )
        add_field_btn.pack(pady=10)

        # Create lifelist button
        def create_lifelist():
            name = name_entry.get().strip()
            taxonomy = taxonomy_entry.get().strip() or None

            if not name:
                messagebox.showerror("Error", "Lifelist name is required")
                return

            # Create the lifelist
            lifelist_id = self.db.create_lifelist(name, taxonomy)

            if lifelist_id is None:
                messagebox.showerror("Error", f"A lifelist named '{name}' already exists")
                return

            # Add custom fields
            for field_name_entry, field_type_combobox, _ in custom_fields:
                field_name = field_name_entry.get().strip()
                field_type = field_type_combobox.get()

                if field_name:
                    self.db.add_custom_field(lifelist_id, field_name, field_type)

            # Refresh sidebar and open the new lifelist
            self.setup_sidebar()
            self.open_lifelist(lifelist_id, name)

            dialog.destroy()

        create_btn = ctk.CTkButton(
            dialog,
            text="Create Lifelist",
            command=create_lifelist
        )
        create_btn.pack(pady=15)

    def open_lifelist(self, lifelist_id, lifelist_name):
        self.current_lifelist_id = lifelist_id
        self.current_observation_id = None

        # Update sidebar to show export option
        self.setup_sidebar()

        # Clear the content area
        for widget in self.content.winfo_children():
            widget.destroy()

        # Create lifelist view
        self.lifelist_frame = ctk.CTkFrame(self.content)
        self.lifelist_frame.pack(fill=tk.BOTH, expand=True)

        # Header with lifelist name and add observation button
        header_frame = ctk.CTkFrame(self.lifelist_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        title_label = ctk.CTkLabel(
            header_frame,
            text=lifelist_name,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(side=tk.LEFT, padx=10)

        # Add the map button
        map_btn = ctk.CTkButton(
            header_frame,
            text="View Map",
            command=self.view_map
        )
        map_btn.pack(side=tk.RIGHT, padx=5)

        add_btn = ctk.CTkButton(
            header_frame,
            text="Add Observation",
            command=lambda: self.show_observation_form()
        )
        add_btn.pack(side=tk.RIGHT, padx=5)

        # Search and filter section
        filter_frame = ctk.CTkFrame(self.lifelist_frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Search box
        search_var = tk.StringVar()
        search_label = ctk.CTkLabel(filter_frame, text="Search:")
        search_label.pack(side=tk.LEFT, padx=5)

        search_entry = ctk.CTkEntry(filter_frame, textvariable=search_var, width=200)
        search_entry.pack(side=tk.LEFT, padx=5)

        # Tier filter
        tier_label = ctk.CTkLabel(filter_frame, text="Tier:")
        tier_label.pack(side=tk.LEFT, padx=(15, 5))

        tiers = ["All"] + self.db.get_all_tiers(lifelist_id)
        tier_var = tk.StringVar(value="All")
        tier_dropdown = ctk.CTkComboBox(filter_frame, values=tiers, variable=tier_var)
        tier_dropdown.pack(side=tk.LEFT, padx=5)

        # Tag filter (multiselect)
        self.selected_tag_ids = []

        tag_label = ctk.CTkLabel(filter_frame, text="Tags:")
        tag_label.pack(side=tk.LEFT, padx=(15, 5))

        tag_btn = ctk.CTkButton(
            filter_frame,
            text="Select Tags",
            command=self.show_tag_filter_dialog
        )
        tag_btn.pack(side=tk.LEFT, padx=5)

        # Clear filters button
        clear_btn = ctk.CTkButton(
            filter_frame,
            text="Clear Filters",
            command=lambda: self.clear_filters(search_var, tier_var)
        )
        clear_btn.pack(side=tk.RIGHT, padx=5)

        # Apply filters button
        apply_btn = ctk.CTkButton(
            filter_frame,
            text="Apply Filters",
            command=lambda: self.apply_filters(search_var.get(), tier_var.get())
        )
        apply_btn.pack(side=tk.RIGHT, padx=5)

        # Observation list
        list_frame = ctk.CTkFrame(self.lifelist_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollable frame for observations
        self.observation_list_canvas = tk.Canvas(list_frame, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(list_frame, orientation="vertical", command=self.observation_list_canvas.yview)
        self.observation_list_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.observation_list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.observations_container = ctk.CTkFrame(self.observation_list_canvas)
        self.observation_list_canvas.create_window((0, 0), window=self.observations_container, anchor="nw")

        self.observations_container.bind("<Configure>", self.on_frame_configure)
        self.observation_list_canvas.bind("<Configure>", self.on_canvas_configure)

        # Header for the list
        header = ctk.CTkFrame(self.observations_container)
        header.pack(fill=tk.X, padx=5, pady=5)

        ctk.CTkLabel(header, text="Species", width=200).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Date", width=100).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Location", width=200).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Tier", width=100).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Actions", width=100).pack(side=tk.LEFT, padx=5)

        # Load observations
        self.load_observations()

    def on_frame_configure(self, event):
        self.observation_list_canvas.configure(scrollregion=self.observation_list_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.observation_list_canvas.itemconfig("win", width=event.width)

    def load_observations(self, search_term=None, tier=None):
        # Clear existing observation items
        for widget in self.observations_container.winfo_children()[1:]:  # Skip the header
            widget.destroy()

        # Get filtered observations
        if tier == "All":
            tier = None

        observations = self.db.get_observations(
            self.current_lifelist_id,
            tier=tier,
            tag_ids=self.selected_tag_ids if self.selected_tag_ids else None,
            search_term=search_term
        )

        if not observations:
            no_results = ctk.CTkLabel(
                self.observations_container,
                text="No observations found",
                font=ctk.CTkFont(size=14)
            )
            no_results.pack(pady=20)
            return

        # Group observations by species
        species_groups = {}
        for obs in observations:
            obs_id, species_name, obs_date, location, tier = obs

            # If we haven't seen this species yet, create a new entry
            if species_name not in species_groups:
                species_groups[species_name] = {
                    "latest_id": obs_id,
                    "date": obs_date,
                    "location": location,
                    "tier": tier,
                    "observation_ids": [obs_id]
                }
            else:
                # Add this observation ID to the list
                species_groups[species_name]["observation_ids"].append(obs_id)

                # Update date if this observation is more recent
                if not species_groups[species_name]["date"] or (obs_date and (
                        not species_groups[species_name]["date"] or obs_date > species_groups[species_name]["date"])):
                    species_groups[species_name]["date"] = obs_date
                    species_groups[species_name]["location"] = location
                    species_groups[species_name]["latest_id"] = obs_id

                # Update tier if this tier is "higher" in precedence
                # Tier precedence: wild > assisted > captive > dead > evidence
                tier_precedence = {"wild": 5, "assisted": 4, "captive": 3, "dead": 2, "evidence": 1}
                current_tier_value = tier_precedence.get(species_groups[species_name]["tier"], 0)
                new_tier_value = tier_precedence.get(tier, 0)

                if new_tier_value > current_tier_value:
                    species_groups[species_name]["tier"] = tier

        # Add each species group to the list
        for species_name, data in species_groups.items():
            obs_id = data["latest_id"]
            obs_date = data["date"]
            location = data["location"]
            tier = data["tier"]
            observation_count = len(data["observation_ids"])

            item = ctk.CTkFrame(self.observations_container)
            item.pack(fill=tk.X, padx=5, pady=2)

            # Try to get the primary photo for this species
            photo_thumbnail = None
            all_photos = []

            # Collect all photos from all observations of this species
            for obs_id in data["observation_ids"]:
                photos = self.db.get_photos(obs_id)
                all_photos.extend(photos)

                # Find the primary photo for this species
                primary_photo = self.db.get_primary_photo_for_species(self.current_lifelist_id, species_name)
                photo_thumbnail = None

                if primary_photo:
                    thumbnail = PhotoUtils.resize_image_for_thumbnail(primary_photo[1])
                    if thumbnail:
                        photo_thumbnail = thumbnail

                # If no primary photo found but all_photos exist, use the first one (fallback)
                if not photo_thumbnail and all_photos:
                    thumbnail = PhotoUtils.resize_image_for_thumbnail(all_photos[0][1])
                    if thumbnail:
                        photo_thumbnail = thumbnail

            # Species name (with thumbnail if available)
            species_frame = ctk.CTkFrame(item)
            species_frame.pack(side=tk.LEFT, padx=5, fill=tk.Y)

            if photo_thumbnail:
                thumbnail_label = ctk.CTkLabel(species_frame, text="", image=photo_thumbnail)
                thumbnail_label.pack(side=tk.LEFT, padx=5)
                thumbnail_label.image = photo_thumbnail  # Keep a reference

            # Add observation count to species name if there are multiple observations
            display_name = species_name
            if observation_count > 1:
                display_name = f"{species_name} ({observation_count} observations)"

            species_label = ctk.CTkLabel(species_frame, text=display_name, width=180)
            species_label.pack(side=tk.LEFT, padx=5)

            # Other fields
            date_label = ctk.CTkLabel(item, text=obs_date or "N/A", width=100)
            date_label.pack(side=tk.LEFT, padx=5)

            location_label = ctk.CTkLabel(item, text=location or "N/A", width=200)
            location_label.pack(side=tk.LEFT, padx=5)

            tier_label = ctk.CTkLabel(item, text=tier or "N/A", width=100)
            tier_label.pack(side=tk.LEFT, padx=5)

            # Action buttons
            actions_frame = ctk.CTkFrame(item)
            actions_frame.pack(side=tk.LEFT, padx=5)

            # If multiple observations, add a button to view all observations
            if observation_count > 1:
                view_all_btn = ctk.CTkButton(
                    actions_frame,
                    text="View All",
                    width=70,
                    command=lambda obs_ids=data["observation_ids"], name=species_name:
                    self.view_species_observations(obs_ids, name)
                )
                view_all_btn.pack(side=tk.LEFT, padx=2)
            else:
                # For single observations, keep the normal view button
                view_btn = ctk.CTkButton(
                    actions_frame,
                    text="View",
                    width=70,
                    command=lambda o_id=data["latest_id"]: self.view_observation(o_id)
                )
                view_btn.pack(side=tk.LEFT, padx=2)

            # Add button to add a new observation of this species
            add_btn = ctk.CTkButton(
                actions_frame,
                text="Add New",
                width=70,
                command=lambda species=species_name: self.add_new_observation_of_species(species)
            )
            add_btn.pack(side=tk.LEFT, padx=2)

    def view_species_observations(self, observation_ids, species_name):
        """Show a list of all observations for a specific species"""
        # Clear the content area
        for widget in self.content.winfo_children():
            widget.destroy()

        # Create container
        container = ctk.CTkFrame(self.content)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header
        header_frame = ctk.CTkFrame(container)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        title_label = ctk.CTkLabel(
            header_frame,
            text=f"All Observations of {species_name}",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(side=tk.LEFT, padx=10)

        back_btn = ctk.CTkButton(
            header_frame,
            text="Back to Lifelist",
            command=lambda: self.open_lifelist(self.current_lifelist_id, self.get_lifelist_name())
        )
        back_btn.pack(side=tk.RIGHT, padx=5)

        add_btn = ctk.CTkButton(
            header_frame,
            text="Add Observation",
            command=lambda: self.add_new_observation_of_species(species_name)
        )
        add_btn.pack(side=tk.RIGHT, padx=5)

        # List frame
        list_frame = ctk.CTkFrame(container)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollable frame for observations
        list_canvas = tk.Canvas(list_frame, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(list_frame, orientation="vertical", command=list_canvas.yview)
        list_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        observations_container = ctk.CTkFrame(list_canvas)
        list_canvas.create_window((0, 0), window=observations_container, anchor="nw")

        observations_container.bind("<Configure>",
                                    lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))
        list_canvas.bind("<Configure>", lambda e: list_canvas.itemconfig("win", width=e.width))

        # Header for the list
        header = ctk.CTkFrame(observations_container)
        header.pack(fill=tk.X, padx=5, pady=5)

        ctk.CTkLabel(header, text="Date", width=100).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Location", width=200).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Tier", width=100).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Actions", width=150).pack(side=tk.LEFT, padx=5)

        # Add each observation
        for obs_id in observation_ids:
            observation = self.db.get_observation_details(obs_id)[0]
            if not observation:
                continue

            _, _, _, obs_date, location, _, _, tier, _ = observation

            item = ctk.CTkFrame(observations_container)
            item.pack(fill=tk.X, padx=5, pady=2)

            date_label = ctk.CTkLabel(item, text=obs_date or "N/A", width=100)
            date_label.pack(side=tk.LEFT, padx=5)

            location_label = ctk.CTkLabel(item, text=location or "N/A", width=200)
            location_label.pack(side=tk.LEFT, padx=5)

            tier_label = ctk.CTkLabel(item, text=tier or "N/A", width=100)
            tier_label.pack(side=tk.LEFT, padx=5)

            # Action buttons
            actions_frame = ctk.CTkFrame(item)
            actions_frame.pack(side=tk.LEFT, padx=5)

            view_btn = ctk.CTkButton(
                actions_frame,
                text="View",
                width=70,
                command=lambda o_id=obs_id: self.view_observation(o_id)
            )
            view_btn.pack(side=tk.LEFT, padx=2)

            edit_btn = ctk.CTkButton(
                actions_frame,
                text="Edit",
                width=70,
                command=lambda o_id=obs_id: self.show_observation_form(o_id)
            )
            edit_btn.pack(side=tk.LEFT, padx=2)

    def add_new_observation_of_species(self, species_name):
        """Open the observation form with the species name pre-filled"""
        self.current_observation_id = None  # New observation

        # Clear the content area and create the form exactly like show_observation_form does
        # but pre-fill the species name
        self.show_observation_form()

        # After show_observation_form has created the form, find the species entry and set its value
        # This is a bit of a hack, but CustomTkinter doesn't have a clear way to modify widgets after creation

        # Find the species entry field in the form
        for widget in self.content.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Canvas):
                        for form_frame in child.winfo_children():
                            for frame in form_frame.winfo_children():
                                if isinstance(frame, ctk.CTkFrame):
                                    for field_frame in frame.winfo_children():
                                        if isinstance(field_frame, ctk.CTkFrame):
                                            for label in field_frame.winfo_children():
                                                if isinstance(label, ctk.CTkLabel) and label.cget(
                                                        "text") == "Species Name:":
                                                    # Found the species name label, now find the entry field
                                                    for entry in field_frame.winfo_children():
                                                        if isinstance(entry, ctk.CTkEntry):
                                                            # Set the species name
                                                            entry.delete(0, tk.END)
                                                            entry.insert(0, species_name)
                                                            return

    def apply_filters(self, search_term, tier):
        self.load_observations(
            search_term=search_term if search_term else None,
            tier=tier
        )

    def clear_filters(self, search_var, tier_var):
        search_var.set("")
        tier_var.set("All")
        self.selected_tag_ids = []
        self.load_observations()

    def show_tag_filter_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Select Tags")
        dialog.geometry("300x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        # Get all tags
        all_tags = self.db.get_all_tags()

        # Selected tags
        selected_tags = set(self.selected_tag_ids)

        ctk.CTkLabel(dialog, text="Select Tags to Filter By:", font=ctk.CTkFont(weight="bold")).pack(pady=10)

        # Scrollable frame for tags
        scroll_frame = ctk.CTkScrollableFrame(dialog)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tag checkboxes
        tag_vars = {}

        for tag_id, tag_name in all_tags:
            var = tk.BooleanVar(value=tag_id in selected_tags)
            tag_vars[tag_id] = var

            checkbox = ctk.CTkCheckBox(
                scroll_frame,
                text=tag_name,
                variable=var
            )
            checkbox.pack(anchor="w", pady=2)

        # Apply button
        def apply_tag_filter():
            selected = [tag_id for tag_id, var in tag_vars.items() if var.get()]
            self.selected_tag_ids = selected
            self.load_observations()
            dialog.destroy()

        apply_btn = ctk.CTkButton(
            dialog,
            text="Apply",
            command=apply_tag_filter
        )
        apply_btn.pack(pady=10)

    def show_observation_form(self, observation_id=None):
        self.current_observation_id = observation_id

        # Clear the content area
        for widget in self.content.winfo_children():
            widget.destroy()

        # Create the form container
        form_container = ctk.CTkFrame(self.content)
        form_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create scroll canvas
        canvas = tk.Canvas(form_container, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(form_container, orientation="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        form_frame = ctk.CTkFrame(canvas)
        canvas.create_window((0, 0), window=form_frame, anchor="nw")

        form_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("win", width=e.width))

        # Form title
        title_text = "Edit Observation" if observation_id else "Add New Observation"
        title_label = ctk.CTkLabel(
            form_frame,
            text=title_text,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=10)

        # Form fields
        form_fields_frame = ctk.CTkFrame(form_frame)
        form_fields_frame.pack(fill=tk.X, padx=20, pady=10)

        # Species field
        species_frame = ctk.CTkFrame(form_fields_frame)
        species_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(species_frame, text="Species Name:", width=150).pack(side=tk.LEFT, padx=5)
        species_entry = ctk.CTkEntry(species_frame, width=300)
        species_entry.pack(side=tk.LEFT, padx=5)

        # Date field
        date_frame = ctk.CTkFrame(form_fields_frame)
        date_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(date_frame, text="Observation Date:", width=150).pack(side=tk.LEFT, padx=5)
        date_entry = ctk.CTkEntry(date_frame, width=300, placeholder_text="YYYY-MM-DD")
        date_entry.pack(side=tk.LEFT, padx=5)

        # Location field
        location_frame = ctk.CTkFrame(form_fields_frame)
        location_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(location_frame, text="Location:", width=150).pack(side=tk.LEFT, padx=5)
        location_entry = ctk.CTkEntry(location_frame, width=300)
        location_entry.pack(side=tk.LEFT, padx=5)

        # Coordinates fields
        coords_frame = ctk.CTkFrame(form_fields_frame)
        coords_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(coords_frame, text="Coordinates:", width=150).pack(side=tk.LEFT, padx=5)

        lat_entry = ctk.CTkEntry(coords_frame, width=145, placeholder_text="Latitude")
        lat_entry.pack(side=tk.LEFT, padx=5)

        lon_entry = ctk.CTkEntry(coords_frame, width=145, placeholder_text="Longitude")
        lon_entry.pack(side=tk.LEFT, padx=5)

        # Tier field
        tier_frame = ctk.CTkFrame(form_fields_frame)
        tier_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(tier_frame, text="Tier:", width=150).pack(side=tk.LEFT, padx=5)

        tier_var = tk.StringVar(value="wild")
        tier_options = ["wild", "captive", "assisted", "dead", "evidence"]

        tier_dropdown = ctk.CTkComboBox(tier_frame, values=tier_options, variable=tier_var, width=300)
        tier_dropdown.pack(side=tk.LEFT, padx=5)

        # Notes field
        notes_frame = ctk.CTkFrame(form_fields_frame)
        notes_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(notes_frame, text="Notes:", width=150).pack(side=tk.LEFT, padx=5, anchor="n")
        notes_text = ctk.CTkTextbox(notes_frame, width=300, height=100)
        notes_text.pack(side=tk.LEFT, padx=5)

        # Custom fields
        custom_fields_label = ctk.CTkLabel(
            form_frame,
            text="Custom Fields",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        custom_fields_label.pack(pady=(20, 5))

        custom_fields_frame = ctk.CTkFrame(form_frame)
        custom_fields_frame.pack(fill=tk.X, padx=20, pady=5)

        # Get custom fields for this lifelist
        custom_fields = self.db.get_custom_fields(self.current_lifelist_id)
        custom_field_entries = {}

        if custom_fields:
            for field_id, field_name, field_type in custom_fields:
                field_frame = ctk.CTkFrame(custom_fields_frame)
                field_frame.pack(fill=tk.X, pady=5)

                ctk.CTkLabel(field_frame, text=f"{field_name}:", width=150).pack(side=tk.LEFT, padx=5)

                if field_type == "text":
                    field_entry = ctk.CTkEntry(field_frame, width=300)
                elif field_type == "number":
                    field_entry = ctk.CTkEntry(field_frame, width=300)
                elif field_type == "date":
                    field_entry = ctk.CTkEntry(field_frame, width=300, placeholder_text="YYYY-MM-DD")
                elif field_type == "boolean":
                    field_entry = ctk.CTkCheckBox(field_frame, text="")
                else:
                    field_entry = ctk.CTkEntry(field_frame, width=300)

                field_entry.pack(side=tk.LEFT, padx=5)
                custom_field_entries[field_id] = field_entry
        else:
            no_fields_label = ctk.CTkLabel(
                custom_fields_frame,
                text="No custom fields defined for this lifelist"
            )
            no_fields_label.pack(pady=10)

        # Tags section
        tags_label = ctk.CTkLabel(
            form_frame,
            text="Tags",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        tags_label.pack(pady=(20, 5))

        tags_frame = ctk.CTkFrame(form_frame)
        tags_frame.pack(fill=tk.X, padx=20, pady=5)

        # Tag entry and add button
        tag_entry_frame = ctk.CTkFrame(tags_frame)
        tag_entry_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(tag_entry_frame, text="Add Tag:", width=150).pack(side=tk.LEFT, padx=5)
        tag_entry = ctk.CTkEntry(tag_entry_frame, width=200)
        tag_entry.pack(side=tk.LEFT, padx=5)

        # List to store the current tags
        current_tags = []
        tag_labels_frame = ctk.CTkFrame(tags_frame)
        tag_labels_frame.pack(fill=tk.X, pady=5)

        def add_tag():
            tag_name = tag_entry.get().strip()
            if tag_name and tag_name not in current_tags:
                current_tags.append(tag_name)
                tag_entry.delete(0, tk.END)
                update_tag_display()

        def remove_tag(tag_name):
            current_tags.remove(tag_name)
            update_tag_display()

        def update_tag_display():
            # Clear existing tags
            for widget in tag_labels_frame.winfo_children():
                widget.destroy()

            # Add tag labels
            for tag_name in current_tags:
                tag_label_frame = ctk.CTkFrame(tag_labels_frame)
                tag_label_frame.pack(side=tk.LEFT, padx=2, pady=2)

                tag_label = ctk.CTkLabel(tag_label_frame, text=tag_name, padx=5)
                tag_label.pack(side=tk.LEFT)

                remove_btn = ctk.CTkButton(
                    tag_label_frame,
                    text="✕",
                    width=20,
                    height=20,
                    command=lambda t=tag_name: remove_tag(t)
                )
                remove_btn.pack(side=tk.LEFT)

        add_tag_btn = ctk.CTkButton(
            tag_entry_frame,
            text="Add",
            width=80,
            command=add_tag
        )
        add_tag_btn.pack(side=tk.LEFT, padx=5)

        # Photos section
        photos_label = ctk.CTkLabel(
            form_frame,
            text="Photos",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        photos_label.pack(pady=(20, 5))

        photos_frame = ctk.CTkFrame(form_frame)
        photos_frame.pack(fill=tk.X, padx=20, pady=5)

        # List to store photos
        photos = []

        def add_photos():
            filetypes = [
                ("Image files", "*.jpg *.jpeg *.png *.gif *.bmp *.tif *.tiff")
            ]
            file_paths = filedialog.askopenfilenames(
                title="Select Photos",
                filetypes=filetypes
            )

            if file_paths:
                for path in file_paths:
                    # Ensure the path is not already in the list
                    if not any(p["path"] == path for p in photos):
                        # Extract EXIF data if available
                        lat, lon, taken_date = PhotoUtils.extract_exif_data(path)

                        # Create thumbnail
                        thumbnail = PhotoUtils.resize_image_for_thumbnail(path)

                        # Add to photos list
                        photos.append({
                            "path": path,
                            "is_primary": len(photos) == 0,  # First photo is primary by default
                            "thumbnail": thumbnail,
                            "latitude": lat,
                            "longitude": lon,
                            "taken_date": taken_date
                        })

                update_photos_display()

        def set_primary_photo(index):
            for i in range(len(photos)):
                photos[i]["is_primary"] = (i == index)
            update_photos_display()

            # Show info about species-level changes
            messagebox.showinfo(
                "Primary Photo Set",
                "This photo will be set as the primary photo for all observations of this species when saved."
            )

        def remove_photo(index):
            photos.pop(index)
            # If we removed the primary photo, set a new one
            if not any(p["is_primary"] for p in photos) and photos:
                photos[0]["is_primary"] = True
            update_photos_display()

        def update_photos_display():
            # Clear existing photos
            for widget in photos_display_frame.winfo_children():
                widget.destroy()

            # Add photo thumbnails
            for i, photo in enumerate(photos):
                photo_frame = ctk.CTkFrame(photos_display_frame)
                photo_frame.pack(side=tk.LEFT, padx=5, pady=5)

                if photo["thumbnail"]:
                    thumbnail_label = ctk.CTkLabel(photo_frame, text="", image=photo["thumbnail"])
                    thumbnail_label.pack(padx=5, pady=5)
                    thumbnail_label.image = photo["thumbnail"]  # Keep a reference
                else:
                    thumbnail_label = ctk.CTkLabel(photo_frame, text="No Thumbnail")
                    thumbnail_label.pack(padx=5, pady=5)

                # Primary photo indicator/setter
                primary_var = tk.BooleanVar(value=photo["is_primary"])
                primary_check = ctk.CTkCheckBox(
                    photo_frame,
                    text="Primary",
                    variable=primary_var,
                    command=lambda idx=i: set_primary_photo(idx)
                )
                primary_check.pack(padx=5, pady=2)

                # Remove button
                remove_btn = ctk.CTkButton(
                    photo_frame,
                    text="Remove",
                    width=80,
                    fg_color="red3",
                    hover_color="red4",
                    command=lambda idx=i: remove_photo(idx)
                )
                remove_btn.pack(padx=5, pady=2)

        # Add photos button
        add_photos_btn = ctk.CTkButton(
            photos_frame,
            text="Add Photos",
            command=add_photos
        )
        add_photos_btn.pack(pady=10)

        # Photos display area
        photos_display_frame = ctk.CTkFrame(photos_frame)
        photos_display_frame.pack(fill=tk.X, pady=5)

        # Buttons frame
        buttons_frame = ctk.CTkFrame(form_frame)
        buttons_frame.pack(fill=tk.X, padx=20, pady=20)

        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            fg_color="gray40",
            hover_color="gray30",
            command=lambda: self.open_lifelist(self.current_lifelist_id, self.get_lifelist_name())
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # If editing an existing observation, add a delete button
        if observation_id:
            delete_btn = ctk.CTkButton(
                buttons_frame,
                text="Delete Observation",
                fg_color="red3",
                hover_color="red4",
                command=self.delete_current_observation
            )
            delete_btn.pack(side=tk.LEFT, padx=5)

        # Helper function to validate form fields
        def validate_fields():
            species = species_entry.get().strip()
            if not species:
                messagebox.showerror("Error", "Species name is required")
                return False
            return True

        # Save function
        def save_observation():
            if not validate_fields():
                return

            # Get basic fields
            species = species_entry.get().strip()
            observation_date = date_entry.get().strip() or None
            location = location_entry.get().strip() or None
            latitude = lat_entry.get().strip() or None
            longitude = lon_entry.get().strip() or None
            tier = tier_var.get()
            notes = notes_text.get("1.0", tk.END).strip() or None

            # Convert latitude/longitude to float if not None
            if latitude:
                try:
                    latitude = float(latitude)
                except ValueError:
                    messagebox.showerror("Error", "Latitude must be a number")
                    return

            if longitude:
                try:
                    longitude = float(longitude)
                except ValueError:
                    messagebox.showerror("Error", "Longitude must be a number")
                    return

            try:
                if observation_id:
                    # Update existing observation
                    success = self.db.update_observation(
                        observation_id,
                        species,
                        observation_date,
                        location,
                        latitude,
                        longitude,
                        tier,
                        notes
                    )

                    if not success:
                        messagebox.showerror("Error", "Failed to update observation")
                        return

                    obs_id = observation_id

                    # For existing observations, get current photos and remove ones that are no longer in the UI
                    current_photos = self.db.get_photos(obs_id)
                    current_photo_ids = set(photo[0] for photo in current_photos)
                    kept_photo_ids = set(photo.get("id") for photo in photos if "id" in photo)

                    # Photos to delete = current photos that aren't in the kept photos list
                    photos_to_delete = current_photo_ids - kept_photo_ids

                    # Delete each photo that was removed
                    for photo_id in photos_to_delete:
                        self.db.delete_photo(photo_id)

                else:
                    # Create new observation
                    obs_id = self.db.add_observation(
                        self.current_lifelist_id,
                        species,
                        observation_date,
                        location,
                        latitude,
                        longitude,
                        tier,
                        notes
                    )

                    if not obs_id:
                        messagebox.showerror("Error", "Failed to add observation")
                        return

                # Save custom field values
                for field_id, field_entry in custom_field_entries.items():
                    if isinstance(field_entry, ctk.CTkCheckBox):
                        value = "1" if field_entry.get() else "0"
                    else:
                        value = field_entry.get().strip()

                    # Delete any existing values
                    self.db.cursor.execute(
                        "DELETE FROM observation_custom_fields WHERE observation_id = ? AND field_id = ?",
                        (obs_id, field_id)
                    )

                    # Insert new value
                    if value:
                        self.db.cursor.execute(
                            "INSERT INTO observation_custom_fields (observation_id, field_id, value) VALUES (?, ?, ?)",
                            (obs_id, field_id, value)
                        )

                # Save tags
                # First, remove all existing tags for this observation
                self.db.cursor.execute(
                    "DELETE FROM observation_tags WHERE observation_id = ?",
                    (obs_id,)
                )

                # Add the current tags
                for tag_name in current_tags:
                    tag_id = self.db.add_tag(tag_name)
                    self.db.add_tag_to_observation(obs_id, tag_id)

                # Save photos
                species_primary_set = False
                for photo in photos:
                    if photo.get("is_primary", False):
                        species_primary_set = True

                    # New or existing photo handling
                    if "id" not in photo:
                        # New photo
                        self.db.add_photo(
                            obs_id,
                            photo["path"],
                            1 if photo["is_primary"] else 0,
                            photo.get("latitude"),
                            photo.get("longitude"),
                            photo.get("taken_date")
                        )
                    else:
                        # Update existing photo's primary status if needed
                        if photo["is_primary"]:
                            self.db.set_primary_photo(photo["id"], obs_id)

                # Provide feedback only once if any photo was set as primary
                if species_primary_set:
                    messagebox.showinfo(
                        "Primary Photo Updated",
                        "The selected primary photo will now appear for all observations of this species."
                    )

                self.db.conn.commit()

                # Reload the lifelist view
                self.open_lifelist(self.current_lifelist_id, self.get_lifelist_name())

            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")

        save_btn = ctk.CTkButton(
            buttons_frame,
            text="Save",
            command=save_observation
        )
        save_btn.pack(side=tk.RIGHT, padx=5)

        # If editing an existing observation, load its data
        if observation_id:
            observation, custom_field_values, obs_tags = self.db.get_observation_details(observation_id)

            if observation:
                species_entry.insert(0, observation[2] or "")  # species_name
                if observation[3]:  # observation_date
                    date_entry.insert(0, observation[3])
                if observation[4]:  # location
                    location_entry.insert(0, observation[4])
                if observation[5]:  # latitude
                    lat_entry.insert(0, str(observation[5]))
                if observation[6]:  # longitude
                    lon_entry.insert(0, str(observation[6]))
                if observation[7]:  # tier
                    tier_var.set(observation[7])
                if observation[8]:  # notes
                    notes_text.insert("1.0", observation[8])

            # Load custom field values
            if custom_field_values:
                for field_name, field_type, value in custom_field_values:
                    for field_id, entry in custom_field_entries.items():
                        if self.db.cursor.execute(
                                "SELECT field_name FROM custom_fields WHERE id = ?",
                                (field_id,)
                        ).fetchone()[0] == field_name:
                            if field_type == "boolean":
                                entry.select() if value == "1" else entry.deselect()
                            else:
                                entry.insert(0, value or "")

            # Load tags
            if obs_tags:
                for tag_id, tag_name in obs_tags:
                    current_tags.append(tag_name)
                update_tag_display()

            # Load photos
            obs_photos = self.db.get_photos(observation_id)
            for photo in obs_photos:
                photo_id, file_path, is_primary, lat, lon, taken_date = photo

                # Create thumbnail
                thumbnail = PhotoUtils.resize_image_for_thumbnail(file_path)

                # Add to photos list
                photos.append({
                    "id": photo_id,
                    "path": file_path,
                    "is_primary": bool(is_primary),
                    "thumbnail": thumbnail,
                    "latitude": lat,
                    "longitude": lon,
                    "taken_date": taken_date
                })

            update_photos_display()

    def view_observation(self, observation_id):
        self.current_observation_id = observation_id

        # Clear the content area
        for widget in self.content.winfo_children():
            widget.destroy()

        # Create the detail container
        detail_container = ctk.CTkFrame(self.content)
        detail_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create scroll canvas
        canvas = tk.Canvas(detail_container, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(detail_container, orientation="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        detail_frame = ctk.CTkFrame(canvas)
        canvas.create_window((0, 0), window=detail_frame, anchor="nw")

        detail_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("win", width=e.width))

        # Load observation details
        observation, custom_fields, tags = self.db.get_observation_details(observation_id)

        if not observation:
            error_label = ctk.CTkLabel(
                detail_frame,
                text="Observation not found",
                font=ctk.CTkFont(size=16)
            )
            error_label.pack(pady=20)

            back_btn = ctk.CTkButton(
                detail_frame,
                text="Back to Lifelist",
                command=lambda: self.open_lifelist(self.current_lifelist_id, self.get_lifelist_name())
            )
            back_btn.pack(pady=10)
            return

        # Photos carousel at the top
        photos = self.db.get_photos(observation_id)

        if photos:
            photos_frame = ctk.CTkFrame(detail_frame)
            photos_frame.pack(fill=tk.X, padx=20, pady=10)

            # Show primary photo larger, with small thumbnails below
            primary_photo = None
            for photo in photos:
                if photo[2]:  # is_primary
                    primary_photo = photo
                    break

            if not primary_photo and photos:
                primary_photo = photos[0]

            if primary_photo:
                try:
                    img = Image.open(primary_photo[1])
                    img.thumbnail((600, 400))  # Resize while maintaining aspect ratio
                    photo_img = ImageTk.PhotoImage(img)

                    photo_label = ctk.CTkLabel(photos_frame, text="", image=photo_img)
                    photo_label.pack(pady=10)
                    photo_label.image = photo_img  # Keep a reference
                except Exception as e:
                    print(f"Error loading primary photo: {e}")

            # Thumbnails row
            thumbnails_frame = ctk.CTkFrame(photos_frame)
            thumbnails_frame.pack(fill=tk.X, pady=10)

            for photo in photos:
                try:
                    thumbnail = PhotoUtils.resize_image_for_thumbnail(photo[1], size=(80, 80))
                    if thumbnail:
                        thumb_frame = ctk.CTkFrame(thumbnails_frame)
                        thumb_frame.pack(side=tk.LEFT, padx=5)

                        thumb_label = ctk.CTkLabel(thumb_frame, text="", image=thumbnail)
                        thumb_label.pack(padx=5, pady=5)
                        thumb_label.image = thumbnail  # Keep a reference

                        # Add a primary indicator if this is the primary photo
                        if photo[2]:  # is_primary
                            primary_label = ctk.CTkLabel(thumb_frame, text="Primary", font=ctk.CTkFont(size=10))
                            primary_label.pack(pady=2)
                except Exception as e:
                    print(f"Error creating thumbnail: {e}")

        # Header with species name
        species_name = observation[2]
        title_label = ctk.CTkLabel(
            detail_frame,
            text=species_name,
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=15)

        # Details section
        details_frame = ctk.CTkFrame(detail_frame)
        details_frame.pack(fill=tk.X, padx=20, pady=10)

        # Observation details
        details_grid = ctk.CTkFrame(details_frame)
        details_grid.pack(fill=tk.X, pady=10)

        # Date
        date_frame = ctk.CTkFrame(details_grid)
        date_frame.pack(fill=tk.X, pady=2)

        ctk.CTkLabel(date_frame, text="Date:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(date_frame, text=observation[3] or "Not recorded").pack(side=tk.LEFT, padx=5)

        # Location
        location_frame = ctk.CTkFrame(details_grid)
        location_frame.pack(fill=tk.X, pady=2)

        ctk.CTkLabel(location_frame, text="Location:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT,
                                                                                                        padx=5)
        ctk.CTkLabel(location_frame, text=observation[4] or "Not recorded").pack(side=tk.LEFT, padx=5)

        # Coordinates
        if observation[5] and observation[6]:  # latitude and longitude
            coords_frame = ctk.CTkFrame(details_grid)
            coords_frame.pack(fill=tk.X, pady=2)

            ctk.CTkLabel(coords_frame, text="Coordinates:", width=150, font=ctk.CTkFont(weight="bold")).pack(
                side=tk.LEFT, padx=5)
            coord_text = f"{observation[5]}, {observation[6]}"
            ctk.CTkLabel(coords_frame, text=coord_text).pack(side=tk.LEFT, padx=5)

        # Tier
        tier_frame = ctk.CTkFrame(details_grid)
        tier_frame.pack(fill=tk.X, pady=2)

        ctk.CTkLabel(tier_frame, text="Tier:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(tier_frame, text=observation[7] or "Not specified").pack(side=tk.LEFT, padx=5)

        # Notes (if any)
        if observation[8]:
            notes_frame = ctk.CTkFrame(details_grid)
            notes_frame.pack(fill=tk.X, pady=5)

            ctk.CTkLabel(notes_frame, text="Notes:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT,
                                                                                                      padx=5,
                                                                                                      anchor="n")

            notes_text = ctk.CTkTextbox(notes_frame, width=400, height=100)
            notes_text.pack(side=tk.LEFT, padx=5, pady=5)
            notes_text.insert("1.0", observation[8])
            notes_text.configure(state="disabled")  # Make it read-only

        # Custom fields
        if custom_fields:
            custom_fields_label = ctk.CTkLabel(
                detail_frame,
                text="Custom Fields",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            custom_fields_label.pack(pady=(20, 5))

            custom_fields_frame = ctk.CTkFrame(detail_frame)
            custom_fields_frame.pack(fill=tk.X, padx=20, pady=5)

            for field_name, field_type, value in custom_fields:
                field_frame = ctk.CTkFrame(custom_fields_frame)
                field_frame.pack(fill=tk.X, pady=2)

                ctk.CTkLabel(field_frame, text=f"{field_name}:", width=150, font=ctk.CTkFont(weight="bold")).pack(
                    side=tk.LEFT, padx=5)

                # Format the value based on field type
                if field_type == "boolean":
                    display_value = "Yes" if value == "1" else "No"
                else:
                    display_value = value or "Not specified"

                ctk.CTkLabel(field_frame, text=display_value).pack(side=tk.LEFT, padx=5)

        # Tags
        if tags:
            tags_label = ctk.CTkLabel(
                detail_frame,
                text="Tags",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            tags_label.pack(pady=(20, 5))

            tags_frame = ctk.CTkFrame(detail_frame)
            tags_frame.pack(fill=tk.X, padx=20, pady=5)

            for tag_id, tag_name in tags:
                tag_label = ctk.CTkLabel(
                    tags_frame,
                    text=tag_name,
                    fg_color="gray30",
                    corner_radius=10,
                    padx=10,
                    pady=5
                )
                tag_label.pack(side=tk.LEFT, padx=5, pady=5)

        # Action buttons
        buttons_frame = ctk.CTkFrame(detail_frame)
        buttons_frame.pack(fill=tk.X, padx=20, pady=20)

        back_btn = ctk.CTkButton(
            buttons_frame,
            text="Back to Lifelist",
            command=lambda: self.open_lifelist(self.current_lifelist_id, self.get_lifelist_name())
        )
        back_btn.pack(side=tk.LEFT, padx=5)

        edit_btn = ctk.CTkButton(
            buttons_frame,
            text="Edit Observation",
            command=lambda: self.show_observation_form(observation_id)
        )
        edit_btn.pack(side=tk.RIGHT, padx=5)

    def view_map(self):
        if not self.current_lifelist_id:
            return

        # Get all observations for this lifelist
        observations = self.db.get_observations(self.current_lifelist_id)

        if not observations:
            messagebox.showinfo("Map View", "No observations to display on the map")
            return

        # Create a temporary file for the map
        import tempfile
        map_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        map_file.close()

        # Generate the map
        result = MapGenerator.create_observation_map(observations, self.db, map_file.name)

        if isinstance(result, tuple) and len(result) == 2:
            map_path, message = result

            if map_path:
                # Map was created successfully
                messagebox.showinfo("Map Created", message)
                webbrowser.open('file://' + os.path.realpath(map_path))
            else:
                # Map creation failed
                messagebox.showinfo("Map Creation Failed",
                                    f"Could not create map: {message}\n\n"
                                    "To fix this issue:\n"
                                    "1. Add latitude/longitude data to your observations, or\n"
                                    "2. Upload photos that contain GPS information in their EXIF data")
        else:
            messagebox.showerror("Error", "An unexpected error occurred while creating the map")

    def get_lifelist_name(self):
        if not self.current_lifelist_id:
            return ""

        self.db.cursor.execute("SELECT name FROM lifelists WHERE id = ?", (self.current_lifelist_id,))
        result = self.db.cursor.fetchone()

        if result:
            return result[0]
        return ""

    def delete_current_observation(self):
        if not self.current_observation_id:
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this observation? This action cannot be undone."
        )

        if confirm:
            success, photos = self.db.delete_observation(self.current_observation_id)

            if success:
                # Return to the lifelist view
                self.open_lifelist(self.current_lifelist_id, self.get_lifelist_name())
            else:
                messagebox.showerror("Error", "Failed to delete the observation")

    def delete_current_lifelist(self):
        if not self.current_lifelist_id:
            return

        lifelist_name = self.get_lifelist_name()

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the lifelist '{lifelist_name}'? This will delete all observations and cannot be undone."
        )

        if confirm:
            # First offer to export
            export_first = messagebox.askyesno(
                "Export First?",
                "Would you like to export this lifelist before deleting it?"
            )

            if export_first:
                self.export_lifelist()

            success = self.db.delete_lifelist(self.current_lifelist_id)

            if success:
                messagebox.showinfo("Success", f"Lifelist '{lifelist_name}' has been deleted")
                self.current_lifelist_id = None
                self.current_observation_id = None
                self.setup_sidebar()

                # Show welcome screen
                for widget in self.content.winfo_children():
                    widget.destroy()

                welcome_frame = ctk.CTkFrame(self.content)
                welcome_frame.pack(fill=tk.BOTH, expand=True)

                welcome_label = ctk.CTkLabel(
                    welcome_frame,
                    text="Welcome to Lifelist Manager",
                    font=ctk.CTkFont(size=24, weight="bold")
                )
                welcome_label.pack(pady=20)
            else:
                messagebox.showerror("Error", f"Failed to delete lifelist '{lifelist_name}'")

    def export_lifelist(self):
        if not self.current_lifelist_id:
            return

        lifelist_name = self.get_lifelist_name()

        # Ask for export location
        export_dir = filedialog.askdirectory(
            title=f"Select Export Location for '{lifelist_name}'"
        )

        if not export_dir:
            return

        # Create a directory for this export
        export_path = os.path.join(export_dir, re.sub(r'[^\w\s-]', '', lifelist_name).strip().replace(' ', '_'))
        os.makedirs(export_path, exist_ok=True)

        # Ask if photos should be included
        include_photos = messagebox.askyesno(
            "Export Photos?",
            "Would you like to include photos in the export? This may increase the export size significantly."
        )

        # Export the lifelist
        success = self.db.export_lifelist(self.current_lifelist_id, export_path, include_photos)

        if success:
            messagebox.showinfo(
                "Export Successful",
                f"Lifelist '{lifelist_name}' has been exported to:\n{export_path}"
            )
        else:
            messagebox.showerror("Export Error", f"Failed to export lifelist '{lifelist_name}'")

    def import_lifelist(self):
        # Ask for JSON file
        json_file = filedialog.askopenfilename(
            title="Select Lifelist JSON File",
            filetypes=[("JSON files", "*.json")]
        )

        if not json_file:
            return

        # Check for photos directory
        photos_dir = None
        json_dir = os.path.dirname(json_file)
        potential_photos_dir = os.path.join(json_dir, "photos")

        if os.path.isdir(potential_photos_dir):
            include_photos = messagebox.askyesno(
                "Import Photos?",
                "A 'photos' directory was found. Would you like to include photos in the import?"
            )

            if include_photos:
                photos_dir = potential_photos_dir

        # Import the lifelist
        success, message = self.db.import_lifelist(json_file, photos_dir)

        if success:
            messagebox.showinfo("Import Successful", message)
            # Refresh sidebar
            self.setup_sidebar()
        else:
            messagebox.showerror("Import Error", message)


def main():
    root = ctk.CTk()
    app = LifelistApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()