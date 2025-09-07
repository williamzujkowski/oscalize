"""
Document reader for DOCX and Markdown files

Converts SSP documents to CIR format using Pandoc for consistent processing.
Maintains source attribution for all sections and content.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from .base_reader import BaseReader

logger = logging.getLogger(__name__)


class DocumentReader(BaseReader):
    """Reader for DOCX and Markdown SSP documents"""
    
    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self.source_type = self._detect_source_type()
        
    def _detect_source_type(self) -> str:
        """Detect document type from file extension"""
        suffix = self.file_path.suffix.lower()
        if suffix == '.docx':
            return 'docx'
        elif suffix in ['.md', '.markdown']:
            return 'md'
        else:
            raise ValueError(f"Unsupported document type: {suffix}")
    
    def to_cir(self) -> Dict[str, Any]:
        """Convert document to CIR format"""
        logger.info(f"Converting {self.source_type.upper()} document: {self.file_path}")
        
        # Get Pandoc version for metadata
        pandoc_version = self._get_pandoc_version()
        
        # Convert to Pandoc JSON AST
        pandoc_json = self._convert_to_pandoc_json()
        
        # Extract sections from AST
        sections = self._extract_sections(pandoc_json)
        
        return {
            "metadata": self._create_base_metadata(
                self.source_type,
                pandoc_version=pandoc_version
            ),
            "sections": sections
        }
    
    def _get_pandoc_version(self) -> str:
        """Get Pandoc version for reproducibility"""
        try:
            result = subprocess.run(
                ['pandoc', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            # Extract first line which contains version
            return result.stdout.split('\n')[0].strip()
        except subprocess.CalledProcessError:
            logger.warning("Could not determine Pandoc version")
            return "unknown"
    
    def _convert_to_pandoc_json(self) -> Dict[str, Any]:
        """Convert document to Pandoc JSON AST"""
        try:
            # Use temporary file for Pandoc JSON output
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            # Convert document to Pandoc JSON
            cmd = [
                'pandoc',
                str(self.file_path),
                '--to', 'json',
                '--output', str(temp_path)
            ]
            
            if self.source_type == 'docx':
                # Extract embedded media for DOCX
                cmd.extend(['--extract-media', str(self.file_path.parent / 'media')])
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Read the JSON AST
            with open(temp_path, 'r', encoding='utf-8') as f:
                pandoc_json = json.load(f)
            
            # Clean up temporary file
            temp_path.unlink()
            
            return pandoc_json
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Pandoc conversion failed: {e.stderr.decode()}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid Pandoc JSON output: {e}")
    
    def _extract_sections(self, pandoc_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract sections from Pandoc JSON AST"""
        blocks = pandoc_json.get('blocks', [])
        sections = []
        current_section = None
        section_counter = 0
        
        for i, block in enumerate(blocks):
            if block.get('t') == 'Header':
                # Start new section
                if current_section is not None:
                    sections.append(current_section)
                
                section_counter += 1
                level = block['c'][0]  # Header level
                attr = block['c'][1]   # Attributes (id, classes, key-values)
                inlines = block['c'][2]  # Header text
                
                title = self._extract_inline_text(inlines)
                section_id = attr[0] if attr[0] else f"section-{section_counter}"
                
                current_section = {
                    "id": section_id,
                    "title": title,
                    "level": level,
                    "text": "",
                    "tables": [],
                    "source": self._create_source_reference(
                        heading_path=self._build_heading_path(sections, level, title),
                        paragraph_start=i,
                        paragraph_end=i
                    )
                }
            
            elif current_section is not None:
                # Add content to current section
                if block.get('t') == 'Table':
                    table = self._extract_table(block, current_section["id"], len(current_section["tables"]))
                    current_section["tables"].append(table)
                else:
                    # Convert block to text and add to section
                    block_text = self._block_to_text(block)
                    if block_text.strip():
                        current_section["text"] += block_text + "\n\n"
                
                # Update paragraph end
                current_section["source"]["paragraph_end"] = i
        
        # Add final section
        if current_section is not None:
            sections.append(current_section)
        
        return sections
    
    def _extract_inline_text(self, inlines: List[Dict[str, Any]]) -> str:
        """Extract plain text from Pandoc inline elements"""
        text_parts = []
        for inline in inlines:
            if inline.get('t') == 'Str':
                text_parts.append(inline['c'])
            elif inline.get('t') == 'Space':
                text_parts.append(' ')
            elif inline.get('t') in ['Strong', 'Emph', 'Code']:
                # Recursively extract from formatted text
                text_parts.append(self._extract_inline_text(inline['c']))
            elif inline.get('t') == 'Link':
                # Extract link text
                text_parts.append(self._extract_inline_text(inline['c'][1]))
        
        return ''.join(text_parts)
    
    def _extract_table(self, table_block: Dict[str, Any], section_id: str, table_index: int) -> Dict[str, Any]:
        """Extract table from Pandoc table block"""
        # Pandoc table structure varies by version, handle both formats
        if 'c' in table_block and len(table_block['c']) >= 5:
            # Newer Pandoc format
            caption_block = table_block['c'][0]
            headers_row = table_block['c'][3]
            body_rows = table_block['c'][4]
            
            # Extract caption
            caption = ""
            if caption_block and 'c' in caption_block:
                caption = self._extract_inline_text(caption_block['c'])
            
            # Extract headers
            headers = []
            if headers_row:
                for cell in headers_row:
                    cell_text = self._extract_cell_text(cell)
                    headers.append(cell_text)
            
            # Extract rows
            rows = []
            for row in body_rows:
                if isinstance(row, list) and row:
                    # Handle row structure
                    row_cells = row[0] if isinstance(row[0], list) else row
                    row_data = []
                    for cell in row_cells:
                        cell_text = self._extract_cell_text(cell)
                        row_data.append(cell_text)
                    rows.append(row_data)
        
        return {
            "id": f"table-{section_id}-{table_index}",
            "caption": caption,
            "headers": headers,
            "rows": rows,
            "source": {
                "section_id": section_id,
                "table_index": table_index
            }
        }
    
    def _extract_cell_text(self, cell: Dict[str, Any]) -> str:
        """Extract text from table cell"""
        if not cell or 'c' not in cell:
            return ""
        
        # Cell contains list of blocks
        blocks = cell['c']
        text_parts = []
        
        for block in blocks:
            block_text = self._block_to_text(block)
            if block_text.strip():
                text_parts.append(block_text.strip())
        
        return ' '.join(text_parts)
    
    def _block_to_text(self, block: Dict[str, Any]) -> str:
        """Convert Pandoc block to plain text"""
        block_type = block.get('t', '')
        
        if block_type == 'Para':
            return self._extract_inline_text(block['c'])
        elif block_type == 'Plain':
            return self._extract_inline_text(block['c'])
        elif block_type == 'CodeBlock':
            return block['c'][1]  # Code content
        elif block_type == 'BulletList':
            items = []
            for item in block['c']:
                item_text = self._blocks_to_text(item)
                items.append(f"• {item_text}")
            return '\n'.join(items)
        elif block_type == 'OrderedList':
            items = []
            for i, item in enumerate(block['c'][1], 1):
                item_text = self._blocks_to_text(item)
                items.append(f"{i}. {item_text}")
            return '\n'.join(items)
        elif block_type == 'BlockQuote':
            quoted_text = self._blocks_to_text(block['c'])
            return f"> {quoted_text}"
        
        return ""
    
    def _blocks_to_text(self, blocks: List[Dict[str, Any]]) -> str:
        """Convert list of blocks to text"""
        text_parts = []
        for block in blocks:
            block_text = self._block_to_text(block)
            if block_text.strip():
                text_parts.append(block_text.strip())
        return ' '.join(text_parts)
    
    def _build_heading_path(self, existing_sections: List[Dict[str, Any]], 
                          level: int, title: str) -> List[str]:
        """Build hierarchical path to current heading"""
        path = []
        
        # Find parent headings
        for section in existing_sections:
            if section['level'] < level:
                path = section['source']['heading_path'] + [section['title']]
        
        return path + [title]