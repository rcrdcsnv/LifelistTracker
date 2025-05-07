"""
Database module - Manages all database operations for the Lifelist Tracker
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
        # Create lifelist_types table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS lifelist_types (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            icon TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create default lifelist type configurations
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS lifelist_type_configs (
            id INTEGER PRIMARY KEY,
            lifelist_type_id INTEGER,
            config_key TEXT,
            config_value TEXT,
            FOREIGN KEY (lifelist_type_id) REFERENCES lifelist_types (id) ON DELETE CASCADE
        )
        ''')

        # Create default tiers for lifelist types
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS lifelist_type_tiers (
            id INTEGER PRIMARY KEY,
            lifelist_type_id INTEGER,
            tier_name TEXT,
            tier_order INTEGER,
            FOREIGN KEY (lifelist_type_id) REFERENCES lifelist_types (id) ON DELETE CASCADE
        )
        ''')

        # Create tables for lifelists (updated)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS lifelists (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            lifelist_type_id INTEGER,
            classification TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lifelist_type_id) REFERENCES lifelist_types (id)
        )
        ''')

        # Create tables for custom fields (updated with more field types)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_fields (
            id INTEGER PRIMARY KEY,
            lifelist_id INTEGER,
            field_name TEXT,
            field_type TEXT,
            field_options TEXT,
            is_required INTEGER DEFAULT 0,
            display_order INTEGER,
            FOREIGN KEY (lifelist_id) REFERENCES lifelists (id) ON DELETE CASCADE
        )
        ''')

        # Create field options for choice fields
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS field_options (
            id INTEGER PRIMARY KEY,
            field_id INTEGER,
            option_value TEXT,
            option_label TEXT,
            option_order INTEGER,
            FOREIGN KEY (field_id) REFERENCES custom_fields (id) ON DELETE CASCADE
        )
        ''')

        # Create field dependencies
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS field_dependencies (
            id INTEGER PRIMARY KEY,
            field_id INTEGER,
            parent_field_id INTEGER,
            condition_type TEXT,
            condition_value TEXT,
            FOREIGN KEY (field_id) REFERENCES custom_fields (id) ON DELETE CASCADE,
            FOREIGN KEY (parent_field_id) REFERENCES custom_fields (id) ON DELETE CASCADE
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

        # Create table for observations (updated)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY,
            lifelist_id INTEGER,
            entry_name TEXT,
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
            name TEXT UNIQUE NOT NULL,
            category TEXT
        )
        ''')

        # Create hierarchical tags
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS tag_hierarchy (
            id INTEGER PRIMARY KEY,
            tag_id INTEGER,
            parent_tag_id INTEGER,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE,
            FOREIGN KEY (parent_tag_id) REFERENCES tags (id) ON DELETE CASCADE
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

        # Rename taxonomies to classifications
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS classifications (
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

        # Rename taxonomy_entries to classification_entries
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS classification_entries (
                id INTEGER PRIMARY KEY,
                classification_id INTEGER,
                name TEXT,
                alternate_name TEXT,
                parent_id INTEGER,
                category TEXT,
                code TEXT,
                rank TEXT,
                is_custom INTEGER DEFAULT 0,
                additional_data TEXT,
                FOREIGN KEY (classification_id) REFERENCES classifications (id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES classification_entries (id) ON DELETE SET NULL
            )
            ''')

        # Create indices for fast lookup
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_classification_name ON classification_entries (classification_id, name)')
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_classification_alt ON classification_entries (classification_id, alternate_name)')
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_classification_category ON classification_entries (classification_id, category)')

        # Insert predefined lifelist types if they don't exist
        self._initialize_lifelist_types()

        self.conn.commit()

    def _initialize_lifelist_types(self):
        """Initialize predefined lifelist types and their default configurations"""
        # Check if lifelist types already exist
        self.cursor.execute("SELECT COUNT(*) FROM lifelist_types")
        count = self.cursor.fetchone()[0]
        
        if count == 0:
            # Insert predefined lifelist types
            lifelist_types = [
                (1, 'Wildlife', 'For tracking animal observations like birds, mammals, reptiles, etc.'),
                (2, 'Plants', 'For tracking plant observations including wildflowers, trees, fungi, etc.'),
                (3, 'Books', 'Track your reading history and book collection'),
                (4, 'Movies', 'Track movies you have watched'),
                (5, 'Music', 'Track music albums, artists, or concerts'),
                (6, 'Travel', 'Track places you have visited'),
                (7, 'Foods', 'Track culinary experiences and dishes'),
                (8, 'Collectibles', 'Generic collection tracker')
            ]
            
            self.cursor.executemany(
                "INSERT INTO lifelist_types (id, name, description) VALUES (?, ?, ?)",
                lifelist_types
            )
            
            # Default tiers for Wildlife
            wildlife_tiers = [
                (1, 'wild', 1),
                (1, 'heard', 2),
                (1, 'captive', 3)
            ]
            
            self.cursor.executemany(
                "INSERT INTO lifelist_type_tiers (lifelist_type_id, tier_name, tier_order) VALUES (?, ?, ?)",
                wildlife_tiers
            )
            
            # Default tiers for Plants
            plant_tiers = [
                (2, 'wild', 1),
                (2, 'garden', 2),
                (2, 'greenhouse', 3)
            ]
            
            self.cursor.executemany(
                "INSERT INTO lifelist_type_tiers (lifelist_type_id, tier_name, tier_order) VALUES (?, ?, ?)",
                plant_tiers
            )
            
            # Default tiers for Books
            book_tiers = [
                (3, 'read', 1),
                (3, 'currently reading', 2),
                (3, 'want to read', 3),
                (3, 'abandoned', 4)
            ]
            
            self.cursor.executemany(
                "INSERT INTO lifelist_type_tiers (lifelist_type_id, tier_name, tier_order) VALUES (?, ?, ?)",
                book_tiers
            )
            
            # Default tiers for Movies
            movie_tiers = [
                (4, 'watched', 1),
                (4, 'want to watch', 2)
            ]
            
            self.cursor.executemany(
                "INSERT INTO lifelist_type_tiers (lifelist_type_id, tier_name, tier_order) VALUES (?, ?, ?)",
                movie_tiers
            )
            
            # Default tiers for Music
            music_tiers = [
                (5, 'owned', 1),
                (5, 'listened', 2),
                (5, 'live performance', 3)
            ]
            
            self.cursor.executemany(
                "INSERT INTO lifelist_type_tiers (lifelist_type_id, tier_name, tier_order) VALUES (?, ?, ?)",
                music_tiers
            )
            
            # Default tiers for Travel
            travel_tiers = [
                (6, 'visited', 1),
                (6, 'stayed overnight', 2),
                (6, 'want to visit', 3)
            ]
            
            self.cursor.executemany(
                "INSERT INTO lifelist_type_tiers (lifelist_type_id, tier_name, tier_order) VALUES (?, ?, ?)",
                travel_tiers
            )
            
            # Default tiers for Foods
            food_tiers = [
                (7, 'tried', 1),
                (7, 'cooked', 2),
                (7, 'want to try', 3)
            ]
            
            self.cursor.executemany(
                "INSERT INTO lifelist_type_tiers (lifelist_type_id, tier_name, tier_order) VALUES (?, ?, ?)",
                food_tiers
            )
            
            # Default tiers for Collectibles
            collectible_tiers = [
                (8, 'owned', 1),
                (8, 'wanted', 2),
                (8, 'previously owned', 3)
            ]
            
            self.cursor.executemany(
                "INSERT INTO lifelist_type_tiers (lifelist_type_id, tier_name, tier_order) VALUES (?, ?, ?)",
                collectible_tiers
            )
            
            self.conn.commit()

    def execute_transaction(self, operations_func):
        """Execute multiple SQL operations as a single transaction

        Args:
            operations_func: Function that contains database operations to execute

        Returns:
            Any: The result of operations_func execution
        """
        try:
            self.conn.execute("BEGIN TRANSACTION")
            result = operations_func()
            self.conn.commit()
            return result
        except Exception as e:
            self.conn.rollback()
            print(f"Transaction error: {e}")
            raise e

    # Lifelist type methods
    def get_lifelist_types(self):
        """Get all available lifelist types"""
        self.cursor.execute("SELECT id, name, description, icon FROM lifelist_types ORDER BY name")
        return self.cursor.fetchall()

    def get_lifelist_type(self, type_id):
        """Get a specific lifelist type by ID"""
        self.cursor.execute(
            "SELECT id, name, description, icon FROM lifelist_types WHERE id = ?",
            (type_id,)
        )
        return self.cursor.fetchone()

    def get_lifelist_type_by_name(self, type_name):
        """Get a specific lifelist type by name"""
        self.cursor.execute(
            "SELECT id, name, description, icon FROM lifelist_types WHERE name = ?",
            (type_name,)
        )
        return self.cursor.fetchone()

    def get_default_tiers_for_type(self, type_id):
        """Get default tier names for a lifelist type"""
        self.cursor.execute(
            "SELECT tier_name FROM lifelist_type_tiers WHERE lifelist_type_id = ? ORDER BY tier_order",
            (type_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def get_default_fields_for_type(self, type_id):
        """Get default custom fields for a lifelist type"""
        self.cursor.execute(
            """SELECT config_value FROM lifelist_type_configs 
            WHERE lifelist_type_id = ? AND config_key = 'default_fields'""",
            (type_id,)
        )
        result = self.cursor.fetchone()
        if result and result[0]:
            try:
                return json.loads(result[0])
            except Exception:
                return []
        return []

    # Lifelist methods
    def create_lifelist(self, name, lifelist_type_id, classification=None):
        """Create a new lifelist"""
        try:
            self.cursor.execute(
                "INSERT INTO lifelists (name, lifelist_type_id, classification) VALUES (?, ?, ?)",
                (name, lifelist_type_id, classification)
            )
            self.conn.commit()
            lifelist_id = self.cursor.lastrowid

            # Set up default tiers based on lifelist type
            if default_tiers := self.get_default_tiers_for_type(lifelist_type_id):
                self.set_lifelist_tiers(lifelist_id, default_tiers)

            # Set up default fields based on lifelist type
            default_fields = self.get_default_fields_for_type(lifelist_type_id)
            for field in default_fields:
                self.add_custom_field(
                    lifelist_id, 
                    field.get('name'), 
                    field.get('type'),
                    field.get('options'),
                    field.get('required', 0),
                    field.get('order', 0)
                )

            return lifelist_id
        except sqlite3.IntegrityError:
            return None  # Lifelist with this name already exists

    def get_lifelists(self):
        """Get all lifelists"""
        self.cursor.execute("""
            SELECT l.id, l.name, l.classification, t.name as type_name 
            FROM lifelists l
            LEFT JOIN lifelist_types t ON l.lifelist_type_id = t.id
            ORDER BY l.name
        """)
        return self.cursor.fetchall()

    def get_lifelist(self, lifelist_id):
        """Get a specific lifelist by ID"""
        self.cursor.execute("""
            SELECT l.id, l.name, l.classification, l.lifelist_type_id, t.name as type_name 
            FROM lifelists l
            LEFT JOIN lifelist_types t ON l.lifelist_type_id = t.id
            WHERE l.id = ?
        """, (lifelist_id,))
        return self.cursor.fetchone()

    def delete_lifelist(self, lifelist_id):
        """Delete a lifelist by ID"""
        # First, get the lifelist data for potential export
        self.cursor.execute("SELECT name FROM lifelists WHERE id = ?", (lifelist_id,))
        if lifelist := self.cursor.fetchone():
            self.cursor.execute("DELETE FROM lifelists WHERE id = ?", (lifelist_id,))
            self.conn.commit()
            return True
        return False

    # Custom fields methods
    def add_custom_field(self, lifelist_id, field_name, field_type, field_options=None, is_required=0, display_order=0):
        """Add a custom field to a lifelist"""
        try:
            options_json = None
            if field_options:
                if isinstance(field_options, dict):
                    options_json = json.dumps(field_options)
                else:
                    options_json = field_options
                    
            self.cursor.execute(
                """INSERT INTO custom_fields 
                (lifelist_id, field_name, field_type, field_options, is_required, display_order) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (lifelist_id, field_name, field_type, options_json, is_required, display_order)
            )
            
            field_id = self.cursor.lastrowid
            
            # If this is a choice field, add the options
            if field_type == 'choice' and field_options and isinstance(field_options, dict):
                options = field_options.get('options', [])
                for i, option in enumerate(options):
                    self.cursor.execute(
                        "INSERT INTO field_options (field_id, option_value, option_label, option_order) VALUES (?, ?, ?, ?)",
                        (field_id, option.get('value'), option.get('label', option.get('value')), i)
                    )
            
            self.conn.commit()
            return field_id
        except sqlite3.IntegrityError:
            return None

    def get_custom_fields(self, lifelist_id):
        """Get all custom fields for a lifelist"""
        self.cursor.execute(
            """SELECT id, field_name, field_type, field_options, is_required, display_order 
            FROM custom_fields WHERE lifelist_id = ? ORDER BY display_order""",
            (lifelist_id,)
        )
        fields = self.cursor.fetchall()
        
        # For choice fields, get their options
        result = []
        for field in fields:
            field_id, field_name, field_type, field_options, is_required, display_order = field
            
            if field_type == 'choice':
                self.cursor.execute(
                    """SELECT option_value, option_label, option_order
                    FROM field_options WHERE field_id = ? ORDER BY option_order""",
                    (field_id,)
                )
                options = self.cursor.fetchall()
                result.append((field_id, field_name, field_type, field_options, is_required, display_order, options))
            else:
                result.append(field + (None,))  # Add None for options
                
        return result

    def get_field_dependencies(self, field_id):
        """Get dependencies for a field"""
        self.cursor.execute(
            """SELECT parent_field_id, condition_type, condition_value
            FROM field_dependencies WHERE field_id = ?""",
            (field_id,)
        )
        return self.cursor.fetchall()

    def add_field_dependency(self, field_id, parent_field_id, condition_type, condition_value):
        """Add a dependency between fields"""
        try:
            self.cursor.execute(
                """INSERT INTO field_dependencies 
                (field_id, parent_field_id, condition_type, condition_value) 
                VALUES (?, ?, ?, ?)""",
                (field_id, parent_field_id, condition_type, condition_value)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    # Tier methods
    def get_lifelist_tiers(self, lifelist_id):
        """Get custom tiers for a lifelist, or return default tiers if none defined"""
        self.cursor.execute(
            "SELECT tier_name FROM lifelist_tiers WHERE lifelist_id = ? ORDER BY tier_order",
            (lifelist_id,)
        )
        tiers = [row[0] for row in self.cursor.fetchall()]

        # If no custom tiers are defined, get default tiers based on lifelist type
        if not tiers:
            self.cursor.execute("SELECT lifelist_type_id FROM lifelists WHERE id = ?", (lifelist_id,))
            if result := self.cursor.fetchone():
                lifelist_type_id = result[0]
                return self.get_default_tiers_for_type(lifelist_type_id)
            return ["owned", "wanted"]  # Fallback default tiers

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

    # Classification methods (renamed from taxonomy methods)
    def add_classification(self, lifelist_id, name, version=None, source=None, description=None):
        """Add a new classification to a lifelist"""
        try:
            self.cursor.execute(
                """INSERT INTO classifications 
                (lifelist_id, name, version, source, description) 
                VALUES (?, ?, ?, ?, ?)""",
                (lifelist_id, name, version, source, description)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding classification: {e}")
            return None

    def get_classifications(self, lifelist_id):
        """Get all classifications for a lifelist"""
        self.cursor.execute(
            """SELECT id, name, version, source, description, is_active 
            FROM classifications WHERE lifelist_id = ?""",
            (lifelist_id,)
        )
        return self.cursor.fetchall()

    def get_active_classification(self, lifelist_id):
        """Get the active classification for a lifelist"""
        self.cursor.execute(
            """SELECT id, name, version, source, description 
            FROM classifications WHERE lifelist_id = ? AND is_active = 1""",
            (lifelist_id,)
        )
        return self.cursor.fetchone()

    def set_active_classification(self, classification_id, lifelist_id):
        """Set a classification as active for a lifelist"""
        try:
            # First, set all classifications for this lifelist as inactive
            self.cursor.execute(
                "UPDATE classifications SET is_active = 0 WHERE lifelist_id = ?",
                (lifelist_id,)
            )

            # Then set the selected classification as active
            self.cursor.execute(
                "UPDATE classifications SET is_active = 1 WHERE id = ?",
                (classification_id,)
            )

            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error setting active classification: {e}")
            return False

    def add_classification_entry(self, classification_id, name, alternate_name=None, 
                                parent_id=None, category=None, code=None, rank=None, 
                                is_custom=0, additional_data=None):
        """Add an entry to a classification"""
        try:
            # Convert additional_data dict to JSON string if provided
            if additional_data and isinstance(additional_data, dict):
                additional_data = json.dumps(additional_data)

            self.cursor.execute(
                """INSERT INTO classification_entries 
                (classification_id, name, alternate_name, parent_id, category, 
                code, rank, is_custom, additional_data) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (classification_id, name, alternate_name, parent_id, category,
                 code, rank, is_custom, additional_data)
            )

            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding classification entry: {e}")
            return None

    def search_classification(self, classification_id, search_term, limit=10):
        """Search for entries in a classification"""
        search_param = f"%{search_term}%"

        self.cursor.execute(
            """SELECT id, name, alternate_name, category 
            FROM classification_entries 
            WHERE classification_id = ? AND 
            (name LIKE ? OR alternate_name LIKE ?)
            ORDER BY 
                CASE WHEN name LIKE ? THEN 1
                     WHEN alternate_name LIKE ? THEN 2
                     ELSE 3
                END,
                name
            LIMIT ?""",
            (classification_id, search_param, search_param, f"{search_term}%", f"{search_term}%", limit)
        )

        return self.cursor.fetchall()

    # Observation methods (updated to use entry_name instead of species_name)
    def add_observation(self, lifelist_id, entry_name, observation_date=None,
                        location=None, latitude=None, longitude=None, tier=None, notes=None):
        """Add a new observation"""
        try:
            # If tier is not specified, get default tier for this lifelist
            if tier is None:
                tiers = self.get_lifelist_tiers(lifelist_id)
                tier = tiers[0] if tiers else "owned"
                
            self.cursor.execute(
                """INSERT INTO observations 
                (lifelist_id, entry_name, observation_date, location, latitude, longitude, tier, notes) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (lifelist_id, entry_name, observation_date, location, latitude, longitude, tier, notes)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None

    def get_observations(self, lifelist_id, tier=None, tag_ids=None, search_term=None):
        """Get observations with optional filtering"""
        query = "SELECT id, entry_name, observation_date, location, tier FROM observations WHERE lifelist_id = ?"
        params = [lifelist_id]

        if tier:
            query += " AND tier = ?"
            params.append(tier)

        if search_term:
            query += " AND (entry_name LIKE ? OR notes LIKE ? OR location LIKE ?)"
            search_param = f"%{search_term}%"
            params.extend([search_param, search_param, search_param])

        if tag_ids and len(tag_ids) > 0:
            placeholders = ','.join(['?' for _ in tag_ids])
            query = f"""
            SELECT o.id, o.entry_name, o.observation_date, o.location, o.tier
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

    def get_observations_by_entry(self, lifelist_id, entry_name):
        """Get all observations of a specific entry in a lifelist"""
        self.cursor.execute(
            "SELECT id FROM observations WHERE lifelist_id = ? AND entry_name = ?",
            (lifelist_id, entry_name)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def get_observation_details(self, observation_id):
        """Get details for a specific observation"""
        self.cursor.execute(
            """SELECT id, lifelist_id, entry_name, observation_date, location, 
            latitude, longitude, tier, notes FROM observations WHERE id = ?""",
            (observation_id,)
        )
        if observation := self.cursor.fetchone():
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
                """SELECT t.id, t.name, t.category
                FROM tags t
                JOIN observation_tags ot ON t.id = ot.tag_id
                WHERE ot.observation_id = ?""",
                (observation_id,)
            )
            tags = self.cursor.fetchall()

            return observation, custom_fields, tags
        return None, None, None

    def update_observation(self, observation_id, entry_name, observation_date=None,
                           location=None, latitude=None, longitude=None, tier=None, notes=None):
        """Update an existing observation"""
        try:
            self.cursor.execute(
                """UPDATE observations SET
                entry_name = ?, observation_date = ?, location = ?, 
                latitude = ?, longitude = ?, tier = ?, notes = ?
                WHERE id = ?""",
                (entry_name, observation_date, location, latitude, longitude, tier, notes, observation_id)
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

    # Photo methods (unchanged, but primary photo references use entry_name)
    def add_photo(self, observation_id, file_path, is_primary=0, latitude=None, longitude=None, taken_date=None):
        """Add a photo to an observation"""
        try:
            # Get the entry_name and lifelist for this observation
            self.cursor.execute(
                "SELECT entry_name, lifelist_id FROM observations WHERE id = ?",
                (observation_id,)
            )
            entry_name, lifelist_id = self.cursor.fetchone()

            # If this is being set as primary, reset all other photos for this entry
            if is_primary:
                # Get all observations for this entry
                self.cursor.execute(
                    "SELECT id FROM observations WHERE lifelist_id = ? AND entry_name = ?",
                    (lifelist_id, entry_name)
                )
                entry_obs_ids = [row[0] for row in self.cursor.fetchall()]

                # Reset all primary photos for this entry
                for obs_id in entry_obs_ids:
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

    def entry_has_primary_photo(self, lifelist_id, entry_name):
        """Check if an entry already has a primary photo set"""
        query = """
        SELECT COUNT(*) FROM photos p
        JOIN observations o ON p.observation_id = o.id
        WHERE o.lifelist_id = ? AND o.entry_name = ? AND p.is_primary = 1
        """
        self.cursor.execute(query, (lifelist_id, entry_name))
        count = self.cursor.fetchone()[0]
        return count > 0

    def get_primary_photo_for_entry(self, lifelist_id, entry_name):
        """Get the primary photo for an entry across all observations"""
        query = """
        SELECT p.id, p.file_path, p.is_primary, p.latitude, p.longitude, p.taken_date
        FROM photos p
        JOIN observations o ON p.observation_id = o.id
        WHERE o.lifelist_id = ? AND o.entry_name = ? AND p.is_primary = 1
        """
        self.cursor.execute(query, (lifelist_id, entry_name))
        if result := self.cursor.fetchone():
            return result

        # If no primary photo is set, find any photo for this entry
        query = """
        SELECT p.id, p.file_path, p.is_primary, p.latitude, p.longitude, p.taken_date
        FROM photos p
        JOIN observations o ON p.observation_id = o.id
        WHERE o.lifelist_id = ? AND o.entry_name = ?
        LIMIT 1
        """
        self.cursor.execute(query, (lifelist_id, entry_name))
        return self.cursor.fetchone()

    def get_entry_primary_photo(self, lifelist_id, entry_name):
        """Get the primary photo for an entry"""
        query = """
        SELECT p.id, p.file_path, p.is_primary, p.latitude, p.longitude, p.taken_date, o.id as observation_id
        FROM photos p
        JOIN observations o ON p.observation_id = o.id
        WHERE o.lifelist_id = ? AND o.entry_name = ? AND p.is_primary = 1
        ORDER BY p.id DESC
        LIMIT 1
        """
        self.cursor.execute(query, (lifelist_id, entry_name))
        return self.cursor.fetchone()

    def set_primary_photo(self, photo_id, observation_id):
        """Set a photo as the primary photo for an entry"""
        try:
            # Get the entry_name and lifelist_id for this observation
            self.cursor.execute("SELECT entry_name, lifelist_id FROM observations WHERE id = ?", (observation_id,))
            result = self.cursor.fetchone()
            if not result:
                return False

            entry_name, lifelist_id = result

            # Get all observations for this entry
            self.cursor.execute("SELECT id FROM observations WHERE lifelist_id = ? AND entry_name = ?",
                                (lifelist_id, entry_name))
            all_obs_ids = [row[0] for row in self.cursor.fetchall()]

            # Reset primary flag for all photos of this entry
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

    # Tag methods (enhanced with hierarchical tags and categories)
    def add_tag(self, tag_name, category=None):
        """Add a tag or get existing tag ID"""
        try:
            self.cursor.execute("INSERT INTO tags (name, category) VALUES (?, ?)", (tag_name, category))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            # Tag already exists, get its ID
            self.cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            return self.cursor.fetchone()[0]

    def get_all_tags(self, category=None):
        """Get all tags, optionally filtered by category"""
        if category:
            self.cursor.execute("SELECT id, name, category FROM tags WHERE category = ? ORDER BY name", (category,))
        else:
            self.cursor.execute("SELECT id, name, category FROM tags ORDER BY name")
        return self.cursor.fetchall()

    def add_tag_hierarchy(self, tag_id, parent_tag_id):
        """Add a hierarchical relationship between tags"""
        try:
            self.cursor.execute(
                "INSERT INTO tag_hierarchy (tag_id, parent_tag_id) VALUES (?, ?)",
                (tag_id, parent_tag_id)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Relationship already exists

    def get_tag_hierarchy(self, tag_id=None):
        """Get hierarchical relationships between tags"""
        if tag_id:
            # Get direct children of this tag
            self.cursor.execute(
                """SELECT t.id, t.name, t.category
                FROM tags t
                JOIN tag_hierarchy h ON t.id = h.tag_id
                WHERE h.parent_tag_id = ?""",
                (tag_id,)
            )
        else:
            # Get all hierarchical relationships
            self.cursor.execute(
                """SELECT h.tag_id, h.parent_tag_id, t1.name as tag_name, t2.name as parent_name
                FROM tag_hierarchy h
                JOIN tags t1 ON h.tag_id = t1.id
                JOIN tags t2 ON h.parent_tag_id = t2.id"""
            )

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
            """SELECT t.id, t.name, t.category FROM tags t
            JOIN observation_tags ot ON t.id = ot.tag_id
            WHERE ot.observation_id = ?""",
            (observation_id,)
        )
        return self.cursor.fetchall()

    # Import/export methods (updated to work with the new schema)
    def export_lifelist(self, lifelist_id, export_path, include_photos=True):
        """Export a lifelist to a portable format (JSON + photos)"""
        try:
            # Get lifelist info
            self.cursor.execute("""
                SELECT l.id, l.name, l.classification, l.lifelist_type_id, t.name as type_name
                FROM lifelists l
                LEFT JOIN lifelist_types t ON l.lifelist_type_id = t.id
                WHERE l.id = ?
            """, (lifelist_id,))
            lifelist = self.cursor.fetchone()

            if not lifelist:
                return False

            lifelist_data = {
                "id": lifelist[0],
                "name": lifelist[1],
                "classification": lifelist[2],
                "lifelist_type_id": lifelist[3],
                "lifelist_type": lifelist[4],
                "tiers": self.get_lifelist_tiers(lifelist_id),
                "custom_fields": [],
                "observations": []
            }

            # Get custom fields
            self.cursor.execute(
                """SELECT id, field_name, field_type, field_options, is_required, display_order
                FROM custom_fields WHERE lifelist_id = ?""",
                (lifelist_id,)
            )
            for field in self.cursor.fetchall():
                lifelist_data["custom_fields"].append({
                    "id": field[0],
                    "name": field[1],
                    "type": field[2],
                    "options": field[3],
                    "required": field[4],
                    "order": field[5]
                })

            # Get observations
            self.cursor.execute(
                """SELECT id, entry_name, observation_date, location, 
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
                    "entry_name": obs[1],
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
                    """SELECT t.name, t.category
                    FROM tags t
                    JOIN observation_tags ot ON t.id = ot.tag_id
                    WHERE ot.observation_id = ?""",
                    (obs[0],)
                )

                obs_data["tags"] = [{"name": tag[0], "category": tag[1]} for tag in self.cursor.fetchall()]

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
            classification = lifelist_data.get("classification")
            lifelist_type_id = lifelist_data.get("lifelist_type_id", 8)  # Default to Collectibles if not specified

            # Check if lifelist already exists
            self.cursor.execute("SELECT id FROM lifelists WHERE name = ?", (lifelist_name,))
            if existing := self.cursor.fetchone():
                return False, f"Lifelist '{lifelist_name}' already exists"

            lifelist_id = self.create_lifelist(lifelist_name, lifelist_type_id, classification)

            # Import custom tiers if present
            if "tiers" in lifelist_data:
                self.set_lifelist_tiers(lifelist_id, lifelist_data["tiers"])

            # Create custom fields
            field_id_mapping = {}
            for field in lifelist_data.get("custom_fields", []):
                new_id = self.add_custom_field(
                    lifelist_id, 
                    field["name"], 
                    field.get("type", "text"),
                    field.get("options"),
                    field.get("required", 0),
                    field.get("order", 0)
                )
                field_id_mapping[field["id"]] = new_id

            # Import observations
            for obs in lifelist_data.get("observations", []):
                obs_id = self.add_observation(
                    lifelist_id,
                    obs["entry_name"],
                    obs.get("observation_date"),
                    obs.get("location"),
                    obs.get("latitude"),
                    obs.get("longitude"),
                    obs.get("tier"),
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
                    if field_result := self.cursor.fetchone():
                        field_id = field_result[0]
                        self.cursor.execute(
                            "INSERT INTO observation_custom_fields (observation_id, field_id, value) VALUES (?, ?, ?)",
                            (obs_id, field_id, field["value"])
                        )

                # Add tags
                for tag_info in obs.get("tags", []):
                    if isinstance(tag_info, dict):
                        tag_name = tag_info["name"]
                        category = tag_info.get("category")
                        tag_id = self.add_tag(tag_name, category)
                    else:
                        tag_name = tag_info
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