"""
OSCAL validator using NIST oscal-cli

Validates OSCAL artifacts using the official NIST oscal-cli tool.
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OSCALValidator:
    """Validator for OSCAL artifacts using NIST oscal-cli"""
    
    def __init__(self, oscal_cli_path: str = "oscal-cli"):
        self.oscal_cli_path = oscal_cli_path
        self._check_oscal_cli()
    
    def _check_oscal_cli(self) -> None:
        """Check if oscal-cli is available"""
        try:
            result = subprocess.run(
                [self.oscal_cli_path, "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Using {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                f"oscal-cli not found at {self.oscal_cli_path}. "
                "Install with: task install-oscal-cli"
            )
    
    def validate_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate OSCAL file using oscal-cli"""
        logger.info(f"Validating OSCAL file: {file_path}")
        
        if not file_path.exists():
            return self._create_error_result(f"File not found: {file_path}")
        
        try:
            # Run oscal-cli validate command
            result = subprocess.run(
                [self.oscal_cli_path, "validate", str(file_path)],
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            return self._parse_validation_result(file_path, result)
            
        except subprocess.TimeoutExpired:
            return self._create_error_result(f"Validation timeout for {file_path}")
        except Exception as e:
            return self._create_error_result(f"Validation error: {str(e)}")
    
    def validate_content(self, content: Dict[str, Any], file_type: str = "json") -> Dict[str, Any]:
        """Validate OSCAL content using temporary file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{file_type}', delete=False) as temp_file:
            try:
                if file_type == "json":
                    json.dump(content, temp_file, indent=2)
                else:
                    temp_file.write(str(content))
                
                temp_path = Path(temp_file.name)
                result = self.validate_file(temp_path)
                
                # Update file reference in result
                result["file"] = "<content>"
                return result
                
            finally:
                Path(temp_file.name).unlink(missing_ok=True)
    
    def validate_directory(self, directory: Path) -> Dict[str, Dict[str, Any]]:
        """Validate all OSCAL files in directory"""
        results = {}
        
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return results
        
        # Find OSCAL files
        oscal_files = []
        for pattern in ["*.json", "*.xml", "*.yaml", "*.yml"]:
            oscal_files.extend(directory.glob(pattern))
        
        logger.info(f"Validating {len(oscal_files)} files in {directory}")
        
        for file_path in oscal_files:
            # Skip non-OSCAL files
            if not self._is_oscal_file(file_path):
                continue
            
            result = self.validate_file(file_path)
            results[str(file_path)] = result
        
        return results
    
    def convert_format(self, input_file: Path, output_file: Path, 
                      target_format: str = "json") -> bool:
        """Convert OSCAL between formats using oscal-cli"""
        logger.info(f"Converting {input_file} to {target_format}")
        
        try:
            result = subprocess.run(
                [
                    self.oscal_cli_path, "convert",
                    str(input_file),
                    "--to", target_format,
                    "--output", str(output_file)
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )
            
            logger.info(f"Conversion successful: {output_file}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Conversion failed: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Conversion timeout")
            return False
    
    def resolve_profile(self, profile_file: Path, output_file: Path) -> bool:
        """Resolve OSCAL profile using oscal-cli"""
        logger.info(f"Resolving profile: {profile_file}")
        
        try:
            result = subprocess.run(
                [
                    self.oscal_cli_path, "profile", "resolve",
                    str(profile_file),
                    "--output", str(output_file)
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=120  # Profiles can take longer
            )
            
            logger.info(f"Profile resolution successful: {output_file}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Profile resolution failed: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Profile resolution timeout")
            return False
    
    def _parse_validation_result(self, file_path: Path, 
                               result: subprocess.CompletedProcess) -> Dict[str, Any]:
        """Parse oscal-cli validation output"""
        validation_result = {
            "file": str(file_path),
            "valid": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "errors": [],
            "warnings": []
        }
        
        # Parse errors and warnings from output
        if result.stderr:
            lines = result.stderr.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if "error" in line.lower():
                    validation_result["errors"].append(line)
                elif "warning" in line.lower():
                    validation_result["warnings"].append(line)
                elif "invalid" in line.lower() or "failed" in line.lower():
                    validation_result["errors"].append(line)
        
        # Parse stdout for additional information
        if result.stdout:
            lines = result.stdout.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if "valid" in line.lower() and "invalid" not in line.lower():
                    # This is a success message
                    continue
                elif any(keyword in line.lower() for keyword in ["error", "invalid", "failed"]):
                    validation_result["errors"].append(line)
                elif "warning" in line.lower():
                    validation_result["warnings"].append(line)
        
        return validation_result
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result structure"""
        return {
            "file": "<unknown>",
            "valid": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": error_message,
            "errors": [error_message],
            "warnings": []
        }
    
    def _is_oscal_file(self, file_path: Path) -> bool:
        """Check if file appears to be an OSCAL document"""
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
            
            elif file_path.suffix.lower() in ['.xml', '.yaml', '.yml']:
                # For non-JSON files, assume they might be OSCAL
                # Could be enhanced with more sophisticated detection
                return True
        
        except (json.JSONDecodeError, IOError):
            pass
        
        return False
    
    def get_supported_formats(self) -> List[str]:
        """Get list of formats supported by oscal-cli"""
        try:
            result = subprocess.run(
                [self.oscal_cli_path, "convert", "--help"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse supported formats from help output
            # This is a simplified implementation
            formats = ["json", "xml", "yaml"]
            
            return formats
            
        except subprocess.CalledProcessError:
            return ["json", "xml", "yaml"]  # Default supported formats