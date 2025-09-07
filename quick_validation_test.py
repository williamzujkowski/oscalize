#!/usr/bin/env python3
"""
Quick validation test to verify our OSCAL structural fixes
"""
import json
from pathlib import Path

def test_ssp_fixes(ssp_path):
    """Test SSP structural fixes"""
    with open(ssp_path) as f:
        ssp = json.load(f)
    
    ssp_content = ssp["system-security-plan"]
    issues = []
    
    # Test 1: Components have responsible-roles
    components = ssp_content.get("system-implementation", {}).get("components", [])
    for i, component in enumerate(components):
        roles = component.get("responsible-roles", [])
        if len(roles) == 0:
            issues.append(f"Component {i} missing responsible-roles")
    
    # Test 2: User authorized-privileges are objects
    users = ssp_content.get("system-implementation", {}).get("users", [])
    for i, user in enumerate(users):
        privileges = user.get("authorized-privileges", [])
        for j, priv in enumerate(privileges):
            if isinstance(priv, str):
                issues.append(f"User {i} privilege {j} is string, should be object")
    
    # Test 3: System characteristics has status
    status = ssp_content.get("system-characteristics", {}).get("status")
    if not status:
        issues.append("Missing system-characteristics status field")
    
    # Test 4: Information types exist
    info_types = ssp_content.get("system-characteristics", {}).get("system-information", {}).get("information-types", [])
    if len(info_types) == 0:
        issues.append("Missing information-types (minimum count violation)")
    
    # Test 5: Back-matter rlinks don't have "rel" keys
    resources = ssp_content.get("back-matter", {}).get("resources", [])
    for i, resource in enumerate(resources):
        rlinks = resource.get("rlinks", [])
        for j, rlink in enumerate(rlinks):
            if "rel" in rlink:
                issues.append(f"Back-matter resource {i} rlink {j} has prohibited 'rel' key")
    
    return issues

def test_poam_fixes(poam_path):
    """Test POA&M structural fixes"""
    with open(poam_path) as f:
        poam = json.load(f)
    
    poam_content = poam["plan-of-action-and-milestones"]
    issues = []
    
    # Test: Origins have actors array (not actor)
    items = poam_content.get("poam-items", [])
    for i, item in enumerate(items):
        origins = item.get("origins", [])
        for j, origin in enumerate(origins):
            if "actor" in origin:  # Old format
                issues.append(f"POA&M item {i} origin {j} has old 'actor' key")
            if "actors" not in origin:  # Missing new format
                issues.append(f"POA&M item {i} origin {j} missing 'actors' array")
    
    return issues

def main():
    """Run quick validation tests"""
    print("🔍 Quick OSCAL Structural Validation Test")
    print("=" * 50)
    
    ssp_path = Path("dist/oscal/ssp.json")
    poam_path = Path("dist/oscal/poam.json")
    
    if not ssp_path.exists():
        print("❌ SSP file not found")
        return
    
    if not poam_path.exists():
        print("❌ POA&M file not found") 
        return
    
    # Test SSP fixes
    print("\n📋 Testing SSP structural fixes...")
    ssp_issues = test_ssp_fixes(ssp_path)
    if ssp_issues:
        print("❌ SSP Issues found:")
        for issue in ssp_issues:
            print(f"  - {issue}")
    else:
        print("✅ All SSP structural fixes verified!")
    
    # Test POA&M fixes
    print("\n📋 Testing POA&M structural fixes...")
    poam_issues = test_poam_fixes(poam_path)
    if poam_issues:
        print("❌ POA&M Issues found:")
        for issue in poam_issues:
            print(f"  - {issue}")
    else:
        print("✅ All POA&M structural fixes verified!")
    
    # Summary
    total_issues = len(ssp_issues) + len(poam_issues)
    print(f"\n🎯 Summary: {total_issues} structural issues remaining")
    
    if total_issues == 0:
        print("🎉 All major structural fixes successfully applied!")
    
    return total_issues == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)