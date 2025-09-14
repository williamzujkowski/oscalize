"""
Corpus generator for creating golden test cases

Generates corpus test cases from sample inputs by running conversion and capturing outputs.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .enhanced_corpus_tester import EnhancedCorpusTester

logger = logging.getLogger(__name__)


class CorpusGenerator:
    """Generator for creating golden corpus test cases"""
    
    def __init__(self, 
                 corpus_dir: Path,
                 console: Optional[Console] = None):
        self.corpus_dir = Path(corpus_dir)
        self.console = console or Console()
        
        # Ensure corpus directory exists
        self.corpus_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize tester for generating golden outputs
        self.tester = EnhancedCorpusTester(
            corpus_dir=self.corpus_dir,
            console=self.console
        )
        
        logger.info(f"Corpus generator initialized: {self.corpus_dir}")
    
    def generate_from_samples(self, 
                            samples_dir: Path,
                            test_descriptions: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Generate corpus from sample input files"""
        
        logger.info(f"Generating corpus from samples: {samples_dir}")
        
        if not samples_dir.exists():
            raise ValueError(f"Samples directory not found: {samples_dir}")
        
        generation_result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "samples_directory": str(samples_dir),
            "corpus_directory": str(self.corpus_dir),
            "generated_tests": [],
            "errors": [],
            "summary": {}
        }
        
        # Discover sample groups
        sample_groups = self._discover_sample_groups(samples_dir)
        
        if not sample_groups:
            generation_result["errors"].append("No sample groups found")
            return generation_result
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            task = progress.add_task(
                f"Generating {len(sample_groups)} corpus test cases...",
                total=len(sample_groups)
            )
            
            for group_name, input_files in sample_groups.items():
                progress.update(task, description=f"Creating test case: {group_name}")
                
                try:
                    description = test_descriptions.get(group_name, f"Generated from samples: {group_name}") if test_descriptions else f"Generated test case: {group_name}"
                    
                    test_dir = self.tester.create_golden_corpus_entry(
                        input_files=input_files,
                        test_name=group_name,
                        description=description
                    )
                    
                    generation_result["generated_tests"].append({
                        "name": group_name,
                        "directory": str(test_dir),
                        "input_files": [str(f) for f in input_files],
                        "status": "SUCCESS"
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to generate test case {group_name}: {e}")
                    generation_result["errors"].append(f"Failed to generate {group_name}: {str(e)}")
                    generation_result["generated_tests"].append({
                        "name": group_name,
                        "status": "ERROR",
                        "error": str(e)
                    })
                
                progress.advance(task)
        
        # Generate summary
        successful = len([t for t in generation_result["generated_tests"] if t.get("status") == "SUCCESS"])
        failed = len(generation_result["generated_tests"]) - successful
        
        generation_result["summary"] = {
            "total_attempted": len(sample_groups),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(sample_groups) * 100) if sample_groups else 0
        }
        
        self.console.print(f"\n✅ Generated {successful} corpus test cases")
        if failed > 0:
            self.console.print(f"❌ {failed} test cases failed to generate")
        
        return generation_result
    
    def create_test_case_from_current_inputs(self, 
                                           inputs_dir: Path = Path("inputs"),
                                           test_name: str = None,
                                           description: str = "") -> Path:
        """Create a corpus test case from current input directory"""
        
        if not inputs_dir.exists():
            raise ValueError(f"Inputs directory not found: {inputs_dir}")
        
        input_files = list(inputs_dir.glob("*"))
        input_files = [f for f in input_files if f.is_file() and not f.name.startswith(".")]
        
        if not input_files:
            raise ValueError(f"No input files found in {inputs_dir}")
        
        if not test_name:
            test_name = f"current_inputs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if not description:
            description = f"Test case generated from {inputs_dir} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        logger.info(f"Creating test case from current inputs: {test_name}")
        
        return self.tester.create_golden_corpus_entry(
            input_files=input_files,
            test_name=test_name,
            description=description
        )
    
    def generate_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Generate comprehensive test suite covering various scenarios"""
        
        logger.info("Generating comprehensive test suite")
        
        # Define test scenarios
        test_scenarios = [
            {
                "name": "minimal_ssp",
                "description": "Minimal SSP document with basic required elements",
                "inputs": ["minimal_ssp.md"],
                "validation_status": "COMPLIANT"
            },
            {
                "name": "basic_poam",
                "description": "Basic POA&M with standard remediation items",
                "inputs": ["poam_basic.xlsx"],
                "validation_status": "COMPLIANT"
            },
            {
                "name": "complete_package",
                "description": "Complete FedRAMP package with SSP, POA&M, and inventory",
                "inputs": ["complete_ssp.md", "poam_complete.xlsx", "inventory_complete.xlsx"],
                "validation_status": "COMPLIANT"
            },
            {
                "name": "edge_cases",
                "description": "Edge cases with unusual formatting and content",
                "inputs": ["edge_case_ssp.docx", "edge_case_poam.xlsx"],
                "validation_status": "COMPLIANT"
            },
            {
                "name": "validation_errors",
                "description": "Inputs that should generate validation errors",
                "inputs": ["invalid_ssp.md", "invalid_poam.xlsx"],
                "validation_status": "NON_COMPLIANT"
            }
        ]
        
        suite_result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "test_scenarios": [],
            "created_scenarios": [],
            "skipped_scenarios": [],
            "summary": {}
        }
        
        for scenario in test_scenarios:
            try:
                # Check if inputs exist (for now, we'll skip if they don't)
                # In practice, you would create these sample files
                scenario_inputs = []
                for input_name in scenario["inputs"]:
                    input_path = Path("test_samples") / input_name
                    if input_path.exists():
                        scenario_inputs.append(input_path)
                
                if scenario_inputs:
                    test_dir = self.tester.create_golden_corpus_entry(
                        input_files=scenario_inputs,
                        test_name=scenario["name"],
                        description=scenario["description"],
                        expected_validation_status=scenario["validation_status"]
                    )
                    
                    suite_result["created_scenarios"].append({
                        "name": scenario["name"],
                        "directory": str(test_dir),
                        "description": scenario["description"]
                    })
                else:
                    suite_result["skipped_scenarios"].append({
                        "name": scenario["name"],
                        "reason": "Input files not found",
                        "expected_inputs": scenario["inputs"]
                    })
                    
            except Exception as e:
                logger.error(f"Failed to create scenario {scenario['name']}: {e}")
                suite_result["skipped_scenarios"].append({
                    "name": scenario["name"],
                    "reason": f"Error: {str(e)}"
                })
        
        suite_result["summary"] = {
            "total_scenarios": len(test_scenarios),
            "created": len(suite_result["created_scenarios"]),
            "skipped": len(suite_result["skipped_scenarios"])
        }
        
        return suite_result
    
    def create_template_test_case(self, test_name: str) -> Path:
        """Create a template test case directory structure"""
        
        test_dir = self.corpus_dir / test_name
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create directories
        inputs_dir = test_dir / "inputs"
        outputs_dir = test_dir / "expected_outputs"
        inputs_dir.mkdir(exist_ok=True)
        outputs_dir.mkdir(exist_ok=True)
        
        # Create template configuration
        template_config = {
            "name": test_name,
            "description": "Template test case - update this description",
            "created": datetime.utcnow().isoformat() + "Z",
            "input_files": [
                "inputs/sample_ssp.md",
                "inputs/sample_poam.xlsx"
            ],
            "expected_outputs": [
                "expected_outputs/ssp.json",
                "expected_outputs/poam.json"
            ],
            "expected_validation_status": "COMPLIANT",
            "test_type": "golden_corpus",
            "metadata": {
                "oscal_version": "1.1.3",
                "oscalize_version": "1.0",
                "template": True
            }
        }
        
        config_file = test_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(template_config, f, indent=2)
        
        # Create README
        readme_content = f"""# Test Case: {test_name}

## Description
{template_config['description']}

## Structure
- `inputs/` - Input files for conversion testing
- `expected_outputs/` - Expected OSCAL outputs after conversion
- `test_config.json` - Test configuration and metadata

## Instructions
1. Add your input files to the `inputs/` directory
2. Run the conversion to generate expected outputs
3. Place the generated outputs in `expected_outputs/` directory
4. Update `test_config.json` with correct file paths and metadata
5. Run corpus tests to validate the test case

## Generated
Created: {template_config['created']}
Generator: oscalize corpus generator
"""
        
        readme_file = test_dir / "README.md"
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        
        logger.info(f"Template test case created: {test_dir}")
        return test_dir
    
    def _discover_sample_groups(self, samples_dir: Path) -> Dict[str, List[Path]]:
        """Discover groups of related sample files"""
        
        groups = {}
        
        # Group by base name patterns
        for file_path in samples_dir.glob("*"):
            if not file_path.is_file():
                continue
            
            # Skip hidden files and temp files
            if file_path.name.startswith('.') or file_path.name.endswith('.tmp'):
                continue
            
            # Group by base name (remove extensions and common suffixes)
            base_name = self._extract_group_name(file_path)
            
            if base_name not in groups:
                groups[base_name] = []
            
            groups[base_name].append(file_path)
        
        # Filter out single-file groups unless they're complete documents
        filtered_groups = {}
        for group_name, files in groups.items():
            if len(files) > 1 or self._is_complete_document(files[0]):
                filtered_groups[group_name] = files
        
        logger.info(f"Discovered {len(filtered_groups)} sample groups")
        return filtered_groups
    
    def _extract_group_name(self, file_path: Path) -> str:
        """Extract group name from file path"""
        name = file_path.stem.lower()
        
        # Remove common suffixes
        suffixes_to_remove = [
            "_sample", "_example", "_test", "_demo",
            "_v1", "_v2", "_draft", "_final"
        ]
        
        for suffix in suffixes_to_remove:
            name = name.replace(suffix, "")
        
        # Remove numbers at the end
        while name and name[-1].isdigit():
            name = name[:-1]
        
        if name.endswith('_'):
            name = name[:-1]
        
        return name or file_path.stem.lower()
    
    def _is_complete_document(self, file_path: Path) -> bool:
        """Check if file is a complete document that can be tested alone"""
        
        # SSP documents
        if file_path.suffix.lower() in ['.md', '.docx'] and 'ssp' in file_path.name.lower():
            return True
        
        # POA&M files
        if file_path.suffix.lower() == '.xlsx' and 'poam' in file_path.name.lower():
            return True
        
        # Inventory files
        if file_path.suffix.lower() == '.xlsx' and 'inventory' in file_path.name.lower():
            return True
        
        return False
    
    def export_corpus_manifest(self) -> Dict[str, Any]:
        """Export manifest of all corpus test cases"""
        
        logger.info("Exporting corpus manifest")
        
        manifest = {
            "manifest_metadata": {
                "title": "Oscalize Corpus Manifest",
                "generated": datetime.utcnow().isoformat() + "Z",
                "generator": "corpus_generator",
                "version": "1.0"
            },
            "corpus_directory": str(self.corpus_dir),
            "test_cases": [],
            "statistics": {}
        }
        
        if not self.corpus_dir.exists():
            manifest["test_cases"] = []
            manifest["statistics"] = {"total": 0, "configured": 0, "auto_detected": 0}
            return manifest
        
        # Discover all test cases
        test_cases = self.tester._discover_enhanced_test_cases()
        
        for test_case in test_cases:
            case_info = {
                "name": test_case["name"],
                "type": test_case["type"],
                "directory": str(test_case["directory"]),
                "input_files": [str(f) for f in test_case.get("input_files", [])],
                "expected_outputs": [str(f) for f in test_case.get("expected_outputs", [])]
            }
            
            # Add configuration details if available
            if "config" in test_case:
                config = test_case["config"]
                case_info["description"] = config.get("description", "")
                case_info["created"] = config.get("created", "")
                case_info["expected_validation_status"] = config.get("expected_validation_status", "COMPLIANT")
            
            manifest["test_cases"].append(case_info)
        
        # Generate statistics
        total = len(test_cases)
        configured = len([tc for tc in test_cases if tc["type"] == "configured_enhanced"])
        auto_detected = total - configured
        
        manifest["statistics"] = {
            "total": total,
            "configured": configured,
            "auto_detected": auto_detected
        }
        
        # Save manifest
        manifest_file = self.corpus_dir / "corpus_manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Corpus manifest exported: {manifest_file}")
        return manifest