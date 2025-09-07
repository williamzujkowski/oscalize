"""
CIR data processor

Processes and normalizes CIR data structures for consistency and optimization.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CIRProcessor:
    """Processor for CIR data normalization and enhancement"""
    
    def __init__(self):
        self.control_id_patterns = [
            r'\b[A-Z]{2}-\d+(?:\(\d+\))?\b',  # AC-1, AC-2(1), etc.
            r'\b[A-Z]{2}\.\d+\b'              # AC.1, AC.2, etc.
        ]
    
    def process(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """Process CIR data based on type"""
        logger.debug(f"Processing CIR data of type: {data_type}")
        
        if data_type == "document":
            return self._process_document(data)
        elif data_type == "poam":
            return self._process_poam(data)
        elif data_type == "inventory":
            return self._process_inventory(data)
        elif data_type == "controls":
            return self._process_controls(data)
        else:
            logger.warning(f"Unknown CIR data type: {data_type}")
            return data
    
    def _process_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process document CIR data"""
        processed_data = data.copy()
        
        if "sections" in processed_data:
            processed_sections = []
            
            for section in processed_data["sections"]:
                processed_section = self._process_section(section)
                processed_sections.append(processed_section)
            
            processed_data["sections"] = processed_sections
        
        return processed_data
    
    def _process_section(self, section: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual document section"""
        processed_section = section.copy()
        
        # Normalize section title
        if "title" in processed_section:
            processed_section["title"] = self._normalize_text(processed_section["title"])
        
        # Extract and enhance control references
        text = processed_section.get("text", "")
        control_ids = self._extract_control_ids(text)
        if control_ids:
            processed_section["control_references"] = control_ids
        
        # Process tables
        if "tables" in processed_section:
            processed_tables = []
            for table in processed_section["tables"]:
                processed_table = self._process_table(table)
                processed_tables.append(processed_table)
            processed_section["tables"] = processed_tables
        
        return processed_section
    
    def _process_table(self, table: Dict[str, Any]) -> Dict[str, Any]:
        """Process table data"""
        processed_table = table.copy()
        
        # Normalize headers
        if "headers" in processed_table:
            processed_table["headers"] = [
                self._normalize_text(header) for header in processed_table["headers"]
            ]
        
        # Normalize cell data
        if "rows" in processed_table:
            processed_rows = []
            for row in processed_table["rows"]:
                processed_row = [self._normalize_text(cell) for cell in row]
                processed_rows.append(processed_row)
            processed_table["rows"] = processed_rows
        
        return processed_table
    
    def _process_poam(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process POA&M CIR data"""
        processed_data = data.copy()
        
        if "rows" in processed_data:
            processed_rows = []
            
            for row in processed_data["rows"]:
                processed_row = self._process_poam_row(row)
                processed_rows.append(processed_row)
            
            processed_data["rows"] = processed_rows
        
        return processed_data
    
    def _process_poam_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual POA&M row"""
        processed_row = row.copy()
        
        # Normalize text fields
        text_fields = ["title", "description", "comments"]
        for field in text_fields:
            if field in processed_row:
                processed_row[field] = self._normalize_text(processed_row[field])
        
        # Validate and normalize control IDs
        if "control_ids" in processed_row:
            normalized_ids = []
            for control_id in processed_row["control_ids"]:
                normalized_id = self._normalize_control_id(control_id)
                if normalized_id:
                    normalized_ids.append(normalized_id)
            processed_row["control_ids"] = normalized_ids
        
        # Normalize asset IDs
        if "asset_ids" in processed_row:
            processed_row["asset_ids"] = [
                self._normalize_asset_id(asset_id) 
                for asset_id in processed_row["asset_ids"]
            ]
        
        # Add derived fields
        processed_row["risk_score"] = self._calculate_risk_score(processed_row)
        
        return processed_row
    
    def _process_inventory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process inventory CIR data"""
        processed_data = data.copy()
        
        if "assets" in processed_data:
            processed_assets = []
            
            for asset in processed_data["assets"]:
                processed_asset = self._process_asset(asset)
                processed_assets.append(processed_asset)
            
            processed_data["assets"] = processed_assets
        
        return processed_data
    
    def _process_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual asset"""
        processed_asset = asset.copy()
        
        # Normalize text fields
        text_fields = ["name", "description", "asset_owner", "system_admin"]
        for field in text_fields:
            if field in processed_asset:
                processed_asset[field] = self._normalize_text(processed_asset[field])
        
        # Normalize asset ID
        if "asset_id" in processed_asset:
            processed_asset["asset_id"] = self._normalize_asset_id(processed_asset["asset_id"])
        
        # Add computed fields
        processed_asset["fqdn"] = self._derive_fqdn(processed_asset)
        processed_asset["risk_category"] = self._categorize_risk(processed_asset)
        
        # Validate IP addresses
        if "ip_address" in processed_asset:
            ip_valid = self._validate_ip_address(processed_asset["ip_address"])
            processed_asset["ip_address_valid"] = ip_valid
        
        return processed_asset
    
    def _process_controls(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process controls CIR data"""
        processed_data = data.copy()
        
        if "controls" in processed_data:
            processed_controls = []
            
            for control in processed_data["controls"]:
                processed_control = self._process_control(control)
                processed_controls.append(processed_control)
            
            processed_data["controls"] = processed_controls
        
        return processed_data
    
    def _process_control(self, control: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual control"""
        processed_control = control.copy()
        
        # Normalize control ID
        if "control_id" in processed_control:
            processed_control["control_id"] = self._normalize_control_id(processed_control["control_id"])
        
        # Normalize text fields
        text_fields = ["control_title", "control_description", "implementation_guidance", "notes"]
        for field in text_fields:
            if field in processed_control:
                processed_control[field] = self._normalize_text(processed_control[field])
        
        return processed_control
    
    # Helper methods
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text content"""
        if not text:
            return ""
        
        # Strip whitespace
        normalized = text.strip()
        
        # Replace multiple whitespace with single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove non-printable characters except newlines and tabs
        normalized = re.sub(r'[^\x20-\x7E\n\t]', '', normalized)
        
        return normalized
    
    def _extract_control_ids(self, text: str) -> List[str]:
        """Extract NIST control IDs from text"""
        control_ids = set()
        
        for pattern in self.control_id_patterns:
            matches = re.findall(pattern, text)
            control_ids.update(matches)
        
        return sorted(list(control_ids))
    
    def _normalize_control_id(self, control_id: str) -> Optional[str]:
        """Normalize control ID format"""
        if not control_id:
            return None
        
        # Remove whitespace and convert to uppercase
        normalized = control_id.strip().upper()
        
        # Validate format
        for pattern in self.control_id_patterns:
            if re.match(pattern, normalized):
                return normalized
        
        logger.warning(f"Invalid control ID format: {control_id}")
        return control_id  # Return original if validation fails
    
    def _normalize_asset_id(self, asset_id: str) -> str:
        """Normalize asset ID format"""
        if not asset_id:
            return ""
        
        # Remove whitespace and convert to lowercase
        normalized = asset_id.strip().lower()
        
        # Replace spaces and special characters with hyphens
        normalized = re.sub(r'[^\w\-]', '-', normalized)
        
        # Remove multiple consecutive hyphens
        normalized = re.sub(r'-+', '-', normalized)
        
        # Remove leading/trailing hyphens
        normalized = normalized.strip('-')
        
        return normalized
    
    def _calculate_risk_score(self, poam_row: Dict[str, Any]) -> int:
        """Calculate numeric risk score from POA&M data"""
        severity = poam_row.get("severity", "Low")
        status = poam_row.get("status", "Open")
        
        # Base score from severity
        severity_scores = {
            "Critical": 10,
            "High": 7,
            "Moderate": 4,
            "Low": 1
        }
        
        base_score = severity_scores.get(severity, 1)
        
        # Adjust for status
        status_multipliers = {
            "Open": 1.0,
            "Ongoing": 0.7,
            "Risk Accepted": 0.3,
            "Completed": 0.1
        }
        
        multiplier = status_multipliers.get(status, 1.0)
        
        return int(base_score * multiplier)
    
    def _derive_fqdn(self, asset: Dict[str, Any]) -> Optional[str]:
        """Derive FQDN from asset data"""
        name = asset.get("name", "")
        network_location = asset.get("network_location", "")
        
        if "." in name:
            return name  # Already looks like FQDN
        
        if network_location and "." in network_location:
            return f"{name}.{network_location}"
        
        return None
    
    def _categorize_risk(self, asset: Dict[str, Any]) -> str:
        """Categorize asset risk level"""
        criticality = asset.get("criticality", "Low")
        public_access = asset.get("public_access", False)
        environment = asset.get("environment", "")
        
        # High risk conditions
        if criticality in ["Critical", "High"]:
            if public_access or environment == "Production":
                return "high"
        
        # Medium risk conditions  
        if criticality == "Moderate" or public_access or environment == "Production":
            return "medium"
        
        return "low"
    
    def _validate_ip_address(self, ip_str: str) -> bool:
        """Validate IP address format"""
        import ipaddress
        
        try:
            ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False