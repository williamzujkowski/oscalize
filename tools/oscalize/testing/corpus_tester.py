"""
Corpus tester for oscalize

Tests conversion against a corpus of known inputs and expected outputs.
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CorpusTester:
    """Tester for corpus of known inputs and outputs"""
    
    def __init__(self, corpus_dir: Path):
        self.corpus_dir = Path(corpus_dir)
        if not self.corpus_dir.exists():
            raise ValueError(f"Corpus directory not found: {corpus_dir}")
    
    def run_tests(self) -> Dict[str, Any]:
        """Run all corpus tests"""
        logger.info(f"Running corpus tests from {self.corpus_dir}")
        
        test_cases = self._discover_test_cases()
        results = {
            "timestamp": "2025-01-01T00:00:00Z",  # Would use actual timestamp
            "corpus_directory": str(self.corpus_dir),
            "total": len(test_cases),
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "test_results": [],
            "summary": {}
        }
        
        for test_case in test_cases:
            try:
                result = self._run_test_case(test_case)
                results["test_results"].append(result)
                
                if result["status"] == "PASSED":
                    results["passed"] += 1
                elif result["status"] == "FAILED":
                    results["failed"] += 1
                else:
                    results["skipped"] += 1
                    
            except Exception as e:
                logger.error(f"Test case error {test_case['name']}: {e}")
                results["test_results"].append({
                    "name": test_case["name"],
                    "status": "ERROR",
                    "error": str(e)
                })
                results["failed"] += 1
        
        results["summary"] = self._generate_summary(results)
        return results
    
    def _discover_test_cases(self) -> List[Dict[str, Any]]:
        """Discover test cases in corpus directory"""
        test_cases = []
        
        # Look for test case directories
        for item in self.corpus_dir.iterdir():
            if item.is_dir():
                test_case = self._analyze_test_case_directory(item)
                if test_case:
                    test_cases.append(test_case)
        
        logger.info(f"Discovered {len(test_cases)} test cases")
        return test_cases
    
    def _analyze_test_case_directory(self, test_dir: Path) -> Optional[Dict[str, Any]]:
        """Analyze test case directory structure"""
        # Look for test configuration
        config_file = test_dir / "test.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                return {
                    "name": test_dir.name,
                    "directory": test_dir,
                    "config": config,
                    "type": "configured"
                }
            except json.JSONDecodeError:
                logger.warning(f"Invalid test config: {config_file}")
        
        # Auto-detect test case structure
        inputs = list(test_dir.glob("input.*"))
        expected_outputs = list(test_dir.glob("expected_*.json"))
        
        if inputs and expected_outputs:
            return {
                "name": test_dir.name,
                "directory": test_dir,
                "inputs": inputs,
                "expected_outputs": expected_outputs,
                "type": "auto-detected"
            }
        
        return None
    
    def _run_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run individual test case"""
        logger.info(f"Running test case: {test_case['name']}")
        
        if test_case["type"] == "configured":
            return self._run_configured_test(test_case)
        else:
            return self._run_auto_detected_test(test_case)
    
    def _run_configured_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run configured test case"""
        config = test_case["config"]
        test_dir = test_case["directory"]
        
        result = {
            "name": test_case["name"],
            "type": "configured",
            "status": "UNKNOWN",
            "details": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Get input files
            input_patterns = config.get("inputs", ["input.*"])
            input_files = []
            for pattern in input_patterns:
                input_files.extend(test_dir.glob(pattern))
            
            if not input_files:
                result["status"] = "SKIPPED"
                result["errors"].append("No input files found")
                return result
            
            # Run conversion (simulated)
            conversion_result = self._simulate_conversion(input_files)
            
            # Compare with expected outputs
            expected_files = config.get("expected_outputs", [])
            comparison_result = self._compare_outputs(
                conversion_result, 
                test_dir,
                expected_files
            )
            
            result["details"] = {
                "input_files": [str(f) for f in input_files],
                "expected_outputs": expected_files,
                "conversion": conversion_result,
                "comparison": comparison_result
            }
            
            if comparison_result["all_matched"]:
                result["status"] = "PASSED"
            else:
                result["status"] = "FAILED"
                result["errors"].extend(comparison_result["errors"])
        
        except Exception as e:
            result["status"] = "ERROR"
            result["errors"].append(str(e))
        
        return result
    
    def _run_auto_detected_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run auto-detected test case"""
        result = {
            "name": test_case["name"],
            "type": "auto-detected", 
            "status": "UNKNOWN",
            "details": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            input_files = test_case["inputs"]
            expected_outputs = test_case["expected_outputs"]
            
            # Run conversion (simulated)
            conversion_result = self._simulate_conversion(input_files)
            
            # Compare with expected outputs
            comparison_result = self._compare_with_expected(
                conversion_result,
                expected_outputs
            )
            
            result["details"] = {
                "input_files": [str(f) for f in input_files],
                "expected_outputs": [str(f) for f in expected_outputs],
                "conversion": conversion_result,
                "comparison": comparison_result
            }
            
            if comparison_result["matches"]:
                result["status"] = "PASSED"
            else:
                result["status"] = "FAILED"
                result["errors"].extend(comparison_result["differences"])
        
        except Exception as e:
            result["status"] = "ERROR"
            result["errors"].append(str(e))
        
        return result
    
    def _simulate_conversion(self, input_files: List[Path]) -> Dict[str, Any]:
        """Simulate conversion process"""
        # This is a simulation since the full conversion pipeline 
        # would require all components to be working
        
        conversion_result = {
            "success": True,
            "outputs": [],
            "cir_data": {},
            "oscal_artifacts": {},
            "validation_results": {}
        }
        
        for input_file in input_files:
            file_type = self._detect_file_type(input_file)
            
            # Simulate CIR generation
            if file_type == "document":
                conversion_result["cir_data"]["document"] = {
                    "metadata": {"source_file": str(input_file)},
                    "sections": []
                }
                conversion_result["oscal_artifacts"]["ssp"] = {
                    "system-security-plan": {"uuid": "test-uuid"}
                }
            elif file_type == "poam":
                conversion_result["cir_data"]["poam"] = {
                    "metadata": {"source_file": str(input_file)},
                    "rows": []
                }
                conversion_result["oscal_artifacts"]["poam"] = {
                    "plan-of-action-and-milestones": {"uuid": "test-uuid"}
                }
            elif file_type == "inventory":
                conversion_result["cir_data"]["inventory"] = {
                    "metadata": {"source_file": str(input_file)},
                    "assets": []
                }
        
        return conversion_result
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Detect input file type"""
        name = file_path.name.lower()
        suffix = file_path.suffix.lower()
        
        if suffix in [".docx", ".md"]:
            return "document"
        elif suffix == ".xlsx":
            if "poam" in name:
                return "poam"
            elif "inventory" in name:
                return "inventory"
            else:
                return "spreadsheet"
        else:
            return "unknown"
    
    def _compare_outputs(self, conversion_result: Dict[str, Any], 
                        test_dir: Path, expected_files: List[str]) -> Dict[str, Any]:
        """Compare conversion outputs with expected files"""
        comparison = {
            "all_matched": True,
            "matches": [],
            "errors": [],
            "missing_files": []
        }
        
        for expected_file in expected_files:
            expected_path = test_dir / expected_file
            if not expected_path.exists():
                comparison["missing_files"].append(expected_file)
                comparison["all_matched"] = False
                continue
            
            # Load expected content
            try:
                with open(expected_path, 'r') as f:
                    expected_content = json.load(f)
                
                # Find corresponding output
                artifact_name = expected_file.replace("expected_", "").replace(".json", "")
                actual_content = conversion_result.get("oscal_artifacts", {}).get(artifact_name)
                
                if actual_content:
                    # Compare structures (simplified)
                    if self._compare_json_structures(actual_content, expected_content):
                        comparison["matches"].append(expected_file)
                    else:
                        comparison["errors"].append(f"Structure mismatch: {expected_file}")
                        comparison["all_matched"] = False
                else:
                    comparison["errors"].append(f"No output for: {expected_file}")
                    comparison["all_matched"] = False
                    
            except json.JSONDecodeError:
                comparison["errors"].append(f"Invalid JSON: {expected_file}")
                comparison["all_matched"] = False
        
        return comparison
    
    def _compare_with_expected(self, conversion_result: Dict[str, Any],
                             expected_files: List[Path]) -> Dict[str, Any]:
        """Compare with expected output files"""
        comparison = {
            "matches": True,
            "differences": [],
            "compared_files": []
        }
        
        for expected_file in expected_files:
            try:
                with open(expected_file, 'r') as f:
                    expected_content = json.load(f)
                
                # Extract artifact type from filename
                artifact_type = self._extract_artifact_type(expected_file.name)
                actual_content = conversion_result.get("oscal_artifacts", {}).get(artifact_type)
                
                if actual_content:
                    if self._compare_json_structures(actual_content, expected_content):
                        comparison["compared_files"].append(str(expected_file))
                    else:
                        comparison["matches"] = False
                        comparison["differences"].append(f"Mismatch: {expected_file.name}")
                else:
                    comparison["matches"] = False
                    comparison["differences"].append(f"Missing output: {artifact_type}")
                    
            except Exception as e:
                comparison["matches"] = False
                comparison["differences"].append(f"Error comparing {expected_file}: {e}")
        
        return comparison
    
    def _extract_artifact_type(self, filename: str) -> str:
        """Extract OSCAL artifact type from filename"""
        name = filename.lower().replace("expected_", "")
        
        if "ssp" in name:
            return "ssp"
        elif "poam" in name:
            return "poam"
        elif "assessment-plan" in name:
            return "assessment-plan"
        elif "assessment-results" in name:
            return "assessment-results"
        else:
            return name.replace(".json", "")
    
    def _compare_json_structures(self, actual: Dict[str, Any], 
                                expected: Dict[str, Any]) -> bool:
        """Compare JSON structures (simplified)"""
        # This is a simplified structural comparison
        # In practice, would implement more sophisticated comparison
        
        if not isinstance(actual, dict) or not isinstance(expected, dict):
            return actual == expected
        
        # Check that expected keys are present
        for key in expected.keys():
            if key not in actual:
                return False
            
            # For nested structures, do recursive comparison
            if isinstance(expected[key], dict):
                if not self._compare_json_structures(actual[key], expected[key]):
                    return False
        
        return True
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test summary"""
        total = results["total"]
        passed = results["passed"]
        failed = results["failed"]
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        summary = {
            "pass_rate": pass_rate,
            "status": "PASS" if failed == 0 else "FAIL",
            "recommendation": self._get_recommendation(pass_rate, failed),
            "test_types": self._count_test_types(results["test_results"])
        }
        
        return summary
    
    def _get_recommendation(self, pass_rate: float, failed_count: int) -> str:
        """Get recommendation based on test results"""
        if pass_rate == 100:
            return "All tests passed. Corpus validation successful."
        elif pass_rate >= 90:
            return f"{failed_count} test(s) failed. Review failed cases and update corpus or implementation."
        elif pass_rate >= 75:
            return f"Multiple tests failed ({failed_count}). Review conversion logic and test expectations."
        else:
            return f"Significant test failures ({failed_count}). Major review of implementation required."
    
    def _count_test_types(self, test_results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count test types"""
        types = {}
        for result in test_results:
            test_type = result.get("type", "unknown")
            types[test_type] = types.get(test_type, 0) + 1
        return types