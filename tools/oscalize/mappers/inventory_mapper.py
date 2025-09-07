"""
Inventory mapper

Converts CIR inventory data to OSCAL component definitions and inventory items.
Integrates with SSP system-implementation section.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_mapper import BaseMapper

logger = logging.getLogger(__name__)


class InventoryMapper(BaseMapper):
    """Mapper for inventory data to OSCAL components and inventory items"""
    
    def __init__(self, mapping_dir: Optional[Path] = None):
        super().__init__(mapping_dir)
        self.asset_type_mappings = {
            "hardware": "hardware",
            "software": "software", 
            "data": "software",  # Map data to software category
            "network": "hardware", # Map network to hardware category
            "service": "software",
            "other": "software"
        }
        
    def map(self, inventory_cir: Dict[str, Any]) -> Dict[str, Any]:
        """Map CIR inventory data to OSCAL component definition"""
        logger.info("Mapping CIR inventory data to OSCAL component definition")
        
        metadata = inventory_cir.get("metadata", {})
        assets = inventory_cir.get("assets", [])
        
        # Build component definition
        component_definition = {
            "component-definition": {
                "uuid": self.generate_uuid(),
                "metadata": self._build_metadata(metadata),
                "components": self._build_components(assets),
                "back-matter": self._build_back_matter(metadata)
            }
        }
        
        return component_definition
    
    def _build_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Build OSCAL metadata from inventory CIR metadata"""
        oscal_metadata = self.create_oscal_metadata(
            title="System Component Inventory",
            version="1.0"
        )
        
        # Add source document properties
        oscal_metadata["props"] = [
            self.create_property("source-file", metadata.get("source_file", "")),
            self.create_property("sheet-name", metadata.get("sheet_name", "")),
            self.create_property("template-version", metadata.get("template_version", "")),
            self.create_property("extraction-date", metadata.get("extraction_date", "")),
            self.create_property("file-hash", metadata.get("hash", ""))
        ]
        
        return oscal_metadata
    
    def _build_components(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build components from inventory assets"""
        components = []
        
        # Group assets by logical components
        component_groups = self._group_assets_by_component(assets)
        
        for component_name, component_assets in component_groups.items():
            component = {
                "uuid": self.generate_uuid(),
                "type": self._determine_component_type(component_assets),
                "title": component_name,
                "description": self._build_component_description(component_assets),
                "status": {"state": self._determine_component_status(component_assets)},
                "props": self._build_component_props(component_assets),
                "links": self._build_component_links(component_assets),
                "responsible-roles": self._build_responsible_roles(component_assets)
            }
            
            # Add control implementations if applicable
            control_implementations = self._build_control_implementations(component_assets)
            if control_implementations:
                component["control-implementations"] = control_implementations
            
            components.append(component)
        
        logger.info(f"Built {len(components)} components from {len(assets)} assets")
        return components
    
    def _group_assets_by_component(self, assets: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group assets into logical components"""
        groups = {}
        
        for asset in assets:
            # Determine component grouping key
            group_key = self._determine_component_group(asset)
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append(asset)
        
        return groups
    
    def _determine_component_group(self, asset: Dict[str, Any]) -> str:
        """Determine which component group an asset belongs to"""
        # Try to group by service layer first
        service_layer = asset.get("service_layer", "")
        if service_layer:
            return f"{service_layer} Layer"
        
        # Fall back to function or asset name
        function = asset.get("function", "")
        if function:
            return function
        
        # Use asset name as fallback
        return asset.get("name", "Unknown Component")
    
    def _determine_component_type(self, assets: List[Dict[str, Any]]) -> str:
        """Determine OSCAL component type from assets"""
        # Count asset types in this component
        type_counts = {}
        for asset in assets:
            asset_type = asset.get("asset_type", "other")
            mapped_type = self.asset_type_mappings.get(asset_type, "software")
            type_counts[mapped_type] = type_counts.get(mapped_type, 0) + 1
        
        # Return most common type, default to software
        if type_counts:
            return max(type_counts.items(), key=lambda x: x[1])[0]
        
        return "software"
    
    def _determine_component_status(self, assets: List[Dict[str, Any]]) -> str:
        """Determine component operational status"""
        # For now, assume all components are operational
        # Could be enhanced to check asset status or environment
        environments = {asset.get("environment", "") for asset in assets}
        
        if "Production" in environments:
            return "operational"
        elif "Development" in environments or "Test" in environments:
            return "under-development"
        else:
            return "operational"
    
    def _build_component_description(self, assets: List[Dict[str, Any]]) -> str:
        """Build component description from assets"""
        if not assets:
            return "Component description not available"
        
        # Use first asset with description, or build generic description
        for asset in assets:
            if asset.get("description"):
                return asset["description"]
        
        # Build generic description
        asset_count = len(assets)
        asset_types = {asset.get("asset_type", "unknown") for asset in assets}
        
        description = f"Component containing {asset_count} asset{'s' if asset_count != 1 else ''}"
        if asset_types:
            description += f" of type(s): {', '.join(sorted(asset_types))}"
        
        return description
    
    def _build_component_props(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build component properties from assets"""
        props = []
        
        # Add asset count
        props.append(self.create_property("asset-count", str(len(assets))))
        
        # Add environments
        environments = {asset.get("environment") for asset in assets if asset.get("environment")}
        if environments:
            props.append(self.create_property("environments", ",".join(sorted(environments))))
        
        # Add criticality levels
        criticalities = {asset.get("criticality") for asset in assets if asset.get("criticality")}
        if criticalities:
            max_criticality = self._get_max_criticality(list(criticalities))
            props.append(self.create_property("max-criticality", max_criticality))
        
        # Add public access flag
        public_assets = [asset for asset in assets if asset.get("public_access")]
        if public_assets:
            props.append(self.create_property("public-access", "true"))
        
        # Add virtual assets count
        virtual_assets = [asset for asset in assets if asset.get("virtual")]
        if virtual_assets:
            props.append(self.create_property("virtual-assets", str(len(virtual_assets))))
        
        return props
    
    def _build_component_links(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build component links from assets"""
        links = []
        
        # Add links from asset data
        for asset in assets:
            asset_links = asset.get("links", [])
            for link in asset_links:
                oscal_link = self.create_link(
                    href=link.get("href", ""),
                    rel=link.get("rel", "reference"),
                    media_type=link.get("media_type")
                )
                links.append(oscal_link)
        
        return links
    
    def _build_responsible_roles(self, assets: List[Dict[str, Any]]) -> List[str]:
        """Build responsible roles from assets"""
        roles = set()
        
        for asset in assets:
            if asset.get("asset_owner"):
                roles.add("asset-owner")
            if asset.get("system_admin"):
                roles.add("system-administrator")
        
        return list(roles)
    
    def _build_control_implementations(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build control implementations for component"""
        # This is a placeholder - would be enhanced with actual control mapping
        implementations = []
        
        # Check if component handles sensitive data
        has_sensitive_data = any(
            asset.get("criticality") in ["High", "Critical"]
            for asset in assets
        )
        
        if has_sensitive_data:
            # Add basic access control implementation
            implementation = {
                "uuid": self.generate_uuid(),
                "source": "https://raw.githubusercontent.com/usnistgov/oscal-content/master/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json",
                "description": "Implementation of access controls for sensitive data handling",
                "implemented-requirements": [
                    {
                        "uuid": self.generate_uuid(),
                        "control-id": "AC-3",
                        "description": "Access controls implemented at component level"
                    }
                ]
            }
            implementations.append(implementation)
        
        return implementations
    
    def _build_back_matter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Build back-matter section"""
        resources = []
        
        # Add source document reference
        source_file = metadata.get("source_file")
        if source_file:
            resource = self.create_back_matter_resource(
                title=f"Inventory Source: {Path(source_file).name}",
                source_path=source_file,
                description="Original inventory spreadsheet used for component generation"
            )
            
            # Add additional metadata
            resource["props"] = [
                self.create_property("template-version", metadata.get("template_version", "")),
                self.create_property("sheet-name", metadata.get("sheet_name", "")),
                self.create_property("file-hash", metadata.get("hash", ""))
            ]
            
            resources.append(resource)
        
        return {
            "resources": resources
        }
    
    def build_inventory_items_for_ssp(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build inventory items for SSP system-implementation"""
        inventory_items = []
        
        for asset in assets:
            item = {
                "uuid": self.generate_uuid(),
                "description": asset.get("description", asset.get("name", "")),
                "props": self._build_asset_props(asset)
            }
            
            # Add responsible parties
            responsible_parties = {}
            if asset.get("asset_owner"):
                responsible_parties["asset-owner"] = [
                    {"party-uuid": self.generate_uuid()}  # Should reference actual party
                ]
            if asset.get("system_admin"):
                responsible_parties["system-administrator"] = [
                    {"party-uuid": self.generate_uuid()}  # Should reference actual party
                ]
            
            if responsible_parties:
                item["responsible-parties"] = responsible_parties
            
            # Add implemented components reference
            item["implemented-components"] = [
                {
                    "component-uuid": self.generate_uuid(),  # Should reference actual component
                    "props": [
                        self.create_property("asset-id", asset.get("asset_id", ""))
                    ]
                }
            ]
            
            inventory_items.append(item)
        
        return inventory_items
    
    def _build_asset_props(self, asset: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build properties for individual asset"""
        props = []
        
        # Add core asset properties
        core_fields = [
            "asset_id", "asset_type", "name", "environment", 
            "criticality", "baseline", "operating_system", 
            "software_version", "patch_level"
        ]
        
        for field in core_fields:
            value = asset.get(field)
            if value:
                prop_name = field.replace("_", "-")
                props.append(self.create_property(prop_name, str(value)))
        
        # Add network properties
        if asset.get("ip_address"):
            props.append(self.create_property("ip-address", asset["ip_address"]))
        
        if asset.get("mac_address"):
            props.append(self.create_property("mac-address", asset["mac_address"]))
        
        if asset.get("vlan"):
            props.append(self.create_property("vlan", asset["vlan"]))
        
        # Add boolean properties
        if asset.get("public_access"):
            props.append(self.create_property("public-access", "true"))
        
        if asset.get("virtual"):
            props.append(self.create_property("virtual", "true"))
        
        # Add tags as properties
        tags = asset.get("tags", [])
        if tags:
            props.append(self.create_property("tags", ",".join(tags)))
        
        return props
    
    def _get_max_criticality(self, criticalities: List[str]) -> str:
        """Get highest criticality level from list"""
        priority_order = ["Critical", "High", "Moderate", "Low"]
        
        for level in priority_order:
            if level in criticalities:
                return level
        
        return "Low"  # Default