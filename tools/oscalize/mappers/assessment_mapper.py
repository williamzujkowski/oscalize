"""
Assessment mapper

Converts assessment data to OSCAL Assessment Plan (AP) and Assessment Results (AR) formats.
Handles Security Assessment Plan and Security Assessment Report conversions.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_mapper import BaseMapper

logger = logging.getLogger(__name__)


class AssessmentMapper(BaseMapper):
    """Mapper for assessment documents to OSCAL AP and AR artifacts"""
    
    def __init__(self, mapping_dir: Optional[Path] = None):
        super().__init__(mapping_dir)
        self.assessment_method_mappings = {
            "test": "TEST",
            "examine": "EXAMINE", 
            "interview": "INTERVIEW"
        }
    
    def map_assessment_plan(self, cir_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map CIR data to OSCAL Assessment Plan"""
        logger.info("Mapping CIR data to OSCAL Assessment Plan")
        
        document = cir_data.get("document", {})
        metadata = document.get("metadata", {})
        sections = document.get("sections", [])
        
        # Build Assessment Plan structure
        assessment_plan = {
            "assessment-plan": {
                "uuid": self.generate_uuid(),
                "metadata": self._build_ap_metadata(metadata),
                "import-ssp": self._build_import_ssp(),
                "local-definitions": self._build_ap_local_definitions(sections),
                "terms-and-conditions": self._build_terms_and_conditions(sections),
                "reviewed-controls": self._build_reviewed_controls(sections),
                "assessment-subjects": self._build_assessment_subjects(sections),
                "assessment-assets": self._build_assessment_assets(sections),
                "tasks": self._build_assessment_tasks(sections),
                "back-matter": self._build_back_matter(metadata)
            }
        }
        
        return assessment_plan
    
    def map_assessment_results(self, cir_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map CIR data to OSCAL Assessment Results"""
        logger.info("Mapping CIR data to OSCAL Assessment Results")
        
        document = cir_data.get("document", {})
        metadata = document.get("metadata", {})
        sections = document.get("sections", [])
        
        # Build Assessment Results structure
        assessment_results = {
            "assessment-results": {
                "uuid": self.generate_uuid(),
                "metadata": self._build_ar_metadata(metadata),
                "import-ap": self._build_import_ap(),
                "local-definitions": self._build_ar_local_definitions(sections),
                "results": self._build_results(sections),
                "back-matter": self._build_back_matter(metadata)
            }
        }
        
        return assessment_results
    
    def _build_ap_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Build metadata for Assessment Plan"""
        oscal_metadata = self.create_oscal_metadata(
            title="Security Assessment Plan",
            version="1.0"
        )
        
        # Add source document properties
        oscal_metadata["props"] = [
            self.create_property("document-type", "assessment-plan"),
            self.create_property("source-file", metadata.get("source_file", "")),
            self.create_property("source-type", metadata.get("source_type", "")),
            self.create_property("extraction-date", metadata.get("extraction_date", "")),
            self.create_property("file-hash", metadata.get("hash", ""))
        ]
        
        return oscal_metadata
    
    def _build_ar_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Build metadata for Assessment Results"""
        oscal_metadata = self.create_oscal_metadata(
            title="Security Assessment Report",
            version="1.0"
        )
        
        # Add source document properties
        oscal_metadata["props"] = [
            self.create_property("document-type", "assessment-results"),
            self.create_property("source-file", metadata.get("source_file", "")),
            self.create_property("source-type", metadata.get("source_type", "")),
            self.create_property("extraction-date", metadata.get("extraction_date", "")),
            self.create_property("file-hash", metadata.get("hash", ""))
        ]
        
        return oscal_metadata
    
    def _build_import_ssp(self) -> Dict[str, Any]:
        """Build import-ssp reference"""
        return {
            "href": "./ssp.json",
            "description": "Reference to the System Security Plan"
        }
    
    def _build_import_ap(self) -> Dict[str, Any]:
        """Build import-ap reference"""
        return {
            "href": "./assessment-plan.json", 
            "description": "Reference to the Assessment Plan"
        }
    
    def _build_ap_local_definitions(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build local definitions for Assessment Plan"""
        local_definitions = {}
        
        # Extract assessment methods from sections
        methods = self._extract_assessment_methods(sections)
        if methods:
            local_definitions["activities"] = []
            for method_name, method_data in methods.items():
                activity = {
                    "uuid": self.generate_uuid(),
                    "title": method_data.get("title", method_name),
                    "description": method_data.get("description", ""),
                    "props": [
                        self.create_property("method", method_name)
                    ]
                }
                
                if method_data.get("steps"):
                    activity["steps"] = []
                    for step_text in method_data["steps"]:
                        step = {
                            "uuid": self.generate_uuid(),
                            "title": step_text[:50] + "..." if len(step_text) > 50 else step_text,
                            "description": step_text
                        }
                        activity["steps"].append(step)
                
                local_definitions["activities"].append(activity)
        
        return local_definitions
    
    def _build_ar_local_definitions(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build local definitions for Assessment Results"""
        local_definitions = {}
        
        # Extract findings from sections
        findings_data = self._extract_findings(sections)
        if findings_data:
            local_definitions["findings"] = findings_data
        
        return local_definitions
    
    def _build_terms_and_conditions(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build terms and conditions section"""
        # Find terms and conditions text
        terms_text = self._extract_section_text(
            sections, 
            ["terms and conditions", "assumptions", "constraints", "limitations"]
        )
        
        return {
            "description": terms_text or "Terms and conditions not specified in source document."
        }
    
    def _build_reviewed_controls(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build reviewed controls section"""
        # Extract control scope from sections
        control_scope = self._extract_control_scope(sections)
        
        return {
            "description": "Controls to be reviewed during assessment",
            "props": [
                self.create_property("scope", control_scope.get("scope", "full"))
            ],
            "control-selections": control_scope.get("selections", [])
        }
    
    def _build_assessment_subjects(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build assessment subjects"""
        subjects = []
        
        # Extract subjects from sections
        subject_info = self._extract_subjects(sections)
        
        for subject_data in subject_info:
            subject = {
                "uuid": self.generate_uuid(),
                "type": subject_data.get("type", "component"),
                "title": subject_data.get("title", ""),
                "description": subject_data.get("description", ""),
                "props": []
            }
            
            if subject_data.get("include_all"):
                subject["include-all"] = {}
            
            subjects.append(subject)
        
        return subjects
    
    def _build_assessment_assets(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build assessment assets"""
        assets = []
        
        # Extract assessment tools and resources
        asset_info = self._extract_assessment_assets(sections)
        
        for asset_data in asset_info:
            asset = {
                "uuid": self.generate_uuid(),
                "title": asset_data.get("title", ""),
                "description": asset_data.get("description", ""),
                "props": []
            }
            
            if asset_data.get("asset_type"):
                asset["props"].append(
                    self.create_property("asset-type", asset_data["asset_type"])
                )
            
            assets.append(asset)
        
        return assets
    
    def _build_assessment_tasks(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build assessment tasks"""
        tasks = []
        
        # Extract assessment procedures
        task_info = self._extract_assessment_tasks(sections)
        
        for task_data in task_info:
            task = {
                "uuid": self.generate_uuid(),
                "type": "action",
                "title": task_data.get("title", ""),
                "description": task_data.get("description", ""),
                "props": [],
                "timing": task_data.get("timing", {}),
                "dependencies": task_data.get("dependencies", [])
            }
            
            if task_data.get("associated_activities"):
                task["associated-activities"] = []
                for activity_ref in task_data["associated_activities"]:
                    task["associated-activities"].append({
                        "activity-uuid": activity_ref,
                        "subjects": [{"subject-uuid": self.generate_uuid()}]
                    })
            
            tasks.append(task)
        
        return tasks
    
    def _build_results(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build assessment results"""
        results = []
        
        # Extract findings and observations
        findings = self._extract_findings(sections)
        observations = self._extract_observations(sections)
        
        # Create result entry
        result = {
            "uuid": self.generate_uuid(),
            "title": "Assessment Results",
            "description": "Results from security assessment activities",
            "start": self.timestamp,
            "end": self.timestamp,  # Should be actual end time
            "props": [
                self.create_property("assessment-status", "complete")
            ],
            "findings": findings,
            "observations": observations
        }
        
        results.append(result)
        return results
    
    def _build_back_matter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Build back-matter section"""
        resources = []
        
        # Add source document reference
        source_file = metadata.get("source_file")
        if source_file:
            resource = self.create_back_matter_resource(
                title=f"Assessment Source: {Path(source_file).name}",
                source_path=source_file,
                description="Original assessment document used for OSCAL generation"
            )
            resources.append(resource)
        
        return {
            "resources": resources
        }
    
    # Helper methods for extraction
    
    def _extract_section_text(self, sections: List[Dict[str, Any]], keywords: List[str]) -> Optional[str]:
        """Extract text from sections matching keywords"""
        for section in sections:
            title_lower = section.get("title", "").lower()
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    return section.get("text", "")
        return None
    
    def _extract_assessment_methods(self, sections: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract assessment methods from sections"""
        methods = {}
        
        for section in sections:
            title_lower = section.get("title", "").lower()
            text = section.get("text", "")
            
            # Look for method keywords
            if any(method in title_lower for method in ["test", "examine", "interview"]):
                method_type = None
                if "test" in title_lower:
                    method_type = "TEST"
                elif "examine" in title_lower:
                    method_type = "EXAMINE"
                elif "interview" in title_lower:
                    method_type = "INTERVIEW"
                
                if method_type and method_type not in methods:
                    methods[method_type] = {
                        "title": section.get("title", ""),
                        "description": text,
                        "steps": self._extract_steps(text)
                    }
        
        return methods
    
    def _extract_steps(self, text: str) -> List[str]:
        """Extract procedure steps from text"""
        # Simple extraction of numbered or bulleted lists
        import re
        
        # Look for numbered steps
        numbered_steps = re.findall(r'^\s*\d+\.?\s+(.+?)(?=^\s*\d+\.|\Z)', text, re.MULTILINE | re.DOTALL)
        if numbered_steps:
            return [step.strip() for step in numbered_steps]
        
        # Look for bulleted steps
        bulleted_steps = re.findall(r'^\s*[•\-\*]\s+(.+?)(?=^\s*[•\-\*]|\Z)', text, re.MULTILINE | re.DOTALL)
        if bulleted_steps:
            return [step.strip() for step in bulleted_steps]
        
        # No clear steps found
        return []
    
    def _extract_control_scope(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract control scope from sections"""
        scope_data = {"scope": "full", "selections": []}
        
        for section in sections:
            title_lower = section.get("title", "").lower()
            if "scope" in title_lower or "control" in title_lower:
                # Simple scope extraction
                text = section.get("text", "").lower()
                if "all controls" in text or "complete" in text:
                    scope_data["scope"] = "full"
                elif "selected" in text or "subset" in text:
                    scope_data["scope"] = "selective"
        
        return scope_data
    
    def _extract_subjects(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract assessment subjects from sections"""
        subjects = []
        
        # Default subject for system-wide assessment
        subjects.append({
            "type": "inventory-item",
            "title": "System Components", 
            "description": "All system components subject to assessment",
            "include_all": True
        })
        
        return subjects
    
    def _extract_assessment_assets(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract assessment assets/tools from sections"""
        assets = []
        
        for section in sections:
            title_lower = section.get("title", "").lower()
            if "tool" in title_lower or "resource" in title_lower or "asset" in title_lower:
                assets.append({
                    "title": section.get("title", ""),
                    "description": section.get("text", "")[:200] + "..." if len(section.get("text", "")) > 200 else section.get("text", ""),
                    "asset_type": "tool"
                })
        
        return assets
    
    def _extract_assessment_tasks(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract assessment tasks from sections"""
        tasks = []
        
        for section in sections:
            title_lower = section.get("title", "").lower()
            if "procedure" in title_lower or "task" in title_lower or "activity" in title_lower:
                tasks.append({
                    "title": section.get("title", ""),
                    "description": section.get("text", ""),
                    "timing": {"period": {"start": self.timestamp}},
                    "dependencies": [],
                    "associated_activities": []
                })
        
        return tasks
    
    def _extract_findings(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract findings from sections"""
        findings = []
        
        for section in sections:
            title_lower = section.get("title", "").lower()
            if "finding" in title_lower or "deficiency" in title_lower or "issue" in title_lower:
                finding = {
                    "uuid": self.generate_uuid(),
                    "title": section.get("title", ""),
                    "description": section.get("text", ""),
                    "props": [
                        self.create_property("finding-type", "deficiency")
                    ]
                }
                findings.append(finding)
        
        return findings
    
    def _extract_observations(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract observations from sections"""
        observations = []
        
        for section in sections:
            title_lower = section.get("title", "").lower()
            if "observation" in title_lower or "result" in title_lower:
                observation = {
                    "uuid": self.generate_uuid(),
                    "title": section.get("title", ""),
                    "description": section.get("text", ""),
                    "methods": ["EXAMINE"],  # Default method
                    "types": ["finding"]
                }
                observations.append(observation)
        
        return observations