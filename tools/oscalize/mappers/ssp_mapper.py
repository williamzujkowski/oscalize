"""
System Security Plan (SSP) mapper

Converts CIR document data to OSCAL SSP v1.1.3 format.
Maps system characteristics, FIPS-199 categorization, and control implementations.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_mapper import BaseMapper

logger = logging.getLogger(__name__)


class SSPMapper(BaseMapper):
    """Mapper for System Security Plan (SSP) OSCAL artifacts"""
    
    def __init__(self, mapping_dir: Optional[Path] = None):
        super().__init__(mapping_dir)
        self.section_mappings = self._load_mapping_config("ssp_sections")
        self.control_mappings = self._load_mapping_config("control_mappings") 
        
    def map(self, cir_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map CIR data to OSCAL SSP format"""
        logger.info("Mapping CIR data to OSCAL SSP")
        
        # Extract document and metadata
        document = cir_data.get("document", {})
        poam = cir_data.get("poam", {})
        inventory = cir_data.get("inventory", {})
        
        # Build SSP structure
        ssp = {
            "system-security-plan": {
                "uuid": self.generate_uuid(),
                "metadata": self._build_metadata(document),
                "import-profile": self._build_import_profile(),
                "system-characteristics": self._build_system_characteristics(document, inventory),
                "system-implementation": self._build_system_implementation(document, inventory),
                "control-implementation": self._build_control_implementation(document, poam),
                "back-matter": self._build_back_matter(cir_data)
            }
        }
        
        return ssp
    
    def _build_metadata(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Build OSCAL metadata from document CIR"""
        doc_metadata = document.get("metadata", {})
        
        # Extract system name and other metadata from document sections
        system_info = self._extract_system_info(document.get("sections", []))
        
        metadata = self.create_oscal_metadata(
            title=system_info.get("system_name", "System Security Plan"),
            version=system_info.get("version", "1.0")
        )
        
        # Add document properties
        metadata["props"] = [
            self.create_property("source-file", doc_metadata.get("source_file", "")),
            self.create_property("source-type", doc_metadata.get("source_type", "")),
            self.create_property("extraction-date", doc_metadata.get("extraction_date", "")),
            self.create_property("file-hash", doc_metadata.get("hash", ""))
        ]
        
        if doc_metadata.get("pandoc_version"):
            metadata["props"].append(
                self.create_property("pandoc-version", doc_metadata["pandoc_version"])
            )
        
        # Add stakeholders as parties
        stakeholders = system_info.get("stakeholders", [])
        if stakeholders:
            metadata["parties"] = []
            metadata["responsible-parties"] = {}
            
            for stakeholder in stakeholders:
                party = self.create_party(
                    name=stakeholder.get("name", ""),
                    party_type=stakeholder.get("type", "person"),
                    email=stakeholder.get("email"),
                    phone=stakeholder.get("phone")
                )
                metadata["parties"].append(party)
                
                # Map roles to responsible parties
                role = stakeholder.get("role", "").lower()
                if role in ["system-owner", "authorizing-official", "isso"]:
                    if role not in metadata["responsible-parties"]:
                        metadata["responsible-parties"][role] = []
                    metadata["responsible-parties"][role].append({
                        "party-uuid": party["uuid"]
                    })
        
        return metadata
    
    def _build_import_profile(self) -> Dict[str, Any]:
        """Build import-profile section"""
        # Default to FedRAMP Low baseline
        return {
            "href": "https://raw.githubusercontent.com/usnistgov/oscal-content/master/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_LOW-baseline_profile.json"
        }
    
    def _build_system_characteristics(self, document: Dict[str, Any], 
                                    inventory: Dict[str, Any]) -> Dict[str, Any]:
        """Build system-characteristics section"""
        sections = document.get("sections", [])
        system_info = self._extract_system_info(sections)
        
        characteristics = {
            "system-ids": [
                {
                    "identifier-type": "https://ietf.org/rfc/rfc4122",
                    "id": system_info.get("system_id", self.generate_uuid())
                }
            ],
            "system-name": system_info.get("system_name", "Unknown System"),
            "description": system_info.get("description", ""),
            "status": {
                "state": system_info.get("status", "operational")
            },
            "system-information": self._build_system_information(system_info),
            "authorization-boundary": self._build_authorization_boundary(sections),
            "network-architecture": self._build_network_architecture(sections, inventory),
            "data-flow": self._build_data_flow(sections)
        }
        
        # Add FIPS-199 security categorization
        if system_info.get("fips199"):
            characteristics["security-sensitivity-level"] = system_info["fips199"]["overall_impact"].lower()
            characteristics.update(self.map_fips199_impact_level(system_info["fips199"]))
        
        return characteristics
    
    def _build_system_information(self, system_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build system-information section"""
        info = {
            "information-types": []
        }
        
        # Add information types based on system classification
        if system_info.get("information_types"):
            for info_type in system_info["information_types"]:
                info["information-types"].append({
                    "uuid": self.generate_uuid(),
                    "title": info_type.get("title", ""),
                    "description": info_type.get("description", ""),
                    "categorizations": info_type.get("categorizations", []),
                    "confidentiality-impact": {
                        "base": info_type.get("confidentiality", "").lower()
                    },
                    "integrity-impact": {
                        "base": info_type.get("integrity", "").lower()
                    },
                    "availability-impact": {
                        "base": info_type.get("availability", "").lower()
                    }
                })
        
        # Ensure at least one information type exists (OSCAL requirement)
        if not info["information-types"]:
            info["information-types"].append({
                "uuid": self.generate_uuid(),
                "title": "General Business Information",
                "description": "General business information processed by the system",
                "categorizations": [
                    {
                        "system": "https://doi.org/10.6028/NIST.SP.800-60v1r1",
                        "information-type-ids": ["C.2.8.12"]
                    }
                ],
                "confidentiality-impact": {"base": "moderate"},
                "integrity-impact": {"base": "moderate"}, 
                "availability-impact": {"base": "low"}
            })
        
        return info
    
    def _build_authorization_boundary(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build authorization-boundary section"""
        # Find authorization boundary description
        boundary_text = self._extract_section_text(sections, ["authorization boundary", "system boundary"])
        
        return {
            "description": boundary_text or "Authorization boundary description not found in source document."
        }
    
    def _build_network_architecture(self, sections: List[Dict[str, Any]], 
                                   inventory: Dict[str, Any]) -> Dict[str, Any]:
        """Build network-architecture section"""
        # Find network architecture description
        network_text = self._extract_section_text(sections, ["network architecture", "network diagram", "system architecture"])
        
        architecture = {
            "description": network_text or "Network architecture description not found in source document."
        }
        
        # Add network diagrams if referenced
        diagrams = self._extract_diagrams(sections, ["network", "architecture", "topology"])
        if diagrams:
            architecture["diagrams"] = diagrams
        
        return architecture
    
    def _build_data_flow(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build data-flow section"""
        # Find data flow description
        dataflow_text = self._extract_section_text(sections, ["data flow", "information flow"])
        
        return {
            "description": dataflow_text or "Data flow description not found in source document."
        }
    
    def _build_system_implementation(self, document: Dict[str, Any], 
                                   inventory: Dict[str, Any]) -> Dict[str, Any]:
        """Build system-implementation section"""
        implementation = {
            "users": self._build_users(document.get("sections", [])),
            "components": self._build_components(inventory),
            "inventory-items": self._build_inventory_items(inventory)
        }
        
        return implementation
    
    def _build_users(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build users from document sections"""
        users = []
        
        # Find user roles and privileges sections
        user_text = self._extract_section_text(sections, ["user", "role", "privilege", "access"])
        
        if user_text:
            # Extract user roles from text (simplified extraction)
            user_roles = self._extract_user_roles(user_text)
            for role in user_roles:
                # Convert string privileges to proper OSCAL privilege objects
                privileges = role.get("privileges", [])
                authorized_privileges = []
                for priv in privileges:
                    if isinstance(priv, str):
                        authorized_privileges.append({
                            "title": priv,
                            "functions-performed": [priv]
                        })
                    else:
                        authorized_privileges.append(priv)
                
                users.append({
                    "uuid": self.generate_uuid(),
                    "title": role["title"],
                    "description": role.get("description", ""),
                    "role-ids": [role["title"].lower().replace(" ", "-")],
                    "authorized-privileges": authorized_privileges
                })
        
        return users
    
    def _build_components(self, inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build components from inventory data"""
        components = []
        
        if not inventory.get("assets"):
            return components
        
        # Group assets by component type
        component_groups = {}
        for asset in inventory["assets"]:
            component_type = asset.get("asset_type", "other")
            if component_type not in component_groups:
                component_groups[component_type] = []
            component_groups[component_type].append(asset)
        
        # Create components for each group
        for comp_type, assets in component_groups.items():
            component = {
                "uuid": self.generate_uuid(),
                "type": comp_type,
                "title": f"{comp_type.title()} Components",
                "description": f"Components of type: {comp_type}",
                "status": {"state": "operational"},
                "responsible-roles": [
                    {
                        "role-id": "system-administrator",
                        "props": [
                            self.create_property("component-type", comp_type)
                        ]
                    }
                ],
                "props": [
                    self.create_property("asset-count", str(len(assets))),
                    self.create_property("component-type", comp_type)
                ]
            }
            
            components.append(component)
        
        return components
    
    def _build_inventory_items(self, inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build inventory-items from inventory data"""
        items = []
        
        if not inventory.get("assets"):
            return items
        
        for asset in inventory["assets"]:
            item = {
                "uuid": self.generate_uuid(),
                "description": asset.get("description", asset.get("name", "")),
                "props": []
            }
            
            # Add asset properties
            for field, value in asset.items():
                if field in ["asset_id", "name", "asset_type", "environment", "criticality"]:
                    if value:
                        item["props"].append(self.create_property(field.replace("_", "-"), str(value)))
            
            # Add implemented components reference
            if asset.get("asset_type"):
                item["implemented-components"] = [
                    {
                        "component-uuid": self.generate_uuid(),  # Should reference actual component
                        "props": [
                            self.create_property("asset-id", asset.get("asset_id", ""))
                        ]
                    }
                ]
            
            items.append(item)
        
        return items
    
    def _build_control_implementation(self, document: Dict[str, Any], 
                                    poam: Dict[str, Any]) -> Dict[str, Any]:
        """Build control-implementation section"""
        sections = document.get("sections", [])
        
        # Extract control implementations from document sections
        implemented_requirements = self._extract_control_implementations(sections)
        
        # Add POA&M-referenced controls (without findings - handled separately in POA&M artifact)
        if poam.get("rows"):
            self._add_poam_controls(implemented_requirements, poam["rows"])
        
        return {
            "description": "Control implementation descriptions extracted from source documents.",
            "implemented-requirements": implemented_requirements
        }
    
    def _extract_control_implementations(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract control implementations from document sections"""
        implementations = []
        
        for section in sections:
            # Look for control-related sections
            control_ids = self._extract_control_ids(section.get("title", ""), section.get("text", ""))
            
            if control_ids:
                for control_id in control_ids:
                    implementation = {
                        "uuid": self.generate_uuid(),
                        "control-id": control_id,
                        "props": [
                            self.create_property("implementation-status", "implemented"),
                            self.create_property("source-section", section.get("title", ""))
                        ],
                        "statements": [
                            {
                                "statement-id": f"{control_id}_stmt",
                                "uuid": self.generate_uuid(),
                                "remarks": section.get("text", "")
                            }
                        ]
                    }
                    implementations.append(implementation)
        
        return implementations
    
    def _add_poam_controls(self, implementations: List[Dict[str, Any]], poam_rows: List[Dict[str, Any]]) -> None:
        """Add POA&M-referenced controls to implementations (without findings)"""
        for poam_item in poam_rows:
            control_ids = poam_item.get("control_ids", [])
            
            for control_id in control_ids:
                if not control_id:
                    continue
                
                # Find matching implementation or create new one
                impl = None
                for existing_impl in implementations:
                    if existing_impl["control-id"] == control_id:
                        impl = existing_impl
                        break
                
                if not impl:
                    # Create new implementation for this control
                    impl = {
                        "uuid": self.generate_uuid(),
                        "control-id": control_id,
                        "props": [
                            self.create_property("implementation-status", "partially-implemented")
                        ],
                        "statements": [
                            {
                                "statement-id": f"{control_id}_stmt",
                                "uuid": self.generate_uuid(),
                                "remarks": f"Control {control_id} implementation has open POA&M items. See POA&M artifact for details."
                            }
                        ]
                    }
                    implementations.append(impl)
    
    def _build_back_matter(self, cir_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build back-matter section with source documents"""
        resources = []
        
        # Add source document references
        for data_type, data in cir_data.items():
            if isinstance(data, dict) and "metadata" in data:
                metadata = data["metadata"]
                source_file = metadata.get("source_file", "")
                
                if source_file:
                    resource = self.create_back_matter_resource(
                        title=f"Source {data_type.title()}: {Path(source_file).name}",
                        source_path=source_file,
                        description=f"Original {data_type} file used for OSCAL generation"
                    )
                    resources.append(resource)
        
        return {
            "resources": resources
        }
    
    def integrate_inventory(self, ssp: Dict[str, Any], inventory_cir: Dict[str, Any]) -> None:
        """Integrate inventory data into existing SSP"""
        if "system-security-plan" not in ssp:
            return
        
        # Update system implementation with inventory
        if "system-implementation" not in ssp["system-security-plan"]:
            ssp["system-security-plan"]["system-implementation"] = {}
        
        ssp["system-security-plan"]["system-implementation"]["components"] = self._build_components(inventory_cir)
        ssp["system-security-plan"]["system-implementation"]["inventory-items"] = self._build_inventory_items(inventory_cir)
    
    # Helper methods
    
    def _extract_system_info(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract system information from document sections"""
        system_info = {}
        
        for section in sections:
            title_lower = section.get("title", "").lower()
            text = section.get("text", "")
            
            # Extract system name
            if "system name" in title_lower or "information system" in title_lower:
                system_info["system_name"] = self._extract_field_value(text, ["system name", "name"])
            
            # Extract system ID
            if "system id" in title_lower or "identifier" in title_lower:
                system_info["system_id"] = self._extract_field_value(text, ["system id", "identifier", "id"])
            
            # Extract FIPS-199 categorization
            if "fips" in title_lower and "199" in title_lower:
                system_info["fips199"] = self._extract_fips199(text)
            
            # Extract system description
            if "description" in title_lower or "overview" in title_lower:
                system_info["description"] = text[:500] + "..." if len(text) > 500 else text
        
        return system_info
    
    def _extract_section_text(self, sections: List[Dict[str, Any]], keywords: List[str]) -> Optional[str]:
        """Extract text from sections matching keywords"""
        for section in sections:
            title_lower = section.get("title", "").lower()
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    return section.get("text", "")
        return None
    
    def _extract_control_ids(self, title: str, text: str) -> List[str]:
        """Extract NIST control IDs from title and text"""
        # Common patterns for NIST controls
        patterns = [
            r'\b[A-Z]{2}-\d+(?:\(\d+\))?\b',  # AC-1, AC-2(1), etc.
            r'\b[A-Z]{2}\.\d+\b'              # AC.1, AC.2, etc.
        ]
        
        control_ids = set()
        combined_text = title + " " + text
        
        for pattern in patterns:
            matches = re.findall(pattern, combined_text)
            control_ids.update(matches)
        
        return list(control_ids)
    
    def _extract_field_value(self, text: str, field_names: List[str]) -> str:
        """Extract field value from text using field names"""
        for field_name in field_names:
            # Look for "field: value" patterns
            pattern = rf"{re.escape(field_name)}\s*:?\s*(.+?)(?:\n|$)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_fips199(self, text: str) -> Dict[str, str]:
        """Extract FIPS-199 categorization from text"""
        fips199 = {}
        
        # Look for CIA impact levels
        patterns = {
            "confidentiality": r"confidentiality\s*:?\s*(\w+)",
            "integrity": r"integrity\s*:?\s*(\w+)",
            "availability": r"availability\s*:?\s*(\w+)",
            "overall_impact": r"overall\s+impact\s*:?\s*(\w+)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fips199[key] = match.group(1).title()
        
        return fips199
    
    def _extract_diagrams(self, sections: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
        """Extract diagram references from sections"""
        diagrams = []
        
        for section in sections:
            title_lower = section.get("title", "").lower()
            for keyword in keywords:
                if keyword in title_lower:
                    diagram = {
                        "uuid": self.generate_uuid(),
                        "description": section.get("text", ""),
                        "caption": section.get("title", "")
                    }
                    diagrams.append(diagram)
                    break
        
        return diagrams
    
    def _extract_user_roles(self, text: str) -> List[Dict[str, Any]]:
        """Extract user roles from text (simplified)"""
        # This is a simplified implementation
        # In practice, this would use more sophisticated text processing
        roles = [
            {
                "title": "System Administrator",
                "description": "Administrative access to system components",
                "privileges": ["admin", "configure", "monitor"]
            },
            {
                "title": "System User", 
                "description": "Standard user access to system",
                "privileges": ["read", "write"]
            }
        ]
        
        return roles