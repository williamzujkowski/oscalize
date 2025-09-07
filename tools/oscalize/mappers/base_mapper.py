"""
Base mapper class for OSCAL conversions

Provides common functionality for all CIR to OSCAL mappers.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BaseMapper(ABC):
    """Base class for all CIR to OSCAL mappers"""
    
    OSCAL_VERSION = "1.1.3"
    
    def __init__(self, mapping_dir: Optional[Path] = None):
        self.mapping_dir = Path(mapping_dir) if mapping_dir else Path("mappings")
        self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def generate_uuid(self) -> str:
        """Generate UUID for OSCAL objects"""
        return str(uuid.uuid4())
    
    def create_oscal_metadata(self, title: str, **kwargs) -> Dict[str, Any]:
        """Create OSCAL metadata section"""
        metadata = {
            "title": title,
            "published": self.timestamp,
            "last-modified": self.timestamp,
            "version": kwargs.get("version", "1.0"),
            "oscal-version": self.OSCAL_VERSION
        }
        
        # Add parties if provided
        if "parties" in kwargs:
            metadata["parties"] = kwargs["parties"]
        
        # Add responsible parties if provided  
        if "responsible_parties" in kwargs:
            metadata["responsible-parties"] = kwargs["responsible_parties"]
        
        return metadata
    
    def create_party(self, name: str, party_type: str = "organization", 
                    uuid_val: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create OSCAL party object"""
        party = {
            "uuid": uuid_val or self.generate_uuid(),
            "type": party_type,
            "name": name
        }
        
        if "email" in kwargs:
            party["email-addresses"] = [{"address": kwargs["email"]}]
        
        if "phone" in kwargs:
            party["telephone-numbers"] = [{"number": kwargs["phone"]}]
        
        if "addresses" in kwargs:
            party["addresses"] = kwargs["addresses"]
        
        return party
    
    def create_property(self, name: str, value: str, **kwargs) -> Dict[str, Any]:
        """Create OSCAL property object"""
        prop = {
            "name": name,
            "value": value
        }
        
        if "ns" in kwargs:
            prop["ns"] = kwargs["ns"]
        
        if "class" in kwargs:
            prop["class"] = kwargs["class"]
        
        return prop
    
    def create_link(self, href: str, rel: str, **kwargs) -> Dict[str, Any]:
        """Create OSCAL link object"""
        link = {
            "href": href,
            "rel": rel
        }
        
        if "media_type" in kwargs:
            link["media-type"] = kwargs["media_type"]
        
        if "text" in kwargs:
            link["text"] = kwargs["text"]
        
        return link
    
    def create_annotation(self, name: str, value: str, **kwargs) -> Dict[str, Any]:
        """Create OSCAL annotation object"""
        annotation = {
            "name": name,
            "value": value
        }
        
        if "ns" in kwargs:
            annotation["ns"] = kwargs["ns"]
        
        return annotation
    
    def map_fips199_impact_level(self, cia_levels: Dict[str, str]) -> Dict[str, Any]:
        """Map FIPS-199 CIA levels to OSCAL security-impact-level"""
        confidentiality = cia_levels.get("confidentiality", "").lower()
        integrity = cia_levels.get("integrity", "").lower()
        availability = cia_levels.get("availability", "").lower()
        
        return {
            "security-impact-level": {
                "security-objective-confidentiality": confidentiality,
                "security-objective-integrity": integrity,
                "security-objective-availability": availability
            }
        }
    
    def extract_source_citation(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """Extract source citation information for back-matter"""
        citation = {
            "uuid": self.generate_uuid(),
            "title": f"Source: {Path(source['file']).name}",
            "props": [
                self.create_property("source-file", source["file"]),
                self.create_property("extraction-timestamp", self.timestamp)
            ]
        }
        
        # Add specific source coordinates
        if "sheet" in source:
            citation["props"].append(
                self.create_property("excel-sheet", source["sheet"])
            )
        
        if "row" in source:
            citation["props"].append(
                self.create_property("excel-row", str(source["row"]))
            )
        
        if "heading_path" in source:
            citation["props"].append(
                self.create_property("document-heading", " > ".join(source["heading_path"]))
            )
        
        return citation
    
    def create_back_matter_resource(self, title: str, source_path: str, 
                                  description: Optional[str] = None) -> Dict[str, Any]:
        """Create back-matter resource for source documents"""
        resource = {
            "uuid": self.generate_uuid(),
            "title": title,
            "rlinks": [
                {
                    "href": source_path
                }
            ]
        }
        
        if description:
            resource["description"] = description
        
        return resource
    
    @abstractmethod
    def map(self, cir_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map CIR data to OSCAL format"""
        pass
    
    def _load_mapping_config(self, config_name: str) -> Dict[str, Any]:
        """Load mapping configuration file"""
        config_path = self.mapping_dir / f"{config_name}.json"
        
        if config_path.exists():
            import json
            with open(config_path, 'r') as f:
                return json.load(f)
        
        return {}  # Return empty config if file doesn't exist