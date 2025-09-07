"""
CIR validator using JSON schemas

Validates Canonical Intermediate Representation data against schemas.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema
from jsonschema import Draft7Validator

logger = logging.getLogger(__name__)


class CIRValidator:
    """Validator for CIR data structures using JSON schemas"""
    
    def __init__(self, schema_dir: Path):
        self.schema_dir = Path(schema_dir)
        self.schemas = {}
        self._load_schemas()
    
    def _load_schemas(self) -> None:
        """Load all CIR schemas from schema directory"""
        if not self.schema_dir.exists():
            logger.warning(f"Schema directory not found: {self.schema_dir}")
            return
        
        for schema_file in self.schema_dir.glob("cir_*.json"):
            schema_name = schema_file.name
            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                
                # Validate the schema itself
                Draft7Validator.check_schema(schema)
                
                self.schemas[schema_name] = schema
                logger.debug(f"Loaded schema: {schema_name}")
                
            except (json.JSONDecodeError, jsonschema.SchemaError) as e:
                logger.error(f"Invalid schema {schema_file}: {e}")
    
    def validate(self, data: Dict[str, Any], schema_name: str) -> bool:
        """Validate data against specified schema"""
        if schema_name not in self.schemas:
            logger.error(f"Schema not found: {schema_name}")
            return False
        
        schema = self.schemas[schema_name]
        validator = Draft7Validator(schema)
        
        try:
            # Validate and collect all errors
            errors = list(validator.iter_errors(data))
            
            if errors:
                logger.error(f"CIR validation failed for {schema_name}:")
                for error in errors:
                    logger.error(f"  {error.message} at {' -> '.join(str(p) for p in error.absolute_path)}")
                return False
            
            logger.info(f"CIR validation successful for {schema_name}")
            return True
            
        except Exception as e:
            logger.error(f"Validation error for {schema_name}: {e}")
            return False
    
    def get_validation_report(self, data: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
        """Get detailed validation report"""
        if schema_name not in self.schemas:
            return {
                "valid": False,
                "errors": [f"Schema not found: {schema_name}"],
                "warnings": [],
                "schema": schema_name
            }
        
        schema = self.schemas[schema_name]
        validator = Draft7Validator(schema)
        
        errors = []
        warnings = []
        
        try:
            # Collect validation errors
            for error in validator.iter_errors(data):
                error_info = {
                    "message": error.message,
                    "path": list(error.absolute_path),
                    "invalid_value": error.instance,
                    "schema_path": list(error.schema_path)
                }
                
                # Classify as error or warning based on severity
                if error.validator in ['required', 'type']:
                    errors.append(error_info)
                else:
                    warnings.append(error_info)
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "schema": schema_name,
                "data_summary": self._summarize_data(data)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation exception: {str(e)}"],
                "warnings": [],
                "schema": schema_name
            }
    
    def validate_all_schemas(self, cir_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Validate all CIR data types against their schemas"""
        results = {}
        
        schema_mappings = {
            "document": "cir_document.json",
            "poam": "cir_poam.json", 
            "inventory": "cir_inventory.json",
            "controls": "cir_controls.json",
            "system_metadata": "cir_system_metadata.json"
        }
        
        for data_type, data in cir_data.items():
            if data_type in schema_mappings:
                schema_name = schema_mappings[data_type]
                results[data_type] = self.get_validation_report(data, schema_name)
            else:
                logger.warning(f"No schema mapping for data type: {data_type}")
        
        return results
    
    def _summarize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of data structure"""
        summary = {
            "type": type(data).__name__,
            "keys": list(data.keys()) if isinstance(data, dict) else None,
            "size": len(data) if hasattr(data, '__len__') else None
        }
        
        # Add specific summaries for known structures
        if isinstance(data, dict):
            if "sections" in data:
                summary["section_count"] = len(data.get("sections", []))
            
            if "rows" in data:
                summary["row_count"] = len(data.get("rows", []))
            
            if "assets" in data:
                summary["asset_count"] = len(data.get("assets", []))
            
            if "controls" in data:
                summary["control_count"] = len(data.get("controls", []))
        
        return summary