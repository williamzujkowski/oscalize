"""
oscalize - LLM-free local OSCAL converter

A Docker-containerized CLI tool that converts .docx/.md SSP content and .xlsx appendices 
(POA&M, Integrated Inventory, CIS/CRM) into OSCAL v1.1.3 JSON artifacts.

Key features:
- Deterministic, offline conversion with no LLMs
- Multi-arch Docker support (Intel/ARM)
- Validation with NIST oscal-cli
- FedRAMP v3.0 POA&M and Integrated Inventory Workbook support
- FIPS-199 categorization mapping
- Signed reproducible bundles with manifests

Architecture:
    Inputs (DOCX/MD/XLSX) → Readers → CIR → Mappers → OSCAL JSON → Validation → Bundle

Compliance:
- OMB M-24-15 automation requirements
- NIST SP 800-53 Release 5.2.0
- NIST SP 800-171 r3  
- NIST SP 800-18 r1 (tracking r2-IPD)
- FedRAMP Initial Authorization Package requirements
"""

__version__ = "1.0.0"
__author__ = "oscalize contributors"
__license__ = "Apache-2.0"

from .cli import cli

__all__ = ['cli']