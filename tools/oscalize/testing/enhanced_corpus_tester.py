"""
Enhanced corpus tester for oscalize with real conversion integration

Provides comprehensive testing against a golden corpus of known inputs and expected outputs.
"""

import json
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

# Import oscalize components for real testing
try:
    from ..readers import DocumentReader, POAMReader, InventoryReader
    from ..mappers import SSPMapper, POAMMapper
    from ..validation import ValidationPipeline
except ImportError:
    # Fallback for direct execution
    pass

logger = logging.getLogger(__name__)


class EnhancedCorpusTester:
    """Enhanced corpus tester with real conversion and validation testing"""
    
    def __init__(self, 
                 corpus_dir: Path,
                 working_dir: Optional[Path] = None,
                 console: Optional[Console] = None):
        self.corpus_dir = Path(corpus_dir)
        self.working_dir = working_dir or (Path.cwd() / "temp_corpus_testing")
        self.console = console or Console()
        
        # Ensure directories exist
        self.corpus_dir.mkdir(parents=True, exist_ok=True)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        
        # Test components
        self.mapping_dir = Path("mappings")
        self.schema_dir = Path("schemas")
        
        # Results tracking
        self.test_results = []
        self.start_time = None
        
        logger.info(f"Enhanced corpus tester initialized: {self.corpus_dir}")
    
    def run_comprehensive_tests(self, 
                              include_validation: bool = True,
                              clean_working_dir: bool = True) -> Dict[str, Any]:
        """Run comprehensive corpus tests with real conversion and validation"""
        self.start_time = time.time()
        
        logger.info("Starting comprehensive corpus testing")
        
        try:
            # Clean working directory if requested
            if clean_working_dir:
                self._clean_working_dir()
            
            # Discover test cases
            test_cases = self._discover_enhanced_test_cases()
            
            if not test_cases:
                return self._create_no_tests_result()
            
            # Run tests with progress tracking
            results = self._run_test_suite(test_cases, include_validation)
            
            # Generate comprehensive report
            report = self._generate_comprehensive_report(results)
            
            # Save results
            self._save_test_results(report)
            
            # Display summary
            self._display_test_summary(report)
            
            return report
            
        except Exception as e:
            logger.exception(f"Comprehensive corpus testing failed: {e}")
            return self._create_error_result(str(e))
    
    def create_golden_corpus_entry(self, 
                                 input_files: List[Path],
                                 test_name: str,
                                 description: str = "",
                                 expected_validation_status: str = "COMPLIANT") -> Path:
        """Create a new golden corpus test case by running conversion and capturing outputs"""
        logger.info(f"Creating golden corpus entry: {test_name}")
        
        test_dir = self.corpus_dir / test_name
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy input files
        inputs_dir = test_dir / "inputs"
        inputs_dir.mkdir(exist_ok=True)
        
        copied_inputs = []
        for input_file in input_files:
            if input_file.exists():
                dest = inputs_dir / input_file.name
                shutil.copy2(input_file, dest)
                copied_inputs.append(dest)
                logger.info(f"Copied input: {input_file.name}")
        
        # Run conversion to generate golden outputs
        outputs_dir = test_dir / "expected_outputs"
        outputs_dir.mkdir(exist_ok=True)
        
        try:
            conversion_results = self._run_real_conversion(copied_inputs)
            
            # Save OSCAL artifacts as expected outputs
            for artifact_type, artifact_data in conversion_results.get("oscal_artifacts", {}).items():
                output_file = outputs_dir / f"{artifact_type}.json"
                with open(output_file, 'w') as f:
                    json.dump(artifact_data, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved expected output: {output_file.name}")
            
            # Run validation and save results
            if conversion_results.get("validation_results"):
                validation_file = outputs_dir / "validation_results.json"
                with open(validation_file, 'w') as f:
                    json.dump(conversion_results["validation_results"], f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to generate golden outputs: {e}")
            # Create placeholder expected outputs
            placeholder_file = outputs_dir / "ERROR_GENERATING_OUTPUTS.txt"
            with open(placeholder_file, 'w') as f:
                f.write(f"Error generating golden outputs: {str(e)}\n")
                f.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n")
        
        # Create test configuration
        test_config = {
            "name": test_name,
            "description": description,
            "created": datetime.utcnow().isoformat() + "Z",
            "input_files": [f"inputs/{f.name}" for f in copied_inputs],
            "expected_outputs": [f"expected_outputs/{f.name}" for f in outputs_dir.glob("*.json")],
            "expected_validation_status": expected_validation_status,
            "test_type": "golden_corpus",
            "metadata": {
                "oscal_version": "1.1.3",
                "oscalize_version": "1.0",
                "generator": "enhanced_corpus_tester"
            }
        }
        
        config_file = test_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(test_config, f, indent=2)
        
        logger.info(f"Golden corpus entry created: {test_dir}")
        return test_dir
    
    def validate_corpus_integrity(self) -> Dict[str, Any]:
        """Validate the integrity and completeness of the corpus"""
        logger.info("Validating corpus integrity")
        
        integrity_report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "corpus_directory": str(self.corpus_dir),
            "total_test_cases": 0,
            "valid_test_cases": 0,
            "invalid_test_cases": 0,
            "missing_files": [],
            "integrity_issues": [],
            "recommendations": []
        }
        
        if not self.corpus_dir.exists():
            integrity_report["integrity_issues"].append("Corpus directory does not exist")
            integrity_report["recommendations"].append("Create corpus directory and add test cases")
            return integrity_report
        
        test_cases = self._discover_enhanced_test_cases()
        integrity_report["total_test_cases"] = len(test_cases)
        
        for test_case in test_cases:
            issues = self._validate_test_case_integrity(test_case)
            if issues:
                integrity_report["invalid_test_cases"] += 1
                integrity_report["integrity_issues"].extend(issues)
            else:
                integrity_report["valid_test_cases"] += 1
        
        # Add recommendations
        if integrity_report["invalid_test_cases"] > 0:
            integrity_report["recommendations"].append(
                f"Fix {integrity_report['invalid_test_cases']} invalid test cases"
            )
        
        if integrity_report["total_test_cases"] < 5:
            integrity_report["recommendations"].append(
                "Add more test cases to improve coverage"
            )
        
        logger.info(f"Corpus integrity check completed: {integrity_report['valid_test_cases']}/{integrity_report['total_test_cases']} valid")
        return integrity_report
    
    def _discover_enhanced_test_cases(self) -> List[Dict[str, Any]]:
        """Discover enhanced test cases with comprehensive metadata"""
        test_cases = []
        
        if not self.corpus_dir.exists():
            logger.warning(f"Corpus directory not found: {self.corpus_dir}")
            return test_cases
        
        for item in self.corpus_dir.iterdir():
            if item.is_dir():
                test_case = self._analyze_enhanced_test_case(item)
                if test_case:
                    test_cases.append(test_case)
        
        logger.info(f"Discovered {len(test_cases)} enhanced test cases")
        return test_cases
    
    def _analyze_enhanced_test_case(self, test_dir: Path) -> Optional[Dict[str, Any]]:
        """Analyze enhanced test case with comprehensive structure"""
        # Look for test configuration first
        config_file = test_dir / "test_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                return {
                    "name": test_dir.name,
                    "directory": test_dir,
                    "config": config,
                    "type": "configured_enhanced",
                    "input_files": [test_dir / f for f in config.get("input_files", [])],
                    "expected_outputs": [test_dir / f for f in config.get("expected_outputs", [])],
                    "validation_status": config.get("expected_validation_status", "COMPLIANT")
                }
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid enhanced test config in {test_dir}: {e}")
        
        # Fall back to auto-detection
        inputs_dir = test_dir / "inputs"
        outputs_dir = test_dir / "expected_outputs"
        
        if inputs_dir.exists() and outputs_dir.exists():
            input_files = list(inputs_dir.glob("*"))
            expected_outputs = list(outputs_dir.glob("*.json"))
            
            if input_files and expected_outputs:
                return {
                    "name": test_dir.name,
                    "directory": test_dir,
                    "type": "auto_detected_enhanced",
                    "input_files": input_files,
                    "expected_outputs": expected_outputs,
                    "validation_status": "COMPLIANT"  # Default assumption
                }
        
        return None
    
    def _run_test_suite(self, test_cases: List[Dict[str, Any]], 
                       include_validation: bool) -> Dict[str, Any]:
        """Run comprehensive test suite with progress tracking"""
        
        results = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_tests": len(test_cases),
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "test_results": [],
            "execution_time": None,
            "include_validation": include_validation
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            task = progress.add_task(
                f"Running {len(test_cases)} corpus tests...",
                total=len(test_cases)
            )
            
            for test_case in test_cases:
                progress.update(task, description=f"Testing {test_case['name']}...")
                
                try:
                    test_result = self._run_enhanced_test_case(test_case, include_validation)
                    results["test_results"].append(test_result)
                    
                    if test_result["status"] == "PASSED":
                        results["passed"] += 1
                    elif test_result["status"] == "FAILED":
                        results["failed"] += 1
                    else:
                        results["errors"] += 1
                
                except Exception as e:
                    logger.exception(f"Test case error {test_case['name']}: {e}")
                    error_result = {
                        "name": test_case["name"],
                        "status": "ERROR",
                        "error": str(e),
                        "execution_time": 0
                    }
                    results["test_results"].append(error_result)
                    results["errors"] += 1
                
                progress.advance(task)
        
        results["execution_time"] = time.time() - self.start_time if self.start_time else 0
        return results
    
    def _run_enhanced_test_case(self, test_case: Dict[str, Any], 
                              include_validation: bool) -> Dict[str, Any]:
        """Run individual enhanced test case with real conversion"""
        
        test_start = time.time()
        logger.info(f"Running enhanced test case: {test_case['name']}")
        
        result = {
            "name": test_case["name"],
            "type": test_case["type"],
            "status": "UNKNOWN",
            "conversion_success": False,
            "validation_success": False,
            "output_matches": False,
            "details": {},
            "errors": [],
            "warnings": [],
            "execution_time": 0
        }
        
        try:
            # Create temporary working directory for this test
            test_work_dir = self.working_dir / f"test_{test_case['name']}"
            test_work_dir.mkdir(parents=True, exist_ok=True)
            
            # Run real conversion
            conversion_result = self._run_real_conversion(test_case["input_files"])
            result["conversion_success"] = conversion_result.get("success", False)
            
            if not result["conversion_success"]:
                result["status"] = "FAILED"
                result["errors"].append("Conversion failed")
                result["details"]["conversion_errors"] = conversion_result.get("errors", [])
                return result
            
            # Save actual outputs for comparison
            actual_outputs = {}
            for artifact_type, artifact_data in conversion_result.get("oscal_artifacts", {}).items():
                output_file = test_work_dir / f"{artifact_type}.json"
                with open(output_file, 'w') as f:
                    json.dump(artifact_data, f, indent=2, ensure_ascii=False)
                actual_outputs[artifact_type] = artifact_data
            
            # Compare with expected outputs
            comparison_result = self._compare_with_golden_outputs(
                actual_outputs, 
                test_case["expected_outputs"]
            )
            result["output_matches"] = comparison_result["all_match"]
            result["details"]["comparison"] = comparison_result
            
            # Run validation if requested
            if include_validation:
                validation_result = self._run_validation_test(
                    test_work_dir, 
                    test_case.get("validation_status", "COMPLIANT")
                )
                result["validation_success"] = validation_result["success"]
                result["details"]["validation"] = validation_result
            
            # Determine overall status
            if result["conversion_success"] and result["output_matches"]:
                if not include_validation or result["validation_success"]:
                    result["status"] = "PASSED"
                else:
                    result["status"] = "FAILED"
                    result["errors"].append("Validation failed")
            else:
                result["status"] = "FAILED"
                if not result["output_matches"]:
                    result["errors"].append("Output comparison failed")
        
        except Exception as e:
            result["status"] = "ERROR"
            result["errors"].append(str(e))
        
        result["execution_time"] = time.time() - test_start
        return result
    
    def _run_real_conversion(self, input_files: List[Path]) -> Dict[str, Any]:
        """Run real conversion using oscalize components"""
        logger.debug(f"Running real conversion on {len(input_files)} files")
        
        conversion_result = {
            "success": False,
            "cir_data": {},
            "oscal_artifacts": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Process each input file
            for input_file in input_files:
                if not input_file.exists():
                    conversion_result["errors"].append(f"Input file not found: {input_file}")
                    continue
                
                try:
                    if input_file.suffix.lower() in ['.docx', '.md']:
                        reader = DocumentReader(input_file)
                        conversion_result["cir_data"]["document"] = reader.to_cir()
                        
                    elif input_file.name.lower().startswith('poam') and input_file.suffix.lower() == '.xlsx':
                        reader = POAMReader(input_file)
                        conversion_result["cir_data"]["poam"] = reader.to_cir()
                        
                    elif input_file.name.lower().startswith('inventory') and input_file.suffix.lower() == '.xlsx':
                        reader = InventoryReader(input_file)
                        conversion_result["cir_data"]["inventory"] = reader.to_cir()
                        
                except Exception as e:
                    conversion_result["errors"].append(f"Failed to read {input_file.name}: {str(e)}")
                    continue
            
            # Convert CIR to OSCAL if we have data
            if conversion_result["cir_data"]:
                try:
                    # Map to OSCAL
                    if "document" in conversion_result["cir_data"]:
                        ssp_mapper = SSPMapper(self.mapping_dir)
                        conversion_result["oscal_artifacts"]["ssp"] = ssp_mapper.map(conversion_result["cir_data"])
                    
                    if "poam" in conversion_result["cir_data"]:
                        poam_mapper = POAMMapper(self.mapping_dir)
                        conversion_result["oscal_artifacts"]["poam"] = poam_mapper.map(conversion_result["cir_data"]["poam"])
                    
                    conversion_result["success"] = True
                    
                except Exception as e:
                    conversion_result["errors"].append(f"OSCAL mapping failed: {str(e)}")
            
            else:
                conversion_result["errors"].append("No valid CIR data generated from inputs")
        
        except Exception as e:
            conversion_result["errors"].append(f"Conversion error: {str(e)}")
        
        return conversion_result
    
    def _compare_with_golden_outputs(self, actual_outputs: Dict[str, Any],
                                   expected_output_files: List[Path]) -> Dict[str, Any]:
        """Compare actual outputs with golden outputs"""
        
        comparison = {
            "all_match": True,
            "matches": [],
            "mismatches": [],
            "missing_expected": [],
            "unexpected_outputs": []
        }
        
        # Load expected outputs
        expected_outputs = {}
        for expected_file in expected_output_files:
            if expected_file.exists() and expected_file.suffix == ".json":
                try:
                    with open(expected_file, 'r') as f:
                        content = json.load(f)
                    artifact_type = expected_file.stem
                    expected_outputs[artifact_type] = content
                except json.JSONDecodeError as e:
                    comparison["mismatches"].append(f"Invalid JSON in {expected_file.name}: {e}")
                    comparison["all_match"] = False
        
        # Compare each expected output
        for artifact_type, expected_content in expected_outputs.items():
            actual_content = actual_outputs.get(artifact_type)
            
            if actual_content:
                # Perform structural comparison
                if self._deep_compare_oscal(actual_content, expected_content):
                    comparison["matches"].append(artifact_type)
                else:
                    comparison["mismatches"].append(f"Structure mismatch in {artifact_type}")
                    comparison["all_match"] = False
            else:
                comparison["missing_expected"].append(artifact_type)
                comparison["all_match"] = False
        
        # Check for unexpected outputs
        for artifact_type in actual_outputs:
            if artifact_type not in expected_outputs:
                comparison["unexpected_outputs"].append(artifact_type)
        
        return comparison
    
    def _deep_compare_oscal(self, actual: Any, expected: Any, path: str = "") -> bool:
        """Deep comparison of OSCAL structures with intelligent flexibility"""
        
        # Handle different types
        if type(actual) != type(expected):
            return False
        
        if isinstance(expected, dict):
            # Check required keys exist
            for key, value in expected.items():
                if key not in actual:
                    return False
                
                # Skip comparison for certain dynamic fields
                skip_fields = ["uuid", "published", "last-modified", "timestamp"]
                if key in skip_fields:
                    continue
                
                if not self._deep_compare_oscal(actual[key], value, f"{path}.{key}"):
                    return False
            
            return True
        
        elif isinstance(expected, list):
            # For lists, check length and compare elements
            if len(actual) != len(expected):
                return False
            
            for i, (actual_item, expected_item) in enumerate(zip(actual, expected)):
                if not self._deep_compare_oscal(actual_item, expected_item, f"{path}[{i}]"):
                    return False
            
            return True
        
        else:
            # Direct comparison for primitives
            return actual == expected
    
    def _run_validation_test(self, test_dir: Path, expected_status: str) -> Dict[str, Any]:
        """Run validation test on outputs"""
        
        validation_result = {
            "success": False,
            "status": "UNKNOWN",
            "expected_status": expected_status,
            "validation_output": {},
            "errors": []
        }
        
        try:
            # Use ValidationPipeline to validate outputs (use local validation when in container)
            pipeline = ValidationPipeline(test_dir)
            results = pipeline.run_complete_validation(use_docker=False, show_progress=False)
            
            actual_status = results.get("compliance_analysis", {}).get("status", "UNKNOWN")
            validation_result["status"] = actual_status
            validation_result["validation_output"] = results
            
            # Check if status matches expectation
            if actual_status == expected_status:
                validation_result["success"] = True
            else:
                validation_result["errors"].append(
                    f"Status mismatch: expected {expected_status}, got {actual_status}"
                )
        
        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def _validate_test_case_integrity(self, test_case: Dict[str, Any]) -> List[str]:
        """Validate integrity of a single test case"""
        issues = []
        
        # Check input files exist
        for input_file in test_case.get("input_files", []):
            if not input_file.exists():
                issues.append(f"Missing input file: {input_file}")
        
        # Check expected output files exist
        for output_file in test_case.get("expected_outputs", []):
            if not output_file.exists():
                issues.append(f"Missing expected output: {output_file}")
            elif output_file.suffix == ".json":
                try:
                    with open(output_file, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError:
                    issues.append(f"Invalid JSON in expected output: {output_file}")
        
        return issues
    
    def _generate_comprehensive_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        total = results["total_tests"]
        passed = results["passed"]
        failed = results["failed"]
        errors = results["errors"]
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        report = {
            "report_metadata": {
                "title": "Enhanced Corpus Testing Report",
                "generated": datetime.utcnow().isoformat() + "Z",
                "generator": "enhanced_corpus_tester",
                "version": "1.0"
            },
            "executive_summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "pass_rate": pass_rate,
                "execution_time": results.get("execution_time", 0),
                "status": "PASS" if failed == 0 and errors == 0 else "FAIL"
            },
            "test_results": results["test_results"],
            "analysis": {
                "test_categories": self._analyze_test_categories(results["test_results"]),
                "failure_patterns": self._analyze_failure_patterns(results["test_results"]),
                "performance_metrics": self._analyze_performance(results["test_results"])
            },
            "recommendations": self._generate_test_recommendations(pass_rate, failed, errors)
        }
        
        return report
    
    def _analyze_test_categories(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze test results by category"""
        categories = {}
        
        for result in test_results:
            category = result.get("type", "unknown")
            if category not in categories:
                categories[category] = {"total": 0, "passed": 0, "failed": 0, "errors": 0}
            
            categories[category]["total"] += 1
            
            status = result.get("status", "UNKNOWN")
            if status == "PASSED":
                categories[category]["passed"] += 1
            elif status == "FAILED":
                categories[category]["failed"] += 1
            else:
                categories[category]["errors"] += 1
        
        return categories
    
    def _analyze_failure_patterns(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in test failures"""
        patterns = {
            "conversion_failures": 0,
            "validation_failures": 0,
            "output_mismatches": 0,
            "common_errors": {}
        }
        
        for result in test_results:
            if result.get("status") in ["FAILED", "ERROR"]:
                if not result.get("conversion_success", True):
                    patterns["conversion_failures"] += 1
                
                if result.get("conversion_success") and not result.get("validation_success", True):
                    patterns["validation_failures"] += 1
                
                if result.get("conversion_success") and not result.get("output_matches", True):
                    patterns["output_mismatches"] += 1
                
                # Track common error messages
                for error in result.get("errors", []):
                    if error not in patterns["common_errors"]:
                        patterns["common_errors"][error] = 0
                    patterns["common_errors"][error] += 1
        
        return patterns
    
    def _analyze_performance(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance metrics"""
        execution_times = [r.get("execution_time", 0) for r in test_results if r.get("execution_time")]
        
        if execution_times:
            return {
                "average_execution_time": sum(execution_times) / len(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "total_execution_time": sum(execution_times)
            }
        else:
            return {"note": "No execution time data available"}
    
    def _generate_test_recommendations(self, pass_rate: float, failed: int, errors: int) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if pass_rate == 100:
            recommendations.append("✅ All tests passing - corpus validation successful")
            recommendations.append("Consider adding more diverse test cases to improve coverage")
        else:
            if failed > 0:
                recommendations.append(f"🔍 Review {failed} failed test(s) - check for logic changes or corpus updates needed")
            if errors > 0:
                recommendations.append(f"🚨 Fix {errors} test error(s) - likely infrastructure or code issues")
            
            if pass_rate < 50:
                recommendations.append("🔧 Major issues detected - review core conversion logic")
            elif pass_rate < 90:
                recommendations.append("📝 Update test expectations or fix implementation gaps")
        
        return recommendations
    
    def _save_test_results(self, report: Dict[str, Any]) -> None:
        """Save test results to files"""
        results_dir = self.working_dir / "test_results"
        results_dir.mkdir(exist_ok=True)
        
        # Save comprehensive report
        report_file = results_dir / "corpus_test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Test results saved: {report_file}")
    
    def _display_test_summary(self, report: Dict[str, Any]) -> None:
        """Display test summary with rich formatting"""
        summary = report["executive_summary"]
        
        self.console.print("\n🧪 [bold blue]Enhanced Corpus Testing Results[/bold blue]")
        
        # Summary table
        table = Table(title="Test Summary", style="cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Value", style="green")
        
        table.add_row("Total Tests", str(summary["total_tests"]))
        table.add_row("Passed", str(summary["passed"]))
        table.add_row("Failed", str(summary["failed"]))
        table.add_row("Errors", str(summary["errors"]))
        table.add_row("Pass Rate", f"{summary['pass_rate']:.1f}%")
        table.add_row("Execution Time", f"{summary['execution_time']:.2f}s")
        table.add_row("Status", summary["status"])
        
        self.console.print(table)
        
        # Show recommendations
        if report.get("recommendations"):
            self.console.print("\n[bold yellow]Recommendations:[/bold yellow]")
            for rec in report["recommendations"]:
                self.console.print(f"  {rec}")
    
    def _clean_working_dir(self) -> None:
        """Clean working directory"""
        if self.working_dir.exists():
            shutil.rmtree(self.working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_no_tests_result(self) -> Dict[str, Any]:
        """Create result when no tests found"""
        return {
            "report_metadata": {
                "title": "Enhanced Corpus Testing Report",
                "generated": datetime.utcnow().isoformat() + "Z",
                "status": "NO_TESTS"
            },
            "executive_summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "pass_rate": 0,
                "status": "NO_TESTS"
            },
            "recommendations": [
                "Create test cases using create_golden_corpus_entry()",
                "Add input files and expected outputs to corpus directory",
                "Ensure test cases follow the enhanced corpus structure"
            ]
        }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result"""
        return {
            "report_metadata": {
                "title": "Enhanced Corpus Testing Report",
                "generated": datetime.utcnow().isoformat() + "Z",
                "status": "ERROR"
            },
            "executive_summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "pass_rate": 0,
                "status": "ERROR",
                "error": error_message
            },
            "recommendations": [
                "Fix corpus testing infrastructure",
                "Check dependencies and file permissions",
                "Review error logs for detailed diagnostics"
            ]
        }