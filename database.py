"""
Database module - Manages all database operations for the Lifelist Manager
"""
import os
import json
import sqlite3
import shutil

class Database:
    def __init__(self, db_path="lifelists.db"):
        """Initialize database connection and create tables if they don't exist"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def __enter__(self):
        """Support for using as a context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting the context"""
        self.close()
        return False  # Don't suppress exceptions

    def create_tables(self):
        """Create all database tables if they don't exist"""
        # Create tables for lifelists
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS lifelists (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            taxonomy TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create tables for custom fields
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_fields (
            id INTEGER PRIMARY KEY,
            lifelist_id INTEGER,
            field_name TEXT,
            field_type TEXT,
            FOREIGN KEY (lifelist_id) REFERENCES lifelists (id) ON DELETE CASCADE
        )
        ''')

        # Create table for lifelist tiers
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS lifelist_tiers (
            id INTEGER PRIMARY KEY,
            lifelist_id INTEGER,
            tier_name TEXT,
            tier_order INTEGER,
            FOREIGN KEY (lifelist_id) REFERENCES lifelists (id) ON DELETE CASCADE,
            UNIQUE (lifelist_id, tier_name)
        )
        ''')

        # Create table for observations
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

        # Create table for observation custom fields
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

        # Create table for photos
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

        # Create tables for tags
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

        # Create tables for taxonomies
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS taxonomies (
                id INTEGER PRIMARY KEY,
                lifelist_id INTEGER,
                name TEXT,
                version TEXT,
                source TEXT,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lifelist_id) REFERENCES lifelists (id) ON DELETE CASCADE
            )
            ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS taxonomy_entries (
                id INTEGER PRIMARY KEY,
                taxonomy_id INTEGER,
                scientific_name TEXT,
                common_name TEXT,
                family TEXT,
                genus TEXT,
                species TEXT,
                subspecies TEXT,
                order_name TEXT,
                class_name TEXT,
                code TEXT,
                rank TEXT,
                is_custom INTEGER DEFAULT 0,
                additional_data TEXT,  -- JSON field for flexible storage
                FOREIGN KEY (taxonomy_id) REFERENCES taxonomies (id) ON DELETE CASCADE
            )
            ''')

        # Create indices for fast lookup
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_taxonomy_scientific ON taxonomy_entries (taxonomy_id, scientific_name)')
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_taxonomy_common ON taxonomy_entries (taxonomy_id, common_name)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_taxonomy_family ON taxonomy_entries (taxonomy_id, family)')

        self.conn.commit()

    # Lifelist methods
    def create_lifelist(self, name, taxonomy=None):
        """Create a new lifelist"""
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
        """Get all lifelists"""
        self.cursor.execute("SELECT id, name, taxonomy FROM lifelists ORDER BY name")
        return self.cursor.fetchall()

    def delete_lifelist(self, lifelist_id):
        """Delete a lifelist by ID"""
        # First, get the lifelist data for potential export
        self.cursor.execute("SELECT name FROM lifelists WHERE id = ?", (lifelist_id,))
        lifelist = self.cursor.fetchone()

        if lifelist:
            self.cursor.execute("DELETE FROM lifelists WHERE id = ?", (lifelist_id,))
            self.conn.commit()
            return True
        return False

    # Custom fields methods
    def add_custom_field(self, lifelist_id, field_name, field_type):
        """Add a custom field to a lifelist"""
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
        """Get all custom fields for a lifelist"""
        self.cursor.execute(
            "SELECT id, field_name, field_type FROM custom_fields WHERE lifelist_id = ?",
            (lifelist_id,)
        )
        return self.cursor.fetchall()

    # Tier methods
    def get_lifelist_tiers(self, lifelist_id):
        """Get custom tiers for a lifelist, or return default tiers if none defined"""
        self.cursor.execute(
            "SELECT tier_name FROM lifelist_tiers WHERE lifelist_id = ? ORDER BY tier_order",
            (lifelist_id,)
        )
        tiers = [row[0] for row in self.cursor.fetchall()]

        # If no custom tiers are defined, return the default ones
        if not tiers:
            return ["wild", "heard", "captive"]

        return tiers

    def set_lifelist_tiers(self, lifelist_id, tiers):
        """Set custom tiers for a lifelist"""
        # First delete any existing tiers for this lifelist
        self.cursor.execute("DELETE FROM lifelist_tiers WHERE lifelist_id = ?", (lifelist_id,))

        # Insert the new tiers
        for i, tier_name in enumerate(tiers):
            self.cursor.execute(
                "INSERT INTO lifelist_tiers (lifelist_id, tier_name, tier_order) VALUES (?, ?, ?)",
                (lifelist_id, tier_name, i)
            )

        self.conn.commit()
        return True

    def get_all_tiers(self, lifelist_id):
        """Get all tiers used in observations for a lifelist along with custom tiers"""
        # Get custom tiers defined for this lifelist
        custom_tiers = self.get_lifelist_tiers(lifelist_id)

        # Get tiers actually used in observations (could include legacy tiers)
        self.cursor.execute(
            "SELECT DISTINCT tier FROM observations WHERE lifelist_id = ?",
            (lifelist_id,)
        )
        used_tiers = [row[0] for row in self.cursor.fetchall()]

        # Combine and deduplicate
        all_tiers = []
        for tier in custom_tiers:
            if tier not in all_tiers:
                all_tiers.append(tier)

        for tier in used_tiers:
            if tier not in all_tiers:
                all_tiers.append(tier)

        return all_tiers

    # Taxonomy methods
    def add_taxonomy(self, lifelist_id, name, version=None, source=None, description=None):
        """Add a new taxonomy to a lifelist"""
        try:
            self.cursor.execute(
                """INSERT INTO taxonomies 
                (lifelist_id, name, version, source, description) 
                VALUES (?, ?, ?, ?, ?)""",
                (lifelist_id, name, version, source, description)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding taxonomy: {e}")
            return None

    def get_taxonomies(self, lifelist_id):
        """Get all taxonomies for a lifelist"""
        self.cursor.execute(
            """SELECT id, name, version, source, description, is_active 
            FROM taxonomies WHERE lifelist_id = ?""",
            (lifelist_id,)
        )
        return self.cursor.fetchall()

    def get_active_taxonomy(self, lifelist_id):
        """Get the active taxonomy for a lifelist"""
        self.cursor.execute(
            """SELECT id, name, version, source, description 
            FROM taxonomies WHERE lifelist_id = ? AND is_active = 1""",
            (lifelist_id,)
        )
        return self.cursor.fetchone()

    def set_active_taxonomy(self, taxonomy_id, lifelist_id):
        """Set a taxonomy as active for a lifelist"""
        try:
            # First, set all taxonomies for this lifelist as inactive
            self.cursor.execute(
                "UPDATE taxonomies SET is_active = 0 WHERE lifelist_id = ?",
                (lifelist_id,)
            )

            # Then set the selected taxonomy as active
            self.cursor.execute(
                "UPDATE taxonomies SET is_active = 1 WHERE id = ?",
                (taxonomy_id,)
            )

            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error setting active taxonomy: {e}")
            return False

    def add_taxonomy_entry(self, taxonomy_id, scientific_name, common_name=None, family=None,
                           genus=None, species=None, subspecies=None, order_name=None,
                           class_name=None, code=None, rank=None, is_custom=0, additional_data=None):
        """Add an entry to a taxonomy"""
        try:
            # Convert additional_data dict to JSON string if provided
            if additional_data and isinstance(additional_data, dict):
                additional_data = json.dumps(additional_data)

            self.cursor.execute(
                """INSERT INTO taxonomy_entries 
                (taxonomy_id, scientific_name, common_name, family, genus, species, 
                subspecies, order_name, class_name, code, rank, is_custom, additional_data) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (taxonomy_id, scientific_name, common_name, family, genus, species,
                 subspecies, order_name, class_name, code, rank, is_custom, additional_data)
            )

            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding taxonomy entry: {e}")
            return None

    def search_taxonomy(self, taxonomy_id, search_term, limit=10):
        """Search for entries in a taxonomy"""
        search_param = f"%{search_term}%"

        self.cursor.execute(
            """SELECT id, scientific_name, common_name, family, genus, species 
            FROM taxonomy_entries 
            WHERE taxonomy_id = ? AND 
            (scientific_name LIKE ? OR common_name LIKE ?)
            ORDER BY 
                CASE WHEN scientific_name LIKE ? THEN 1
                     WHEN common_name LIKE ? THEN 2
                     ELSE 3
                END,
                scientific_name
            LIMIT ?""",
            (taxonomy_id, search_param, search_param, f"{search_term}%", f"{search_term}%", limit)
        )

        return self.cursor.fetchall()

    def import_csv_taxonomy(self, taxonomy_id, csv_file, mapping):
        """Import taxonomy entries from a CSV file using the provided field mapping"""
        try:
            import csv

            # Begin a transaction for better performance
            self.conn.execute("BEGIN TRANSACTION")

            # Track the number of entries added
            count = 0

            # Read the CSV file with context manager
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # Process each row
                for row in reader:
                    # Map CSV fields to database fields using the provided mapping
                    entry_data = {}

                    for db_field, csv_field in mapping.items():
                        if csv_field in row:
                            entry_data[db_field] = row[csv_field]

                    # Check if we have at least a scientific name
                    if 'scientific_name' in entry_data and entry_data['scientific_name']:
                        # Add any unmapped data to the additional_data field
                        additional_data = {}
                        for key, value in row.items():
                            if key not in mapping.values() and value:
                                additional_data[key] = value

                        # Only add additional_data if we have any
                        if additional_data:
                            entry_data['additional_data'] = json.dumps(additional_data)

                        # Add the entry to the database
                        self.cursor.execute(
                            """INSERT INTO taxonomy_entries 
                            (taxonomy_id, scientific_name, common_name, family, genus, species, 
                            subspecies, order_name, class_name, code, rank, is_custom, additional_data) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                taxonomy_id,
                                entry_data.get('scientific_name'),
                                entry_data.get('common_name'),
                                entry_data.get('family'),
                                entry_data.get('genus'),
                                entry_data.get('species'),
                                entry_data.get('subspecies'),
                                entry_data.get('order_name'),
                                entry_data.get('class_name'),
                                entry_data.get('code'),
                                entry_data.get('rank'),
                                0,  # is_custom
                                entry_data.get('additional_data')
                            )
                        )

                        count += 1

            # Commit the transaction
            self.conn.commit()
            return count

        except Exception as e:
            self.conn.rollback()
            print(f"Error importing taxonomy from CSV: {e}")
            return -1

    # Observation methods
    def add_observation(self, lifelist_id, species_name, observation_date=None,
                        location=None, latitude=None, longitude=None, tier="wild", notes=None):
        """Add a new observation"""
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
        """Get observations with optional filtering"""
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

    def get_observation_details(self, observation_id):
        """Get details for a specific observation"""
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
        """Update an existing observation"""
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
        """Delete an observation"""
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

    # Photo methods
    def add_photo(self, observation_id, file_path, is_primary=0, latitude=None, longitude=None, taken_date=None):
        """Add a photo to an observation"""
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
        """Get all photos for an observation"""
        self.cursor.execute(
            "SELECT id, file_path, is_primary, latitude, longitude, taken_date FROM photos WHERE observation_id = ?",
            (observation_id,)
        )
        return self.cursor.fetchall()

    def species_has_primary_photo(self, lifelist_id, species_name):
        """Check if a species already has a primary photo set"""
        query = """
        SELECT COUNT(*) FROM photos p
        JOIN observations o ON p.observation_id = o.id
        WHERE o.lifelist_id = ? AND o.species_name = ? AND p.is_primary = 1
        """
        self.cursor.execute(query, (lifelist_id, species_name))
        count = self.cursor.fetchone()[0]
        return count > 0

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

    def get_species_primary_photo(self, lifelist_id, species_name):
        """Get the primary photo for a species"""
        query = """
        SELECT p.id, p.file_path, p.is_primary, p.latitude, p.longitude, p.taken_date, o.id as observation_id
        FROM photos p
        JOIN observations o ON p.observation_id = o.id
        WHERE o.lifelist_id = ? AND o.species_name = ? AND p.is_primary = 1
        ORDER BY p.id DESC
        LIMIT 1
        """
        self.cursor.execute(query, (lifelist_id, species_name))
        return self.cursor.fetchone()

    def set_primary_photo(self, photo_id, observation_id):
        """Set a photo as the primary photo for a species"""
        try:
            # Get the species name and lifelist_id for this observation
            self.cursor.execute("SELECT species_name, lifelist_id FROM observations WHERE id = ?", (observation_id,))
            result = self.cursor.fetchone()
            if not result:
                return False

            species_name, lifelist_id = result

            # Get all observations for this species
            self.cursor.execute("SELECT id FROM observations WHERE lifelist_id = ? AND species_name = ?",
                                (lifelist_id, species_name))
            all_obs_ids = [row[0] for row in self.cursor.fetchall()]

            # Reset primary flag for all photos of this species
            for obs_id in all_obs_ids:
                self.cursor.execute("UPDATE photos SET is_primary = 0 WHERE observation_id = ?", (obs_id,))

            # Set the selected photo as primary
            self.cursor.execute("UPDATE photos SET is_primary = 1 WHERE id = ?", (photo_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error setting primary photo: {e}")
            return False

    def delete_photo(self, photo_id):
        """Delete a photo"""
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

    # Tag methods
    def add_tag(self, tag_name):
        """Add a tag or get existing tag ID"""
        try:
            self.cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            # Tag already exists, get its ID
            self.cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            return self.cursor.fetchone()[0]

    def get_all_tags(self):
        """Get all tags"""
        self.cursor.execute("SELECT id, name FROM tags ORDER BY name")
        return self.cursor.fetchall()

    def add_tag_to_observation(self, observation_id, tag_id):
        """Add a tag to an observation"""
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
        """Remove a tag from an observation"""
        self.cursor.execute(
            "DELETE FROM observation_tags WHERE observation_id = ? AND tag_id = ?",
            (observation_id, tag_id)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_observation_tags(self, observation_id):
        """Get all tags for an observation"""
        self.cursor.execute(
            """SELECT t.id, t.name FROM tags t
            JOIN observation_tags ot ON t.id = ot.tag_id
            WHERE ot.observation_id = ?""",
            (observation_id,)
        )
        return self.cursor.fetchall()

    # Import/export methods
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
                "tiers": self.get_lifelist_tiers(lifelist_id),
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

            # Write the JSON file using context manager
            with open(os.path.join(export_path, f"{lifelist_data['name']}.json"), 'w') as f:
                json.dump(lifelist_data, f, indent=2)

            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False

    def import_lifelist(self, json_path, photos_dir=None):
        """Import a lifelist from a JSON file"""
        try:
            # Use context manager for file operations
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

            # Import custom tiers if present
            if "tiers" in lifelist_data:
                self.set_lifelist_tiers(lifelist_id, lifelist_data["tiers"])

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
        """Close the database connection"""
        if self.conn:
            self.conn.close()