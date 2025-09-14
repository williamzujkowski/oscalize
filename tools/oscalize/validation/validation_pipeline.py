"""
Enhanced OSCAL validation pipeline with comprehensive error reporting and logging

Orchestrates the complete validation workflow with detailed logging, error categorization,
and actionable feedback for OSCAL v1.1.3 compliance.
"""

import json
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from .oscal_validator import OSCALValidator
from .validation_reporter import ValidationReporter

logger = logging.getLogger(__name__)

# Timeout constants (in seconds)
DOCKER_CHECK_TIMEOUT = 10
DOCKER_VALIDATION_TIMEOUT = 120


class ValidationPipeline:
    """Enhanced OSCAL validation pipeline with comprehensive error reporting"""
    
    def __init__(self, 
                 oscal_dir: Path,
                 validation_dir: Optional[Path] = None,
                 console: Optional[Console] = None):
        self.oscal_dir = Path(oscal_dir)
        self.validation_dir = validation_dir or (self.oscal_dir / "validation")
        self.console = console or Console()
        
        # Create validation directory
        self.validation_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.validator = None
        self.reporter = ValidationReporter(self.validation_dir)
        
        # Pipeline state
        self.start_time = None
        self.results = {}
        
        # Setup enhanced logging
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup enhanced logging for validation pipeline"""
        log_file = self.validation_dir / "validation_pipeline.log"
        
        # Create file handler
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Add to logger
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)
        
        logger.info("Validation pipeline logging initialized")
    
    def run_complete_validation(self, 
                              use_docker: bool = False,
                              oscal_cli_path: str = "oscal-cli",
                              show_progress: bool = True) -> Dict[str, Any]:
        """Run complete validation pipeline with enhanced error reporting"""
        self.start_time = time.time()
        
        with self.console.status("[bold green]Initializing validation pipeline...") as status:
            logger.info("Starting enhanced OSCAL validation pipeline")
            logger.info(f"OSCAL directory: {self.oscal_dir}")
            logger.info(f"Validation directory: {self.validation_dir}")
            
            try:
                # Phase 1: Environment setup and validation
                status.update("[bold blue]Setting up validation environment...")
                self._validate_environment(use_docker, oscal_cli_path)
                
                # Phase 2: Discover and validate OSCAL files
                status.update("[bold blue]Discovering OSCAL files...")
                oscal_files = self._discover_oscal_files()
                
                if not oscal_files:
                    return self._create_no_files_result()
                
                # Phase 3: Run validation for each file
                status.update("[bold blue]Running OSCAL validation...")
                validation_results = self._run_validation_batch(oscal_files, use_docker, oscal_cli_path, show_progress)
                
                # Phase 4: Generate comprehensive reports
                status.update("[bold blue]Generating validation reports...")
                summary = self._generate_enhanced_summary(validation_results)
                
                # Phase 5: Create actionable outputs
                status.update("[bold blue]Creating actionable outputs...")
                self._create_actionable_outputs(summary)
                
                # Phase 6: Display results
                self._display_results(summary)
                
                logger.info("Validation pipeline completed successfully")
                return summary
                
            except Exception as e:
                logger.exception(f"Validation pipeline failed: {e}")
                self.console.print(f"[red]Validation pipeline failed: {e}[/red]")
                return self._create_error_result(str(e))
    
    def _validate_environment(self, use_docker: bool, oscal_cli_path: str) -> None:
        """Validate that validation environment is properly set up"""
        logger.info("Validating validation environment")
        
        # Check OSCAL directory exists
        if not self.oscal_dir.exists():
            raise RuntimeError(f"OSCAL directory not found: {self.oscal_dir}")
        
        # Check validation tools
        if use_docker:
            self._check_docker_availability()
        else:
            self._check_oscal_cli(oscal_cli_path)
        
        logger.info("Environment validation passed")
    
    def _check_docker_availability(self) -> None:
        """Check if Docker is available for containerized validation"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=DOCKER_CHECK_TIMEOUT
            )
            logger.info(f"Docker available: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            raise RuntimeError("Docker not available for containerized validation")
    
    def _check_oscal_cli(self, oscal_cli_path: str) -> None:
        """Check if oscal-cli is available"""
        try:
            result = subprocess.run(
                [oscal_cli_path, "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=DOCKER_CHECK_TIMEOUT
            )
            logger.info(f"oscal-cli available: {result.stdout.strip()}")
            self.validator = OSCALValidator(oscal_cli_path)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            raise RuntimeError(f"oscal-cli not available at: {oscal_cli_path}")
    
    def _discover_oscal_files(self) -> List[Path]:
        """Discover OSCAL files to validate"""
        logger.info(f"Discovering OSCAL files in {self.oscal_dir}")
        
        oscal_files = []
        patterns = ["*.json", "*.xml", "*.yaml", "*.yml"]
        
        for pattern in patterns:
            files = list(self.oscal_dir.glob(pattern))
            # Filter to likely OSCAL files
            for file_path in files:
                if self._is_likely_oscal_file(file_path):
                    oscal_files.append(file_path)
        
        logger.info(f"Found {len(oscal_files)} OSCAL files: {[f.name for f in oscal_files]}")
        return oscal_files
    
    def _is_likely_oscal_file(self, file_path: Path) -> bool:
        """Check if file is likely an OSCAL document"""
        # Skip known non-OSCAL files
        skip_patterns = ["manifest", "summary", "report", "log"]
        if any(pattern in file_path.stem.lower() for pattern in skip_patterns):
            return False
        
        try:
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r') as f:
                    content = json.load(f)
                
                # Check for OSCAL root elements
                oscal_roots = [
                    "catalog", "profile", "component-definition",
                    "system-security-plan", "assessment-plan", "assessment-results", 
                    "plan-of-action-and-milestones"
                ]
                
                return any(root in content for root in oscal_roots)
            
            # For non-JSON, assume might be OSCAL
            return file_path.suffix.lower() in ['.xml', '.yaml', '.yml']
            
        except (json.JSONDecodeError, IOError):
            return False
    
    def _run_validation_batch(self, 
                            oscal_files: List[Path], 
                            use_docker: bool,
                            oscal_cli_path: str,
                            show_progress: bool = True) -> Dict[str, Dict[str, Any]]:
        """Run validation for batch of OSCAL files with enhanced error reporting"""
        results = {}
        
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                
                validation_task = progress.add_task(
                    f"Validating {len(oscal_files)} OSCAL files...", 
                    total=len(oscal_files)
                )
                
                for file_path in oscal_files:
                    progress.update(
                        validation_task, 
                        description=f"Validating {file_path.name}..."
                    )
                    
                    try:
                        if use_docker:
                            result = self._validate_with_docker(file_path)
                        else:
                            result = self._validate_with_oscal_cli(file_path, oscal_cli_path)
                        
                        results[str(file_path)] = result
                        
                        # Log result
                        if result["valid"]:
                            logger.info(f"✓ {file_path.name} validation passed")
                        else:
                            logger.error(f"✗ {file_path.name} validation failed: {len(result['errors'])} errors")
                            for error in result["errors"]:
                                logger.error(f"  Error: {error}")
                        
                    except Exception as e:
                        logger.exception(f"Failed to validate {file_path}: {e}")
                        results[str(file_path)] = self._create_validation_error_result(file_path, str(e))
                    
                    progress.advance(validation_task)
        else:
            # Run without progress display
            for file_path in oscal_files:
                logger.info(f"Validating {file_path.name}...")
                
                try:
                    if use_docker:
                        result = self._validate_with_docker(file_path)
                    else:
                        result = self._validate_with_oscal_cli(file_path, oscal_cli_path)
                    
                    results[str(file_path)] = result
                    
                    # Log result
                    if result["valid"]:
                        logger.info(f"✓ {file_path.name} validation passed")
                    else:
                        logger.error(f"✗ {file_path.name} validation failed: {len(result['errors'])} errors")
                        for error in result["errors"]:
                            logger.error(f"  Error: {error}")
                    
                except Exception as e:
                    logger.exception(f"Failed to validate {file_path}: {e}")
                    results[str(file_path)] = self._create_validation_error_result(file_path, str(e))
        
        return results
    
    def _validate_with_docker(self, file_path: Path) -> Dict[str, Any]:
        """Validate OSCAL file using Docker container"""
        logger.debug(f"Validating {file_path} with Docker")
        
        try:
            # Determine OSCAL document type for validation
            doc_type = self._detect_oscal_type(file_path)
            
            if not doc_type:
                return {
                    "file": str(file_path),
                    "valid": False,
                    "errors": ["Could not determine OSCAL document type"],
                    "warnings": [],
                    "validation_method": "docker"
                }
            
            # Run Docker validation
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{self.oscal_dir.absolute()}:/work",
                "-w", "/work",
                "oscalize:dev",
                f"/opt/oscal-cli/bin/oscal-cli {doc_type} validate {file_path.name}"
            ]
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=DOCKER_VALIDATION_TIMEOUT
            )
            
            return self._parse_oscal_cli_output(file_path, result, "docker")
            
        except subprocess.TimeoutExpired:
            return {
                "file": str(file_path),
                "valid": False,
                "errors": ["Validation timeout (Docker)"],
                "warnings": [],
                "validation_method": "docker"
            }
        except Exception as e:
            return {
                "file": str(file_path),
                "valid": False,
                "errors": [f"Docker validation error: {str(e)}"],
                "warnings": [],
                "validation_method": "docker"
            }
    
    def _validate_with_oscal_cli(self, file_path: Path, oscal_cli_path: str) -> Dict[str, Any]:
        """Validate OSCAL file using local oscal-cli"""
        logger.debug(f"Validating {file_path} with local oscal-cli")
        
        if not self.validator:
            self.validator = OSCALValidator(oscal_cli_path)
        
        result = self.validator.validate_file(file_path)
        result["validation_method"] = "local"
        return result
    
    def _detect_oscal_type(self, file_path: Path) -> Optional[str]:
        """Detect OSCAL document type for validation"""
        try:
            with open(file_path, 'r') as f:
                content = json.load(f)
            
            type_mapping = {
                "system-security-plan": "ssp",
                "plan-of-action-and-milestones": "poam",
                "assessment-plan": "ap",
                "assessment-results": "ar",
                "catalog": "catalog",
                "profile": "profile",
                "component-definition": "component-definition"
            }
            
            for oscal_key, cli_type in type_mapping.items():
                if oscal_key in content:
                    return cli_type
            
            return None
            
        except (json.JSONDecodeError, IOError):
            return None
    
    def _parse_oscal_cli_output(self, 
                               file_path: Path, 
                               result: subprocess.CompletedProcess,
                               method: str) -> Dict[str, Any]:
        """Parse oscal-cli output with enhanced error extraction"""
        validation_result = {
            "file": str(file_path),
            "valid": result.returncode == 0,
            "exit_code": result.returncode,
            "errors": [],
            "warnings": [],
            "validation_method": method,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
        # Enhanced error parsing
        all_output = f"{result.stdout}\n{result.stderr}"
        lines = all_output.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            
            # Enhanced error detection
            error_indicators = [
                "error", "invalid", "failed", "violation", 
                "constraint", "schema", "not valid", "missing"
            ]
            warning_indicators = ["warning", "warn"]
            
            if any(indicator in line_lower for indicator in error_indicators):
                validation_result["errors"].append(line)
            elif any(indicator in line_lower for indicator in warning_indicators):
                validation_result["warnings"].append(line)
        
        return validation_result
    
    def _generate_enhanced_summary(self, validation_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate enhanced validation summary with detailed analysis"""
        logger.info("Generating enhanced validation summary")
        
        # Save individual validation logs
        for file_path, result in validation_results.items():
            log_file = self.validation_dir / f"{Path(file_path).stem}.log"
            with open(log_file, 'w') as f:
                f.write(f"OSCAL Validation Report\n")
                f.write(f"File: {file_path}\n")
                f.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n")
                f.write(f"Method: {result.get('validation_method', 'unknown')}\n")
                f.write(f"Valid: {result['valid']}\n")
                f.write(f"Exit Code: {result.get('exit_code', 'N/A')}\n")
                f.write("\n--- STDOUT ---\n")
                f.write(result.get('stdout', ''))
                f.write("\n--- STDERR ---\n")
                f.write(result.get('stderr', ''))
                f.write("\n--- ERRORS ---\n")
                for error in result.get('errors', []):
                    f.write(f"ERROR: {error}\n")
                f.write("\n--- WARNINGS ---\n")
                for warning in result.get('warnings', []):
                    f.write(f"WARNING: {warning}\n")
        
        # Generate comprehensive summary using reporter
        summary = self.reporter.generate_summary()
        
        # Enhance with pipeline-specific information
        summary["pipeline_metadata"] = {
            "start_time": datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
            "duration": time.time() - self.start_time if self.start_time else None,
            "oscal_directory": str(self.oscal_dir),
            "validation_directory": str(self.validation_dir),
            "pipeline_version": "1.0"
        }
        
        return summary
    
    def _create_actionable_outputs(self, summary: Dict[str, Any]) -> None:
        """Create actionable outputs for validation results"""
        logger.info("Creating actionable outputs")
        
        # Create must-fix checklist
        must_fix_checklist = self.reporter.export_must_fix_checklist()
        if must_fix_checklist:
            checklist_file = self.validation_dir / "must_fix_checklist.json"
            with open(checklist_file, 'w') as f:
                json.dump(must_fix_checklist, f, indent=2)
            logger.info(f"Must-fix checklist saved: {checklist_file}")
        
        # Create detailed report
        detailed_report = self.reporter.generate_detailed_report()
        report_file = self.validation_dir / "detailed_validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(detailed_report, f, indent=2)
        logger.info(f"Detailed report saved: {report_file}")
        
        # Create summary report
        summary_file = self.validation_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Summary report saved: {summary_file}")
    
    def _display_results(self, summary: Dict[str, Any]) -> None:
        """Display validation results with enhanced formatting"""
        self.console.print()
        self.console.print(Panel.fit(
            "[bold blue]OSCAL Validation Pipeline Results[/bold blue]",
            style="blue"
        ))
        
        # Summary table
        table = Table(title="Validation Summary", style="cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Value", style="green")
        
        summary_data = summary["summary"]
        table.add_row("Total Files", str(summary_data["total_files"]))
        table.add_row("Valid Files", str(summary_data["valid_files"]))
        table.add_row("Invalid Files", str(summary_data["invalid_files"]))
        table.add_row("Files with Warnings", str(summary_data["files_with_warnings"]))
        table.add_row("Must-Fix Issues", str(len(summary["must_fix"])))
        table.add_row("Nice-to-Have Issues", str(len(summary["nice_to_have"])))
        
        compliance = summary.get("compliance_analysis", {})
        table.add_row("Compliance Score", f"{compliance.get('overall_compliance', 0):.1f}%")
        table.add_row("Status", compliance.get('status', 'UNKNOWN'))
        
        self.console.print(table)
        
        # Show critical issues if any
        if summary["must_fix"]:
            self.console.print("\n[bold red]Critical Issues Requiring Attention:[/bold red]")
            for issue in summary["must_fix"][:5]:  # Show first 5
                self.console.print(f"  • [red]{issue['title']}[/red] - {issue['file']}")
            if len(summary["must_fix"]) > 5:
                self.console.print(f"  ... and {len(summary['must_fix']) - 5} more issues")
        
        # Next steps
        if compliance.get("next_steps"):
            self.console.print("\n[bold yellow]Recommended Next Steps:[/bold yellow]")
            for step in compliance["next_steps"]:
                self.console.print(f"  • {step}")
        
        self.console.print(f"\n[dim]Detailed reports available in: {self.validation_dir}[/dim]")
    
    def _create_validation_error_result(self, file_path: Path, error_message: str) -> Dict[str, Any]:
        """Create error result for validation failures"""
        return {
            "file": str(file_path),
            "valid": False,
            "errors": [f"Validation system error: {error_message}"],
            "warnings": [],
            "validation_method": "error"
        }
    
    def _create_no_files_result(self) -> Dict[str, Any]:
        """Create result when no OSCAL files are found"""
        return {
            "summary": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "total_files": 0,
                "valid_files": 0,
                "invalid_files": 0,
                "files_with_warnings": 0
            },
            "results": [],
            "must_fix": [{
                "title": "No OSCAL Files Found",
                "description": f"No OSCAL files found in {self.oscal_dir}",
                "severity": "ERROR",
                "action": "Generate OSCAL files using conversion pipeline"
            }],
            "nice_to_have": [],
            "compliance_analysis": {
                "overall_compliance": 0,
                "status": "NO_FILES",
                "readiness_assessment": "No OSCAL files available for validation"
            }
        }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result for pipeline failures"""
        return {
            "summary": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "total_files": 0,
                "valid_files": 0,
                "invalid_files": 0,
                "files_with_warnings": 0
            },
            "results": [],
            "must_fix": [{
                "title": "Validation Pipeline Error",
                "description": error_message,
                "severity": "CRITICAL",
                "action": "Fix pipeline configuration and retry"
            }],
            "nice_to_have": [],
            "compliance_analysis": {
                "overall_compliance": 0,
                "status": "PIPELINE_ERROR",
                "readiness_assessment": f"Pipeline error: {error_message}"
            }
        }