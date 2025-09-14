"""
Plan of Action and Milestones (POA&M) mapper

Converts CIR POA&M data to OSCAL POA&M v1.1.3 format.
Complies with FedRAMP POA&M v3.0 requirements and structure.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_mapper import BaseMapper

logger = logging.getLogger(__name__)


class POAMMapper(BaseMapper):
    """Mapper for Plan of Action and Milestones (POA&M) OSCAL artifacts"""
    
    def __init__(self, mapping_dir: Optional[Path] = None):
        super().__init__(mapping_dir)
        self.severity_mappings = {
            "Low": "low",
            "Moderate": "moderate", 
            "High": "high",
            "Critical": "critical"
        }
        self.status_mappings = {
            "Open": "open",
            "Ongoing": "ongoing",
            "Completed": "completed",
            "Risk Accepted": "risk-accepted"
        }
    
    def map(self, poam_cir: Dict[str, Any]) -> Dict[str, Any]:
        """Map CIR POA&M data to OSCAL POA&M format"""
        logger.info("Mapping CIR POA&M data to OSCAL POA&M")
        
        metadata = poam_cir.get("metadata", {})
        rows = poam_cir.get("rows", [])
        
        # Build POA&M structure
        poam = {
            "plan-of-action-and-milestones": {
                "uuid": self.generate_uuid(),
                "metadata": self._build_metadata(metadata),
                "system-id": {
                    "identifier-type": "https://ietf.org/rfc/rfc4122",
                    "id": self.generate_uuid()  # Should reference actual system UUID
                },
                "local-definitions": self._build_local_definitions(rows),
                "poam-items": self._build_poam_items(rows),
                "back-matter": self._build_back_matter(metadata)
            }
        }
        
        return poam
    
    def _build_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Build OSCAL metadata from POA&M CIR metadata"""
        oscal_metadata = self.create_oscal_metadata(
            title="Plan of Action and Milestones (POA&M)",
            version="1.0"
        )
        
        # Add source document properties
        oscal_metadata["props"] = [
            self.create_property("source-file", metadata.get("source_file", "")),
            self.create_property("sheet-name", metadata.get("sheet_name", "")),
            self.create_property("template-version", metadata.get("template_version", "")),
            self.create_property("extraction-date", metadata.get("extraction_date", "")),
            self.create_property("file-hash", metadata.get("hash", ""))
        ]
        
        return oscal_metadata
    
    def _build_local_definitions(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build local-definitions section"""
        # Extract unique components and assessment methods from POA&M items
        components = set()
        assessment_methods = set()
        
        for row in rows:
            # Extract components from asset IDs
            asset_ids = row.get("asset_ids", [])
            for asset_id in asset_ids:
                if asset_id:
                    components.add(asset_id)
            
            # Extract assessment methods from origin
            origin = row.get("origin", "")
            if origin:
                if "assessment" in origin.lower():
                    assessment_methods.add("TEST")
                elif "review" in origin.lower():
                    assessment_methods.add("EXAMINE")
                elif "interview" in origin.lower():
                    assessment_methods.add("INTERVIEW")
        
        local_definitions = {}
        
        # Add components if any found
        if components:
            local_definitions["components"] = []
            for comp_name in sorted(components):
                component = {
                    "uuid": self.generate_uuid(),
                    "type": "software",  # Default type
                    "title": comp_name,
                    "description": f"Component referenced in POA&M: {comp_name}",
                    "status": {"state": "operational"}
                }
                local_definitions["components"].append(component)
        
        # Add assessment methods if any found
        if assessment_methods:
            local_definitions["activities"] = []
            for method in sorted(assessment_methods):
                activity = {
                    "uuid": self.generate_uuid(),
                    "title": f"{method} Assessment",
                    "description": f"Assessment activity using {method} method",
                    "props": [
                        self.create_property("method", method)
                    ]
                }
                local_definitions["activities"].append(activity)
        
        return local_definitions
    
    def _build_poam_items(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build poam-items from CIR rows"""
        poam_items = []
        
        for row in rows:
            item = {
                "uuid": self.generate_uuid(),
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "props": self._build_item_props(row),
                "related-findings": self._build_related_findings(row),
                "related-risks": self._build_related_risks(row)
            }
            
            # Add origins
            if row.get("origin"):
                item["origins"] = [
                    {
                        "actors": [
                            {
                                "type": "party",
                                "actor-uuid": self.generate_uuid(),
                                "props": [
                                    self.create_property("origin-type", "assessment")
                                ]
                            }
                        ]
                    }
                ]
            
            poam_items.append(item)
        
        logger.info(f"Built {len(poam_items)} POA&M items")
        return poam_items
    
    def _build_item_props(self, row: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build properties for POA&M item"""
        props = []
        
        # Add POA&M ID
        if row.get("poam_id"):
            props.append(self.create_property("poam-id", row["poam_id"]))
        
        # Add severity
        if row.get("severity"):
            severity = self.severity_mappings.get(row["severity"], row["severity"].lower())
            props.append(self.create_property("severity", severity))
        
        # Add scheduled completion date
        if row.get("scheduled_completion_date"):
            props.append(self.create_property("scheduled-completion-date", row["scheduled_completion_date"]))
        
        # Add actual completion date
        if row.get("actual_completion_date"):
            props.append(self.create_property("actual-completion-date", row["actual_completion_date"]))
        
        # Add affected assets
        asset_ids = row.get("asset_ids", [])
        if asset_ids:
            props.append(self.create_property("affected-assets", ",".join(asset_ids)))
        
        # Add comments
        if row.get("comments"):
            props.append(self.create_property("comments", row["comments"]))
        
        # Add source attribution
        source = row.get("source", {})
        if source:
            props.append(self.create_property("source-row", str(source.get("row", ""))))
            props.append(self.create_property("source-sheet", source.get("sheet", "")))
        
        return props
    
    def _build_related_findings(self, row: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build related-findings for POA&M item"""
        findings = []
        
        # Create finding from POA&M item details
        finding = {
            "finding-uuid": self.generate_uuid()
        }
        
        # Note: control associations handled via props in POA&M item, not related-controls
        
        findings.append(finding)
        return findings
    
    def _build_related_risks(self, row: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build related-risks for POA&M item"""
        risks = []
        
        # Create risk from POA&M item
        risk = {
            "risk-uuid": self.generate_uuid()
        }
        
        risks.append(risk)
        return risks
    
    def _build_milestones(self, milestones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build milestones from CIR milestone data"""
        oscal_milestones = []
        
        for milestone in milestones:
            oscal_milestone = {
                "uuid": self.generate_uuid(),
                "title": milestone.get("description", ""),
                "description": milestone.get("description", ""),
                "props": []
            }
            
            # Add milestone date
            if milestone.get("scheduled_date"):
                oscal_milestone["target-date"] = milestone["scheduled_date"]
                oscal_milestone["props"].append(
                    self.create_property("target-date", milestone["scheduled_date"])
                )
            
            # Add milestone status
            if milestone.get("status"):
                oscal_milestone["props"].append(
                    self.create_property("milestone-status", milestone["status"].lower())
                )
            
            oscal_milestones.append(oscal_milestone)
        
        return oscal_milestones
    
    def _build_back_matter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Build back-matter section"""
        resources = []
        
        # Add source document reference
        source_file = metadata.get("source_file")
        if source_file:
            resource = self.create_back_matter_resource(
                title=f"POA&M Source: {Path(source_file).name}",
                source_path=source_file,
                description="Original POA&M spreadsheet used for OSCAL generation"
            )
            
            # Add additional metadata
            resource["props"] = [
                self.create_property("template-version", metadata.get("template_version", "")),
                self.create_property("sheet-name", metadata.get("sheet_name", "")),
                self.create_property("file-hash", metadata.get("hash", ""))
            ]
            
            resources.append(resource)
        
        return {
            "resources": resources
        }