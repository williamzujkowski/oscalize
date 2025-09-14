"""
Compliance checker for M-24-15, FedRAMP and other requirements

Checks OSCAL artifacts against compliance requirements and standards.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ComplianceChecker:
    """Checker for compliance against various standards"""
    
    def __init__(self):
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        
        # M-24-15 requirements
        self.m24_15_requirements = {
            "machine_readable": True,
            "standardized_format": "OSCAL",
            "automated_processing": True,
            "required_artifacts": ["system-security-plan"]
        }
        
        # FedRAMP requirements
        self.fedramp_requirements = {
            "required_artifacts": [
                "system-security-plan",
                "plan-of-action-and-milestones"
            ],
            "attachments": [
                "integrated_inventory_workbook",
                "customer_responsibility_matrix"
            ],
            "baseline_profiles": [
                "fedramp-low",
                "fedramp-moderate", 
                "fedramp-high"
            ]
        }
        
        # NIST SP 800-53 requirements
        self.nist_800_53_requirements = {
            "version": "rev5",
            "required_control_families": [
                "AC", "AT", "AU", "CA", "CM", "CP", "IA", "IR", 
                "MA", "MP", "PE", "PL", "PS", "RA", "SA", "SC", "SI", "SR"
            ]
        }
    
    def check_directory(self, directory: Path) -> Dict[str, Any]:
        """Check all OSCAL artifacts in directory for compliance"""
        logger.info(f"Checking compliance for directory: {directory}")
        
        if not directory.exists():
            return self._create_error_result(f"Directory not found: {directory}")
        
        # Discover OSCAL artifacts
        artifacts = self._discover_oscal_artifacts(directory)
        
        compliance_report = {
            "compliance_check": {
                "timestamp": self.timestamp,
                "directory": str(directory),
                "artifacts_found": len(artifacts),
                "compliant": True,
                "compliance_score": 0.0,
                "checks_performed": {},
                "violations": [],
                "recommendations": [],
                "summary": {}
            }
        }
        
        if not artifacts:
            compliance_report["compliance_check"]["compliant"] = False
            compliance_report["compliance_check"]["violations"].append(
                "No OSCAL artifacts found for compliance checking"
            )
            return compliance_report
        
        # Perform compliance checks
        checks = [
            ("M-24-15", self._check_m24_15_compliance),
            ("FedRAMP", self._check_fedramp_compliance),
            ("NIST SP 800-53", self._check_nist_800_53_compliance),
            ("OSCAL Format", self._check_oscal_format_compliance)
        ]
        
        total_score = 0
        max_score = len(checks) * 100
        
        for check_name, check_function in checks:
            try:
                result = check_function(artifacts)
                compliance_report["compliance_check"]["checks_performed"][check_name] = result
                
                total_score += result.get("score", 0)
                
                if not result.get("compliant", False):
                    compliance_report["compliance_check"]["compliant"] = False
                
                # Collect violations and recommendations
                compliance_report["compliance_check"]["violations"].extend(
                    result.get("violations", [])
                )
                compliance_report["compliance_check"]["recommendations"].extend(
                    result.get("recommendations", [])
                )
                
            except Exception as e:
                logger.error(f"Compliance check {check_name} failed: {e}")
                compliance_report["compliance_check"]["violations"].append(
                    f"Compliance check error ({check_name}): {str(e)}"
                )
                compliance_report["compliance_check"]["compliant"] = False
        
        # Calculate overall compliance score
        compliance_report["compliance_check"]["compliance_score"] = (
            (total_score / max_score * 100) if max_score > 0 else 0
        )
        
        # Generate summary
        compliance_report["compliance_check"]["summary"] = self._generate_summary(
            compliance_report["compliance_check"]
        )
        
        return compliance_report
    
    def _discover_oscal_artifacts(self, directory: Path) -> List[Dict[str, Any]]:
        """Discover OSCAL artifacts in directory"""
        artifacts = []
        
        for file_path in directory.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    content = json.load(f)
                
                artifact_type = self._identify_oscal_artifact_type(content)
                if artifact_type:
                    artifacts.append({
                        "file": str(file_path),
                        "type": artifact_type,
                        "content": content
                    })
                    
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read {file_path}: {e}")
        
        logger.info(f"Discovered {len(artifacts)} OSCAL artifacts")
        return artifacts
    
    def _identify_oscal_artifact_type(self, content: Dict[str, Any]) -> Optional[str]:
        """Identify OSCAL artifact type from content"""
        oscal_types = {
            "system-security-plan": "system-security-plan",
            "plan-of-action-and-milestones": "plan-of-action-and-milestones",
            "assessment-plan": "assessment-plan",
            "assessment-results": "assessment-results",
            "component-definition": "component-definition",
            "profile": "profile",
            "catalog": "catalog"
        }
        
        for key in content.keys():
            if key in oscal_types:
                return oscal_types[key]
        
        return None
    
    def _check_m24_15_compliance(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check OMB M-24-15 compliance requirements"""
        result = {
            "compliant": True,
            "score": 0,
            "violations": [],
            "recommendations": [],
            "details": {}
        }
        
        # Check for machine-readable format
        if artifacts:
            result["score"] += 25
            result["details"]["machine_readable"] = True
        else:
            result["compliant"] = False
            result["violations"].append("No machine-readable OSCAL artifacts found")
            result["details"]["machine_readable"] = False
        
        # Check for standardized OSCAL format
        oscal_artifacts = [a for a in artifacts if a["type"] in [
            "system-security-plan", "plan-of-action-and-milestones",
            "assessment-plan", "assessment-results"
        ]]
        
        if oscal_artifacts:
            result["score"] += 25
            result["details"]["standardized_format"] = True
        else:
            result["compliant"] = False
            result["violations"].append("No standardized OSCAL artifacts found")
            result["details"]["standardized_format"] = False
        
        # Check for automated processing support
        valid_artifacts = self._count_valid_artifacts(artifacts)
        if valid_artifacts == len(artifacts):
            result["score"] += 25
            result["details"]["automated_processing"] = True
        else:
            result["violations"].append(
                f"Some artifacts may not support automated processing ({valid_artifacts}/{len(artifacts)} valid)"
            )
            result["details"]["automated_processing"] = False
        
        # Check for required SSP
        ssp_artifacts = [a for a in artifacts if a["type"] == "system-security-plan"]
        if ssp_artifacts:
            result["score"] += 25
            result["details"]["required_ssp"] = True
        else:
            result["compliant"] = False
            result["violations"].append("Required System Security Plan not found")
            result["details"]["required_ssp"] = False
        
        # Add recommendations
        if result["score"] < 100:
            if not result["details"]["machine_readable"]:
                result["recommendations"].append("Generate machine-readable OSCAL artifacts")
            if not result["details"]["required_ssp"]:
                result["recommendations"].append("Create System Security Plan in OSCAL format")
        
        return result
    
    def _check_fedramp_compliance(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check FedRAMP compliance requirements"""
        result = {
            "compliant": True,
            "score": 0,
            "violations": [],
            "recommendations": [],
            "details": {}
        }
        
        # Check for required artifacts
        artifact_types = {a["type"] for a in artifacts}
        
        # SSP required
        if "system-security-plan" in artifact_types:
            result["score"] += 40
            result["details"]["ssp_present"] = True
        else:
            result["compliant"] = False
            result["violations"].append("FedRAMP requires System Security Plan")
            result["details"]["ssp_present"] = False
        
        # POA&M required
        if "plan-of-action-and-milestones" in artifact_types:
            result["score"] += 40
            result["details"]["poam_present"] = True
        else:
            result["compliant"] = False
            result["violations"].append("FedRAMP requires Plan of Action and Milestones")
            result["details"]["poam_present"] = False
        
        # Check for FedRAMP-specific content
        fedramp_content_score = self._check_fedramp_content(artifacts)
        result["score"] += fedramp_content_score
        result["details"]["fedramp_content_score"] = fedramp_content_score
        
        if fedramp_content_score < 20:
            result["violations"].append("Artifacts lack FedRAMP-specific content")
        
        # Add recommendations
        if not result["details"]["ssp_present"]:
            result["recommendations"].append("Create FedRAMP System Security Plan")
        if not result["details"]["poam_present"]:
            result["recommendations"].append("Create Plan of Action and Milestones")
        if fedramp_content_score < 20:
            result["recommendations"].append("Enhance artifacts with FedRAMP-specific content")
        
        return result
    
    def _check_nist_800_53_compliance(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check NIST SP 800-53 compliance"""
        result = {
            "compliant": True,
            "score": 0,
            "violations": [],
            "recommendations": [],
            "details": {}
        }
        
        # Find SSP artifacts for control analysis
        ssp_artifacts = [a for a in artifacts if a["type"] == "system-security-plan"]
        
        if not ssp_artifacts:
            result["compliant"] = False
            result["violations"].append("No SSP found for NIST SP 800-53 control analysis")
            result["details"]["controls_implemented"] = 0
            return result
        
        # Analyze control implementations
        implemented_controls = set()
        control_families = set()
        
        for ssp in ssp_artifacts:
            controls = self._extract_implemented_controls(ssp["content"])
            implemented_controls.update(controls)
            
            # Extract control families
            for control_id in controls:
                if "-" in control_id:
                    family = control_id.split("-")[0]
                    control_families.add(family)
        
        result["details"]["implemented_controls"] = len(implemented_controls)
        result["details"]["control_families"] = list(control_families)
        
        # Score based on control coverage
        required_families = set(self.nist_800_53_requirements["required_control_families"])
        family_coverage = len(control_families.intersection(required_families)) / len(required_families)
        
        result["score"] = int(family_coverage * 100)
        
        if family_coverage < 0.8:
            result["compliant"] = False
            missing_families = required_families - control_families
            result["violations"].append(
                f"Insufficient control family coverage: missing {', '.join(sorted(missing_families))}"
            )
        
        if len(implemented_controls) < 50:  # Arbitrary threshold
            result["violations"].append("Low number of implemented controls")
            result["recommendations"].append("Implement more NIST SP 800-53 controls")
        
        return result
    
    def _check_oscal_format_compliance(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check OSCAL format compliance"""
        result = {
            "compliant": True,
            "score": 0,
            "violations": [],
            "recommendations": [],
            "details": {}
        }
        
        if not artifacts:
            result["compliant"] = False
            result["violations"].append("No artifacts to check for OSCAL format compliance")
            return result
        
        valid_artifacts = 0
        
        for artifact in artifacts:
            if self._validate_oscal_structure(artifact["content"]):
                valid_artifacts += 1
        
        compliance_rate = valid_artifacts / len(artifacts)
        result["score"] = int(compliance_rate * 100)
        result["details"]["valid_artifacts"] = valid_artifacts
        result["details"]["total_artifacts"] = len(artifacts)
        result["details"]["compliance_rate"] = compliance_rate
        
        if compliance_rate < 1.0:
            result["compliant"] = False
            invalid_count = len(artifacts) - valid_artifacts
            result["violations"].append(f"{invalid_count} artifacts have OSCAL format issues")
            result["recommendations"].append("Fix OSCAL format validation errors")
        
        return result
    
    def _count_valid_artifacts(self, artifacts: List[Dict[str, Any]]) -> int:
        """Count artifacts that appear valid for automated processing"""
        valid_count = 0
        
        for artifact in artifacts:
            if self._validate_oscal_structure(artifact["content"]):
                valid_count += 1
        
        return valid_count
    
    def _validate_oscal_structure(self, content: Dict[str, Any]) -> bool:
        """Basic OSCAL structure validation"""
        # Find OSCAL root element
        oscal_root = None
        for key, value in content.items():
            if key in ["system-security-plan", "plan-of-action-and-milestones",
                      "assessment-plan", "assessment-results", "component-definition"]:
                oscal_root = value
                break
        
        if not oscal_root:
            return False
        
        # Check for required fields
        required_fields = ["uuid", "metadata"]
        for field in required_fields:
            if field not in oscal_root:
                return False
        
        # Check metadata structure
        metadata = oscal_root.get("metadata", {})
        if not isinstance(metadata, dict) or "title" not in metadata:
            return False
        
        return True
    
    def _check_fedramp_content(self, artifacts: List[Dict[str, Any]]) -> int:
        """Check for FedRAMP-specific content and return score 0-20"""
        # Look for FedRAMP-specific elements (4 points each, max 20)
        fedramp_indicators = [
            "fedramp",
            "cloud service provider",
            "authorization boundary", 
            "fips 199",
            "customer responsibility matrix"
        ]
        
        # Track which indicators have been found to avoid double counting
        found_indicators = set()
        
        for artifact in artifacts:
            content_str = json.dumps(artifact["content"]).lower()
            for indicator in fedramp_indicators:
                if indicator in content_str:
                    found_indicators.add(indicator)
        
        # Award 4 points for each unique indicator found
        score = len(found_indicators) * 4
        return min(score, 20)  # Cap at 20 points
    
    def _extract_implemented_controls(self, ssp_content: Dict[str, Any]) -> List[str]:
        """Extract implemented control IDs from SSP"""
        controls = []
        
        # Navigate to control implementation section
        ssp = ssp_content.get("system-security-plan", {})
        control_impl = ssp.get("control-implementation", {})
        implemented_reqs = control_impl.get("implemented-requirements", [])
        
        for req in implemented_reqs:
            control_id = req.get("control-id")
            if control_id:
                controls.append(control_id)
        
        return controls
    
    def _generate_summary(self, compliance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate compliance summary"""
        score = compliance_data.get("compliance_score", 0)
        compliant = compliance_data.get("compliant", False)
        violations_count = len(compliance_data.get("violations", []))
        
        summary = {
            "overall_status": "COMPLIANT" if compliant else "NON_COMPLIANT",
            "compliance_score": f"{score:.1f}%",
            "violations_count": violations_count,
            "readiness_level": self._assess_readiness_level(score, compliant),
            "next_steps": self._recommend_next_steps(score, violations_count),
            "priority_actions": self._identify_priority_actions(compliance_data)
        }
        
        return summary
    
    def _assess_readiness_level(self, score: float, compliant: bool) -> str:
        """Assess readiness level"""
        if compliant and score >= 95:
            return "PRODUCTION_READY"
        elif compliant and score >= 85:
            return "NEAR_READY"
        elif score >= 70:
            return "DEVELOPMENT"
        else:
            return "INITIAL"
    
    def _recommend_next_steps(self, score: float, violations_count: int) -> List[str]:
        """Recommend next steps"""
        steps = []
        
        if violations_count > 0:
            steps.append("Address compliance violations")
        
        if score < 85:
            steps.append("Improve compliance score to 85% or higher")
        
        if score >= 85:
            steps.append("Review recommendations for final optimization")
            steps.append("Prepare for compliance review")
        
        return steps
    
    def _identify_priority_actions(self, compliance_data: Dict[str, Any]) -> List[str]:
        """Identify priority actions from compliance checks"""
        priority_actions = []
        
        checks = compliance_data.get("checks_performed", {})
        
        # M-24-15 priorities
        m24_15 = checks.get("M-24-15", {})
        if not m24_15.get("details", {}).get("machine_readable", True):
            priority_actions.append("Generate machine-readable OSCAL artifacts")
        
        # FedRAMP priorities
        fedramp = checks.get("FedRAMP", {})
        if not fedramp.get("details", {}).get("ssp_present", True):
            priority_actions.append("Create System Security Plan")
        if not fedramp.get("details", {}).get("poam_present", True):
            priority_actions.append("Create Plan of Action and Milestones")
        
        # OSCAL format priorities
        oscal_format = checks.get("OSCAL Format", {})
        if not oscal_format.get("compliant", True):
            priority_actions.append("Fix OSCAL format validation errors")
        
        return priority_actions[:5]  # Return top 5 priorities
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result"""
        return {
            "compliance_check": {
                "timestamp": self.timestamp,
                "compliant": False,
                "compliance_score": 0.0,
                "error": error_message,
                "violations": [error_message],
                "recommendations": ["Fix the underlying issue and re-run compliance check"]
            }
        }