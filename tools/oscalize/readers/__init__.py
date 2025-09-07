"""
Document readers for oscalize

Readers convert input formats (DOCX, MD, XLSX) to Canonical Intermediate Representation (CIR).
All readers implement source attribution for auditability.
"""

from .document_reader import DocumentReader
from .poam_reader import POAMReader  
from .inventory_reader import InventoryReader
from .base_reader import BaseReader

__all__ = [
    'BaseReader',
    'DocumentReader', 
    'POAMReader',
    'InventoryReader'
]