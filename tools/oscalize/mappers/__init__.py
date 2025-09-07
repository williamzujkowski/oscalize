"""
OSCAL mappers for oscalize

Mappers convert Canonical Intermediate Representation (CIR) to OSCAL v1.1.3 JSON artifacts.
All mappers maintain source attribution and comply with NIST OSCAL model specifications.
"""

from .base_mapper import BaseMapper
from .ssp_mapper import SSPMapper
from .poam_mapper import POAMMapper
from .inventory_mapper import InventoryMapper
from .assessment_mapper import AssessmentMapper

__all__ = [
    'BaseMapper',
    'SSPMapper',
    'POAMMapper', 
    'InventoryMapper',
    'AssessmentMapper'
]