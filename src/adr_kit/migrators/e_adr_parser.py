"""Parser for ste-runtime E-ADR markdown format."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class EADRMetadata:
    """E-ADR metadata extracted from markdown header."""
    
    id: str
    title: str
    status: str
    implementation: Optional[str]
    date: str
    author: str
    authority: Optional[str]
    next_step: Optional[str]


@dataclass
class EADRContent:
    """E-ADR content sections."""
    
    metadata: EADRMetadata
    context: str
    decision: str
    rationale: str
    specification: str
    consequences: str
    implementation_notes: Optional[str] = None
    future_work: Optional[str] = None
    references: Optional[str] = None
    other_sections: Optional[Dict[str, str]] = None


class EADRParser:
    """Parse ste-runtime E-ADR markdown files."""
    
    def parse_file(self, file_path: Path) -> EADRContent:
        """Parse E-ADR markdown file.
        
        Args:
            file_path: Path to E-ADR markdown file
            
        Returns:
            Parsed EADRContent
            
        Raises:
            ValueError: If file cannot be parsed
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ValueError(f"E-ADR file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract metadata
        metadata = self._parse_metadata(content, file_path)
        
        # Split into sections
        sections = self._split_sections(content)
        
        # Extract standard sections
        eadr_content = EADRContent(
            metadata=metadata,
            context=sections.get("Context", ""),
            decision=sections.get("Decision", ""),
            rationale=sections.get("Rationale", ""),
            specification=sections.get("Specification", ""),
            consequences=sections.get("Consequences", ""),
            implementation_notes=sections.get("Implementation", sections.get("Implementation Notes")),
            future_work=sections.get("Future Work", sections.get("Future Considerations")),
            references=sections.get("References", ""),
        )
        
        # Capture any other sections
        standard_sections = {
            "Context", "Decision", "Rationale", "Specification", 
            "Consequences", "Implementation", "Implementation Notes",
            "Future Work", "Future Considerations", "References"
        }
        other_sections = {k: v for k, v in sections.items() if k not in standard_sections}
        if other_sections:
            eadr_content.other_sections = other_sections
        
        return eadr_content
    
    def _parse_metadata(self, content: str, file_path: Path) -> EADRMetadata:
        """Parse metadata from E-ADR header.
        
        Args:
            content: Full markdown content
            file_path: Path to file (for extracting ID from filename)
            
        Returns:
            EADRMetadata
        """
        lines = content.split('\n')
        
        # Extract title (first line, after # )
        title_match = re.match(r'^#\s+(.+)$', lines[0])
        if not title_match:
            raise ValueError(f"Cannot extract title from first line: {lines[0]}")
        
        title_full = title_match.group(1)
        
        # Extract ID from title (E-ADR-XXX: Title)
        id_match = re.match(r'^(E-ADR-\d+):\s*(.+)$', title_full)
        if id_match:
            eadr_id = id_match.group(1)
            title = id_match.group(2)
        else:
            # Fallback: extract from filename
            eadr_id = file_path.stem.split('-')[0:3]  # E-ADR-001
            eadr_id = '-'.join(eadr_id)
            title = title_full
        
        # Extract metadata fields (bold text format: **Field:** Value)
        metadata_fields = {}
        for line in lines[1:20]:  # Check first 20 lines for metadata
            match = re.match(r'^\*\*([^*]+):\*\*\s*(.+)$', line)
            if match:
                field = match.group(1).strip()
                value = match.group(2).strip()
                metadata_fields[field.lower()] = value
        
        # Extract "Next Step" from blockquote
        next_step = None
        for line in lines[1:20]:
            if line.startswith('> **Next Step:**'):
                next_step = line.replace('> **Next Step:**', '').strip()
            elif line.startswith('> **Purpose:**'):
                # Some E-ADRs use Purpose instead
                next_step = line.replace('> **Purpose:**', '').strip()
        
        return EADRMetadata(
            id=eadr_id,
            title=title,
            status=metadata_fields.get("status", "unknown"),
            implementation=metadata_fields.get("implementation"),
            date=metadata_fields.get("date", ""),
            author=metadata_fields.get("author", ""),
            authority=metadata_fields.get("authority"),
            next_step=next_step,
        )
    
    def _split_sections(self, content: str) -> Dict[str, str]:
        """Split markdown into sections by ## headers.
        
        Args:
            content: Full markdown content
            
        Returns:
            Dict mapping section name to section content
        """
        sections = {}
        current_section = None
        current_content = []
        
        lines = content.split('\n')
        
        # Skip header and metadata (first ~15 lines)
        in_header = True
        
        for line in lines:
            # Detect end of header (first --- separator)
            if line.strip() == '---' and in_header:
                in_header = False
                continue
            
            if in_header:
                continue
            
            # Check for section header (## Section Name)
            section_match = re.match(r'^##\s+(.+)$', line)
            if section_match:
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = section_match.group(1).strip()
                current_content = []
            else:
                # Add to current section
                if current_section:
                    current_content.append(line)
        
        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
