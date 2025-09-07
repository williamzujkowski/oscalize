"""
Base reader class for oscalize

Provides common functionality for all document readers.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class BaseReader(ABC):
    """Base class for all document readers"""
    
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
        
        self.file_hash = self._calculate_file_hash()
        self.extraction_date = datetime.utcnow().isoformat() + "Z"
    
    def _calculate_file_hash(self) -> str:
        """Calculate SHA-256 hash of input file"""
        hasher = hashlib.sha256()
        with open(self.file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _create_source_reference(self, **kwargs) -> Dict[str, Any]:
        """Create source reference for auditability"""
        source = {
            "file": str(self.file_path),
            **kwargs
        }
        return source
    
    @abstractmethod
    def to_cir(self) -> Dict[str, Any]:
        """Convert input to Canonical Intermediate Representation"""
        pass
    
    def _create_base_metadata(self, source_type: str, **additional) -> Dict[str, Any]:
        """Create base metadata section for CIR"""
        return {
            "source_file": str(self.file_path),
            "source_type": source_type,
            "extraction_date": self.extraction_date,
            "hash": self.file_hash,
            **additional
        }