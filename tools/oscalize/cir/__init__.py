"""
Canonical Intermediate Representation (CIR) processing

Provides validation and processing utilities for CIR data structures.
"""

from .validator import CIRValidator
from .processor import CIRProcessor

__all__ = [
    'CIRValidator',
    'CIRProcessor'
]