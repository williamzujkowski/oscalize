"""
Validation reporter

Generates reports from OSCAL validation results.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ValidationReporter:
    """Reporter for OSCAL validation results"""
    
    def __init__(self, validation_dir: Path):
        self.validation_dir = Path(validation_dir)
        self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive validation summary"""
        logger.info(f"Generating validation summary from {self.validation_dir}")
        
        if not self.validation_dir.exists():
            return self._create_empty_summary()
        
        # Collect all validation log files
        log_files = list(self.validation_dir.glob("*.log"))
        
        if not log_files:
            logger.warning(f"No validation log files found in {self.validation_dir}")
            return self._create_empty_summary()
        
        summary = {
            "summary": {
                "timestamp": self.timestamp,
                "validation_directory": str(self.validation_dir),
                "total_files": len(log_files),
                "valid_files": 0,
                "invalid_files": 0,
                "files_with_warnings": 0
            },
            "results": [],
            "must_fix": [],
            "nice_to_have": [],
            "compliance_gaps": [],
            "evidence_notes": []
        }
        
        # Process each log file
        for log_file in log_files:
            result = self._process_log_file(log_file)
            summary["results"].append(result)
            
            # Update counters
            if result["valid"]:
                summary["summary"]["valid_files"] += 1
            else:
                summary["summary"]["invalid_files"] += 1
            
            if result["warnings"]:
                summary["summary"]["files_with_warnings"] += 1
            
            # Categorize issues
            self._categorize_issues(result, summary)
        
        # Add compliance analysis
        summary["compliance_analysis"] = self._analyze_compliance(summary["results"])
        
        return summary
    
    def generate_detailed_report(self) -> Dict[str, Any]:
        """Generate detailed validation report"""
        summary = self.generate_summary()
        
        detailed_report = {
            "report_metadata": {
                "title": "OSCAL Validation Detailed Report",
                "generated": self.timestamp,
                "generator": "oscalize validation reporter",
                "version": "1.0"
            },
            "executive_summary": self._generate_executive_summary(summary),
            "validation_results": summary,
            "recommendations": self._generate_recommendations(summary),
            "appendices": {
                "fedramp_checklist_status": self._check_fedramp_requirements(summary),
                "m24_15_compliance": self._check_m24_15_compliance(summary),
                "sp_800_53_gaps": self._identify_sp_800_53_gaps(summary)
            }
        }
        
        return detailed_report
    
    def export_must_fix_checklist(self) -> List[Dict[str, Any]]:
        """Export must-fix items as actionable checklist"""
        summary = self.generate_summary()
        
        checklist = []
        counter = 1
        
        for item in summary["must_fix"]:
            checklist_item = {
                "id": f"MUST-FIX-{counter:03d}",
                "priority": "CRITICAL",
                "title": item["title"],
                "description": item["description"],
                "file": item.get("file", ""),
                "line": item.get("line", ""),
                "action_required": item.get("action", "Review and fix"),
                "status": "OPEN",
                "assigned_to": "",
                "due_date": "",
                "notes": ""
            }
            checklist.append(checklist_item)
            counter += 1
        
        return checklist
    
    def _process_log_file(self, log_file: Path) -> Dict[str, Any]:
        """Process individual validation log file"""
        try:
            with open(log_file, 'r') as f:
                log_content = f.read()
        except IOError as e:
            logger.error(f"Failed to read log file {log_file}: {e}")
            return self._create_error_result(str(log_file), f"Failed to read log: {e}")
        
        # Parse log content
        result = {
            "file": log_file.stem,  # Remove .log extension
            "log_file": str(log_file),
            "valid": self._is_validation_successful(log_content),
            "errors": self._extract_errors(log_content),
            "warnings": self._extract_warnings(log_content),
            "info": self._extract_info(log_content),
            "raw_output": log_content
        }
        
        return result
    
    def _is_validation_successful(self, log_content: str) -> bool:
        """Determine if validation was successful"""
        content_lower = log_content.lower()
        
        # Check for success indicators
        success_indicators = [
            "valid",
            "validation successful",
            "no errors found",
            "passed"
        ]
        
        # Check for failure indicators  
        failure_indicators = [
            "error",
            "invalid",
            "failed",
            "validation failed",
            "schema validation error"
        ]
        
        # If any failure indicators are found, it's invalid
        for indicator in failure_indicators:
            if indicator in content_lower:
                return False
        
        # If success indicators are found, it's valid
        for indicator in success_indicators:
            if indicator in content_lower:
                return True
        
        # If empty or unclear, assume invalid
        return len(log_content.strip()) == 0
    
    def _extract_errors(self, log_content: str) -> List[str]:
        """Extract error messages from log content"""
        errors = []
        lines = log_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ["error", "invalid", "failed"]):
                errors.append(line)
        
        return errors
    
    def _extract_warnings(self, log_content: str) -> List[str]:
        """Extract warning messages from log content"""
        warnings = []
        lines = log_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if "warning" in line.lower():
                warnings.append(line)
        
        return warnings
    
    def _extract_info(self, log_content: str) -> List[str]:
        """Extract informational messages from log content"""
        info = []
        lines = log_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            # Info messages are lines that aren't errors or warnings
            if not any(keyword in line_lower for keyword in ["error", "warning", "invalid", "failed"]):
                if any(keyword in line_lower for keyword in ["info", "valid", "success", "passed"]):
                    info.append(line)
        
        return info
    
    def _categorize_issues(self, result: Dict[str, Any], summary: Dict[str, Any]) -> None:
        """Categorize validation issues into must-fix vs nice-to-have"""
        file_name = result["file"]
        
        # Process errors (must-fix)
        for error in result["errors"]:
            must_fix_item = {
                "title": f"Validation Error in {file_name}",
                "description": error,
                "file": file_name,
                "severity": "ERROR",
                "category": "schema_validation",
                "action": "Fix validation error to ensure OSCAL compliance"
            }
            summary["must_fix"].append(must_fix_item)
        
        # Process warnings (nice-to-have)
        for warning in result["warnings"]:
            nice_to_have_item = {
                "title": f"Validation Warning in {file_name}",
                "description": warning,
                "file": file_name,
                "severity": "WARNING",
                "category": "best_practice",
                "action": "Consider addressing to improve OSCAL quality"
            }
            summary["nice_to_have"].append(nice_to_have_item)
    
    def _analyze_compliance(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze compliance status across all results"""
        total_files = len(results)
        valid_files = sum(1 for r in results if r["valid"])
        
        compliance_score = (valid_files / total_files * 100) if total_files > 0 else 0
        
        analysis = {
            "overall_compliance": compliance_score,
            "status": "COMPLIANT" if compliance_score == 100 else "NON_COMPLIANT",
            "total_files": total_files,
            "valid_files": valid_files,
            "invalid_files": total_files - valid_files,
            "readiness_assessment": self._assess_readiness(compliance_score),
            "next_steps": self._recommend_next_steps(compliance_score)
        }
        
        return analysis
    
    def _assess_readiness(self, compliance_score: float) -> str:
        """Assess readiness for submission/deployment"""
        if compliance_score == 100:
            return "READY - All OSCAL artifacts validated successfully"
        elif compliance_score >= 90:
            return "NEARLY_READY - Minor issues require resolution"
        elif compliance_score >= 75:
            return "REQUIRES_WORK - Significant validation issues present"
        else:
            return "NOT_READY - Major validation failures must be addressed"
    
    def _recommend_next_steps(self, compliance_score: float) -> List[str]:
        """Recommend next steps based on compliance score"""
        if compliance_score == 100:
            return [
                "Proceed with OSCAL artifact deployment",
                "Consider automated validation in CI/CD pipeline",
                "Review artifacts with stakeholders for final approval"
            ]
        else:
            steps = [
                "Review and fix all MUST-FIX validation errors",
                "Address NICE-TO-HAVE warnings where feasible",
                "Re-run validation after fixes",
                "Update source documents if structural changes needed"
            ]
            
            if compliance_score < 75:
                steps.insert(0, "Review OSCAL structure and mapping configuration")
            
            return steps
    
    def _generate_executive_summary(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary"""
        total_files = summary["summary"]["total_files"]
        valid_files = summary["summary"]["valid_files"]
        must_fix_count = len(summary["must_fix"])
        
        return {
            "title": "OSCAL Validation Executive Summary",
            "overview": f"Validated {total_files} OSCAL artifacts with {valid_files} passing validation",
            "key_findings": [
                f"{must_fix_count} critical issues require immediate attention",
                f"{len(summary['nice_to_have'])} improvement opportunities identified",
                f"Overall compliance score: {summary['compliance_analysis']['overall_compliance']:.1f}%"
            ],
            "recommendation": summary["compliance_analysis"]["readiness_assessment"]
        }
    
    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Critical recommendations
        if summary["must_fix"]:
            recommendations.append({
                "priority": "CRITICAL",
                "title": "Resolve Validation Errors",
                "description": f"Address {len(summary['must_fix'])} critical validation errors blocking compliance",
                "actions": ["Review error details in validation logs", "Update source documents or mapping configuration", "Re-run validation to verify fixes"]
            })
        
        # Nice-to-have recommendations
        if summary["nice_to_have"]:
            recommendations.append({
                "priority": "MEDIUM",
                "title": "Address Validation Warnings", 
                "description": f"Consider resolving {len(summary['nice_to_have'])} warnings to improve OSCAL quality",
                "actions": ["Review warning details", "Implement best practices", "Enhance documentation quality"]
            })
        
        return recommendations
    
    def _check_fedramp_requirements(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Check against FedRAMP requirements"""
        # This is a placeholder for FedRAMP-specific checks
        return {
            "status": "PENDING_REVIEW",
            "required_artifacts": ["SSP", "POA&M", "IIW"],
            "present_artifacts": [r["file"] for r in summary["results"]],
            "missing_artifacts": [],  # Would be computed based on requirements
            "compliance_notes": ["Manual review required for FedRAMP Initial Authorization Package completeness"]
        }
    
    def _check_m24_15_compliance(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Check M-24-15 compliance"""
        return {
            "machine_readable": summary["summary"]["valid_files"] > 0,
            "automation_ready": summary["compliance_analysis"]["overall_compliance"] == 100,
            "status": "COMPLIANT" if summary["compliance_analysis"]["status"] == "COMPLIANT" else "NON_COMPLIANT",
            "notes": ["OSCAL artifacts support M-24-15 automation requirements when validation passes"]
        }
    
    def _identify_sp_800_53_gaps(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Identify SP 800-53 implementation gaps"""
        return {
            "status": "AUTOMATED_ANALYSIS_LIMITED",
            "notes": [
                "Control implementation analysis requires manual review",
                "POA&M items may indicate control gaps", 
                "Review control-implementation sections in SSP for completeness"
            ],
            "recommendations": [
                "Cross-reference POA&M findings with control implementations",
                "Ensure all required controls are documented",
                "Validate control implementation descriptions for completeness"
            ]
        }
    
    def _create_empty_summary(self) -> Dict[str, Any]:
        """Create empty summary structure"""
        return {
            "summary": {
                "timestamp": self.timestamp,
                "validation_directory": str(self.validation_dir),
                "total_files": 0,
                "valid_files": 0,
                "invalid_files": 0,
                "files_with_warnings": 0
            },
            "results": [],
            "must_fix": [],
            "nice_to_have": [],
            "compliance_gaps": [],
            "evidence_notes": [],
            "compliance_analysis": {
                "overall_compliance": 0,
                "status": "NO_FILES_FOUND",
                "readiness_assessment": "No validation files found"
            }
        }
    
    def _create_error_result(self, file_name: str, error_message: str) -> Dict[str, Any]:
        """Create error result for failed log processing"""
        return {
            "file": file_name,
            "log_file": file_name,
            "valid": False,
            "errors": [error_message],
            "warnings": [],
            "info": [],
            "raw_output": error_message
        }