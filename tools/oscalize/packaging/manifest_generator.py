"""
Manifest generator for OSCAL artifacts

Generates manifests with file hashes, timestamps, and metadata for reproducible builds.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ManifestGenerator:
    """Generator for OSCAL artifact manifests"""
    
    def __init__(self):
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.generator_version = "1.0.0"
    
    def generate(self, artifact_dir: Path, include_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate manifest for OSCAL artifacts directory"""
        logger.info(f"Generating manifest for {artifact_dir}")
        
        if not artifact_dir.exists():
            raise ValueError(f"Artifact directory not found: {artifact_dir}")
        
        # Default patterns for OSCAL files
        if include_patterns is None:
            include_patterns = ["*.json", "*.xml", "*.yaml", "*.yml", "*.log", "*.md"]
        
        manifest = {
            "manifest": {
                "version": "1.0",
                "generated": self.timestamp,
                "generator": f"oscalize-manifest-generator-{self.generator_version}",
                "directory": str(artifact_dir),
                "files": self._collect_files(artifact_dir, include_patterns),
                "summary": {},
                "integrity": {},
                "metadata": self._collect_metadata(artifact_dir)
            }
        }
        
        # Add summary statistics
        manifest["manifest"]["summary"] = self._generate_summary(manifest["manifest"]["files"])
        
        # Add integrity information
        manifest["manifest"]["integrity"] = self._generate_integrity_info(manifest["manifest"]["files"])
        
        return manifest
    
    def _collect_files(self, directory: Path, patterns: List[str]) -> List[Dict[str, Any]]:
        """Collect file information matching patterns"""
        files = []
        
        for pattern in patterns:
            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    file_info = self._analyze_file(file_path, directory)
                    files.append(file_info)
        
        # Sort by relative path for consistency
        files.sort(key=lambda x: x["path"])
        
        logger.info(f"Collected {len(files)} files for manifest")
        return files
    
    def _analyze_file(self, file_path: Path, base_dir: Path) -> Dict[str, Any]:
        """Analyze individual file for manifest"""
        try:
            stat_info = file_path.stat()
            relative_path = file_path.relative_to(base_dir)
            
            file_info = {
                "path": str(relative_path),
                "absolute_path": str(file_path),
                "size": stat_info.st_size,
                "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat() + "Z",
                "permissions": oct(stat_info.st_mode)[-3:],
                "hash": {
                    "algorithm": "SHA-256",
                    "value": self._calculate_file_hash(file_path)
                },
                "type": self._determine_file_type(file_path),
                "metadata": self._extract_file_metadata(file_path)
            }
            
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")
            return {
                "path": str(file_path.relative_to(base_dir)),
                "error": f"Analysis failed: {str(e)}"
            }
    
    def _calculate_file_hash(self, file_path: Path, algorithm: str = "sha256") -> str:
        """Calculate file hash"""
        hasher = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Failed to hash file {file_path}: {e}")
            return ""
    
    def _determine_file_type(self, file_path: Path) -> str:
        """Determine OSCAL file type"""
        suffix = file_path.suffix.lower()
        name = file_path.name.lower()
        
        # Identify OSCAL artifact types
        if "ssp" in name or "system-security-plan" in name:
            return "system-security-plan"
        elif "poam" in name or "plan-of-action" in name:
            return "plan-of-action-and-milestones"
        elif "assessment-plan" in name:
            return "assessment-plan"
        elif "assessment-results" in name:
            return "assessment-results"
        elif "component-definition" in name:
            return "component-definition"
        elif "profile" in name:
            return "profile"
        elif "catalog" in name:
            return "catalog"
        elif suffix == ".log":
            return "validation-log"
        elif "manifest" in name:
            return "manifest"
        elif suffix in [".json", ".xml", ".yaml", ".yml"]:
            return "oscal-document"
        else:
            return "supporting-document"
    
    def _extract_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from file"""
        metadata = {}
        
        try:
            if file_path.suffix.lower() == ".json":
                with open(file_path, 'r') as f:
                    content = json.load(f)
                
                # Extract OSCAL metadata if present
                oscal_metadata = self._find_oscal_metadata(content)
                if oscal_metadata:
                    metadata["oscal"] = {
                        "title": oscal_metadata.get("title", ""),
                        "version": oscal_metadata.get("version", ""),
                        "oscal_version": oscal_metadata.get("oscal-version", ""),
                        "last_modified": oscal_metadata.get("last-modified", "")
                    }
        
        except Exception as e:
            logger.debug(f"Could not extract metadata from {file_path}: {e}")
        
        return metadata
    
    def _find_oscal_metadata(self, content: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find OSCAL metadata section in document"""
        # Check common OSCAL root elements
        for root_key in content.keys():
            if isinstance(content[root_key], dict) and "metadata" in content[root_key]:
                return content[root_key]["metadata"]
        
        return None
    
    def _generate_summary(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics"""
        summary = {
            "total_files": len(files),
            "total_size": sum(f.get("size", 0) for f in files if "size" in f),
            "file_types": {},
            "oscal_artifacts": 0,
            "validation_logs": 0,
            "supporting_files": 0
        }
        
        # Count by file type
        for file_info in files:
            file_type = file_info.get("type", "unknown")
            summary["file_types"][file_type] = summary["file_types"].get(file_type, 0) + 1
            
            # Categorize
            if file_type in ["system-security-plan", "plan-of-action-and-milestones", 
                           "assessment-plan", "assessment-results", "component-definition",
                           "profile", "catalog"]:
                summary["oscal_artifacts"] += 1
            elif file_type == "validation-log":
                summary["validation_logs"] += 1
            else:
                summary["supporting_files"] += 1
        
        return summary
    
    def _generate_integrity_info(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate integrity information"""
        # Collect all file hashes for overall manifest hash
        file_hashes = []
        for file_info in files:
            if "hash" in file_info and "value" in file_info["hash"]:
                file_hashes.append(file_info["hash"]["value"])
        
        # Create manifest hash from sorted file hashes
        manifest_hash = ""
        if file_hashes:
            combined_hashes = "".join(sorted(file_hashes))
            manifest_hash = hashlib.sha256(combined_hashes.encode()).hexdigest()
        
        integrity = {
            "manifest_hash": {
                "algorithm": "SHA-256",
                "value": manifest_hash,
                "description": "Hash of all file hashes for integrity verification"
            },
            "verification_command": "oscalize verify-manifest manifest.json",
            "hash_count": len(file_hashes)
        }
        
        return integrity
    
    def _collect_metadata(self, directory: Path) -> Dict[str, Any]:
        """Collect directory-level metadata"""
        metadata = {
            "generation_environment": {
                "working_directory": str(directory),
                "user": os.getenv("USER", "unknown"),
                "hostname": os.getenv("HOSTNAME", "unknown"),
                "generator": "oscalize"
            },
            "compliance_frameworks": [
                "NIST OSCAL v1.1.3",
                "OMB M-24-15",
                "FedRAMP",
                "NIST SP 800-53 Rev 5"
            ]
        }
        
        # Add Git information if available
        git_info = self._get_git_info(directory)
        if git_info:
            metadata["source_control"] = git_info
        
        return metadata
    
    def _get_git_info(self, directory: Path) -> Optional[Dict[str, Any]]:
        """Get Git repository information if available"""
        try:
            import subprocess
            
            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get commit information
            commit_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True
            )
            
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False
            )
            
            return {
                "commit": commit_result.stdout.strip(),
                "branch": branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown",
                "repository": "oscalize"
            }
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    
    def verify_manifest(self, manifest_file: Path) -> Dict[str, Any]:
        """Verify manifest integrity"""
        logger.info(f"Verifying manifest: {manifest_file}")
        
        if not manifest_file.exists():
            return {"valid": False, "error": f"Manifest file not found: {manifest_file}"}
        
        try:
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            verification_results = {
                "valid": True,
                "timestamp": self.timestamp,
                "manifest_file": str(manifest_file),
                "files_checked": 0,
                "files_valid": 0,
                "files_missing": 0,
                "files_modified": 0,
                "errors": []
            }
            
            # Verify each file
            manifest_data = manifest.get("manifest", {})
            base_dir = Path(manifest_data.get("directory", manifest_file.parent))
            
            for file_info in manifest_data.get("files", []):
                file_path = base_dir / file_info["path"]
                verification_results["files_checked"] += 1
                
                if not file_path.exists():
                    verification_results["files_missing"] += 1
                    verification_results["errors"].append(f"Missing file: {file_info['path']}")
                    continue
                
                # Verify hash
                expected_hash = file_info.get("hash", {}).get("value", "")
                if expected_hash:
                    actual_hash = self._calculate_file_hash(file_path)
                    if actual_hash != expected_hash:
                        verification_results["files_modified"] += 1
                        verification_results["errors"].append(f"Hash mismatch: {file_info['path']}")
                        continue
                
                verification_results["files_valid"] += 1
            
            # Overall validity
            verification_results["valid"] = (
                verification_results["files_missing"] == 0 and
                verification_results["files_modified"] == 0
            )
            
            return verification_results
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Manifest verification failed: {str(e)}"
            }