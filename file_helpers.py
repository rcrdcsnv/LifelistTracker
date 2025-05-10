# file_helpers.py
from pathlib import Path
import json
import csv
from typing import Dict, List, Any, Tuple, Optional, Union

def ensure_directory(directory_path: Union[str, Path]) -> bool:
    """Create directory if it doesn't exist"""
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {directory_path}: {e}")
        return False

def read_json(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Read a JSON file"""
    try:
        file_path = Path(file_path)
        return json.loads(file_path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"Error reading JSON file {file_path}: {e}")
        return None

def write_json(file_path: Union[str, Path], data: Dict[str, Any], indent: int = 2) -> bool:
    """Write data to a JSON file"""
    try:
        file_path = Path(file_path)
        file_path.write_text(json.dumps(data, indent=indent), encoding='utf-8')
        return True
    except Exception as e:
        print(f"Error writing JSON file {file_path}: {e}")
        return False

def read_csv_dict(file_path: Union[str, Path], encoding: str = 'utf-8') -> Tuple[List[Dict[str, str]], List[str]]:
    """Read a CSV file as a list of dictionaries"""
    try:
        file_path = Path(file_path)
        with file_path.open('r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            rows = list(reader)
        return rows, headers
    except Exception as e:
        print(f"Error reading CSV file {file_path}: {e}")
        return [], []

def list_files(directory_path: Union[str, Path], extension: Optional[str] = None) -> List[Path]:
    """List files in a directory, optionally filtered by extension"""
    directory = Path(directory_path)
    if not directory.exists():
        return []
        
    if extension:
        return list(directory.glob(f"*{extension}"))
    else:
        return [f for f in directory.iterdir() if f.is_file()]