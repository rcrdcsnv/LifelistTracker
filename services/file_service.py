# services/file_service.py
"""
File Service - Handles file operations
"""
import os
import shutil
import json
import csv
from typing import Dict, List, Any, Tuple, Optional, Union


class IFileService:
    """Interface for file service"""

    def ensure_directory(self, directory_path: str) -> bool:
        pass

    def read_json(self, file_path: str) -> Optional[Dict[str, Any]]:
        pass

    def write_json(self, file_path: str, data: Dict[str, Any], indent: int = 2) -> bool:
        pass

    def read_csv_dict(self, file_path: str, encoding: str = 'utf-8') -> Tuple[List[Dict[str, str]], List[str]]:
        pass

    def read_csv_rows(self, file_path: str, encoding: str = 'utf-8') -> Tuple[List[List[str]], List[str]]:
        pass

    def write_csv(self, file_path: str, headers: List[str], rows: List[Union[List[str], Dict[str, str]]],
                  encoding: str = 'utf-8') -> bool:
        pass

    def copy_file(self, source_path: str, destination_path: str) -> bool:
        pass

    def delete_file(self, file_path: str) -> bool:
        pass

    def list_files(self, directory_path: str, extension: Optional[str] = None) -> List[str]:
        pass


class FileService(IFileService):
    """Service for file operations"""

    def __init__(self):
        """Initialize the file service with no dependencies"""
        pass

    def ensure_directory(self, directory_path: str) -> bool:
        """
        Ensure a directory exists, creating it if necessary

        Args:
            directory_path: Path to the directory to ensure

        Returns:
            True if directory exists or was created, False otherwise
        """
        try:
            os.makedirs(directory_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directory {directory_path}: {e}")
            return False

    def read_json(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Read a JSON file

        Args:
            file_path: Path to the JSON file

        Returns:
            Parsed JSON data or None if reading failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading JSON file {file_path}: {e}")
            return None

    def write_json(self, file_path: str, data: Dict[str, Any], indent: int = 2) -> bool:
        """
        Write data to a JSON file

        Args:
            file_path: Path to the JSON file
            data: Data to write
            indent: Indentation level for formatting

        Returns:
            True if writing succeeded, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent)
            return True
        except Exception as e:
            print(f"Error writing JSON file {file_path}: {e}")
            return False

    def read_csv_dict(self, file_path: str, encoding: str = 'utf-8') -> Tuple[List[Dict[str, str]], List[str]]:
        """
        Read a CSV file as a list of dictionaries

        Args:
            file_path: Path to the CSV file
            encoding: File encoding

        Returns:
            Tuple of (List of row dictionaries, List of header names)
        """
        rows = []
        headers = []

        try:
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                for row in reader:
                    rows.append(row)
            return rows, headers
        except Exception as e:
            print(f"Error reading CSV file {file_path}: {e}")
            return [], []

    def read_csv_rows(self, file_path: str, encoding: str = 'utf-8') -> Tuple[List[List[str]], List[str]]:
        """
        Read a CSV file as a list of rows

        Args:
            file_path: Path to the CSV file
            encoding: File encoding

        Returns:
            Tuple of (List of rows, List of header names)
        """
        rows = []
        headers = []

        try:
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                for row in reader:
                    rows.append(row)
            return rows, headers
        except Exception as e:
            print(f"Error reading CSV file {file_path}: {e}")
            return [], []

    def write_csv(self, file_path: str, headers: List[str], rows: List[Union[List[str], Dict[str, str]]],
                  encoding: str = 'utf-8') -> bool:
        """
        Write data to a CSV file

        Args:
            file_path: Path to the CSV file
            headers: List of column headers
            rows: List of rows (either lists or dictionaries)
            encoding: File encoding

        Returns:
            True if writing succeeded, False otherwise
        """
        try:
            with open(file_path, 'w', encoding=encoding, newline='') as f:
                if rows and isinstance(rows[0], dict):
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(rows)
                else:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(rows)
            return True
        except Exception as e:
            print(f"Error writing CSV file {file_path}: {e}")
            return False

    def copy_file(self, source_path: str, destination_path: str) -> bool:
        """
        Copy a file from source to destination

        Args:
            source_path: Source file path
            destination_path: Destination file path

        Returns:
            True if copy succeeded, False otherwise
        """
        try:
            shutil.copy2(source_path, destination_path)
            return True
        except Exception as e:
            print(f"Error copying file from {source_path} to {destination_path}: {e}")
            return False

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file

        Args:
            file_path: Path to the file to delete

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False

    def list_files(self, directory_path: str, extension: Optional[str] = None) -> List[str]:
        """
        List files in a directory, optionally filtered by extension

        Args:
            directory_path: Directory to list files from
            extension: Optional file extension filter (e.g., '.jpg')

        Returns:
            List of file paths
        """
        try:
            if not os.path.exists(directory_path):
                return []

            files = []
            for filename in os.listdir(directory_path):
                file_path = os.path.join(directory_path, filename)
                if os.path.isfile(file_path):
                    if extension is None or filename.lower().endswith(extension.lower()):
                        files.append(file_path)
            return files
        except Exception as e:
            print(f"Error listing files in {directory_path}: {e}")
            return []