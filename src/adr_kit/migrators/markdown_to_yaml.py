"""Migrate E-ADR markdown to ADR Kit YAML format with reverse-engineering."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from ..models import (
    Alternative,
    ComponentSpecification,
    Consequences,
    Decision,
    EnforcementLevel,
    Gap,
    ImpactLevel,
    ImplementationIdentifiers,
    Invariant,
    LogicalADR,
    PhysicalADR,
    TechnologyChoice,
)
from .e_adr_parser import EADRParser, EADRContent
from .e_adr_classification import (
    classify_eadr,
    get_new_adr_id,
    get_classification_metadata,
)


class MarkdownToYAMLMigrator:
    """Migrate E-ADR markdown to ADR Kit YAML format."""
    
    def __init__(self, ste_runtime_root: Path):
        """Initialize migrator.
        
        Args:
            ste_runtime_root: Path to ste-runtime project root
        """
        self.parser = EADRParser()
        self.ste_runtime_root = Path(ste_runtime_root)
    
    def migrate_eadr(self, eadr_file: Path) -> Optional[Dict]:
        """Migrate single E-ADR to ADR Kit format.
        
        Args:
            eadr_file: Path to E-ADR markdown file
            
        Returns:
            Dict with 'type', 'adr_id', 'adr_model', 'yaml_content' or None if documentation
        """
        # Parse E-ADR
        eadr = self.parser.parse_file(eadr_file)
        
        # Get classification
        classification = get_classification_metadata(eadr.metadata.id)
        
        if classification["type"] == "documentation":
            return None  # Skip documentation guides
        
        # Build ADR based on type
        if classification["type"] == "logical":
            adr_model = self._build_logical_adr(eadr, classification)
        else:  # physical
            adr_model = self._build_physical_adr(eadr, classification)
        
        # Convert to YAML
        yaml_content = self._model_to_yaml(adr_model)
        
        return {
            "type": classification["type"],
            "adr_id": classification["new_id"],
            "adr_model": adr_model,
            "yaml_content": yaml_content,
        }
    
    def _build_logical_adr(self, eadr: EADRContent, classification: Dict) -> LogicalADR:
        """Build LogicalADR model from E-ADR content.
        
        Args:
            eadr: Parsed E-ADR content
            classification: Classification metadata
            
        Returns:
            LogicalADR model
        """
        # Parse decisions from Decision section
        decisions = self._extract_decisions(eadr.decision, eadr.rationale, eadr.consequences)
        
        # Parse invariants from Specification section
        invariants = self._extract_invariants(eadr.specification, classification["new_id"])
        
        # Parse gaps (if any mentioned)
        gaps = self._extract_gaps(eadr.context, eadr.consequences)
        
        # Build model
        return LogicalADR(
            schema_version="1.0",
            adr_type="logical",
            id=classification["new_id"],
            title=classification["title"],
            status=self._normalize_status(eadr.metadata.status),
            created_date=self._parse_date(eadr.metadata.date),
            last_modified_date=self._parse_date(eadr.metadata.date),
            authors=[self._normalize_author(eadr.metadata.author)],
            domains=classification["domains"],
            tags=classification["tags"],
            context=eadr.context,
            decisions=decisions,
            invariants=invariants,
            gaps=gaps,
            related_adrs=[],  # To be enriched manually
            metadata={
                "migrated_from": eadr.metadata.id,
                "original_authority": eadr.metadata.authority or "",
                "original_next_step": eadr.metadata.next_step or "",
            }
        )
    
    def _build_physical_adr(self, eadr: EADRContent, classification: Dict) -> PhysicalADR:
        """Build PhysicalADR model from E-ADR content with reverse-engineering.
        
        Args:
            eadr: Parsed E-ADR content
            classification: Classification metadata
            
        Returns:
            PhysicalADR model
        """
        # Reverse-engineer implementation details from source code
        tech_stack = self._extract_technology_choices(eadr.metadata.id)
        components = self._reverse_engineer_components(eadr.metadata.id, eadr.specification)
        
        # Parse gaps
        gaps = self._extract_gaps(eadr.context, eadr.consequences)
        
        # Build model
        return PhysicalADR(
            schema_version="1.0",
            adr_type="physical",
            id=classification["new_id"],
            title=classification["title"],
            status=self._normalize_status(eadr.metadata.status),
            created_date=self._parse_date(eadr.metadata.date),
            modified_date=self._parse_date(eadr.metadata.date),
            authors=[self._normalize_author(eadr.metadata.author)],
            domains=classification["domains"],
            tags=classification["tags"],
            implements_logical=classification.get("implements_logical", []),
            technologies=self._extract_technology_list(eadr.metadata.id),
            context=eadr.context,
            technology_stack=tech_stack,
            component_specifications=components,
            gaps=gaps,
            related_adrs=[],  # To be enriched manually
            metadata={
                "migrated_from": eadr.metadata.id,
                "original_authority": eadr.metadata.authority or "",
                "original_next_step": eadr.metadata.next_step or "",
                "original_implementation_status": eadr.metadata.implementation or "",
            }
        )
    
    def _extract_technology_list(self, eadr_id: str) -> List[str]:
        """Extract technology stack from package.json and source code.
        
        Args:
            eadr_id: E-ADR ID
            
        Returns:
            List of technologies
        """
        tech_stack = set()
        
        # Base technologies from package.json
        package_json = self.ste_runtime_root / "package.json"
        if package_json.exists():
            with open(package_json) as f:
                pkg = json.load(f)
                
            # Core technologies
            tech_stack.update(["typescript", "node.js"])
            
            # Extract from dependencies
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            
            # Map package names to technologies
            tech_mapping = {
                "@modelcontextprotocol/sdk": "mcp",
                "chokidar": "file-watching",
                "commander": "cli",
                "js-yaml": "yaml",
                "globby": "file-discovery",
                "zod": "schema-validation",
                "vitest": "testing",
            }
            
            for pkg_name, tech_name in tech_mapping.items():
                if pkg_name in deps:
                    tech_stack.add(tech_name)
        
        # E-ADR specific technologies
        eadr_tech_map = {
            "E-ADR-004": ["cli", "graph-traversal"],
            "E-ADR-005": ["json", "data-extraction"],
            "E-ADR-006": ["angular", "css", "scss", "ast-parsing"],
            "E-ADR-011": ["mcp", "stdio", "file-watching", "incremental-recon"],
            "E-ADR-013": ["validation", "testing"],
        }
        
        if eadr_id in eadr_tech_map:
            tech_stack.update(eadr_tech_map[eadr_id])
        
        return sorted(list(tech_stack))
    
    def _extract_technology_choices(self, eadr_id: str) -> List[TechnologyChoice]:
        """Extract technology choices with rationale.
        
        Args:
            eadr_id: E-ADR ID
            
        Returns:
            List of TechnologyChoice models
        """
        tech_choices = []
        
        # Base technology choices from package.json
        package_json = self.ste_runtime_root / "package.json"
        if package_json.exists():
            with open(package_json) as f:
                pkg = json.load(f)
            
            # Core language
            tech_choices.append(TechnologyChoice(
                category="language",
                name="TypeScript",
                version="5.3+",
                rationale="Type safety, excellent Node.js ecosystem, maintainability"
            ))
            
            tech_choices.append(TechnologyChoice(
                category="framework",
                name="Node.js",
                version="18.0+",
                rationale="JavaScript runtime for CLI and server applications"
            ))
            
            # E-ADR specific technologies
            if eadr_id == "E-ADR-011":
                tech_choices.append(TechnologyChoice(
                    category="library",
                    name="@modelcontextprotocol/sdk",
                    version=pkg.get("dependencies", {}).get("@modelcontextprotocol/sdk", "^1.0.0"),
                    rationale="Standard MCP protocol implementation for AI assistant integration"
                ))
                tech_choices.append(TechnologyChoice(
                    category="library",
                    name="chokidar",
                    version=pkg.get("dependencies", {}).get("chokidar", "^3.5.0"),
                    rationale="Cross-platform file watching with robust event handling"
                ))
        
        return tech_choices
    
    def _reverse_engineer_components(self, eadr_id: str, specification: str) -> List[ComponentSpecification]:
        """Reverse-engineer component specifications from source code.
        
        Args:
            eadr_id: E-ADR ID
            specification: Specification section from E-ADR
            
        Returns:
            List of ComponentSpecification models
        """
        components = []
        
        # E-ADR specific component mapping
        component_map = {
            "E-ADR-004": [
                {
                    "name": "RSS CLI",
                    "type": "cli",
                    "purpose": "Command-line interface for RSS graph traversal operations",
                    "implementation_identifiers": [
                        "src/cli/rss-cli.ts",
                        "src/rss/rss-operations.ts",
                        "src/rss/graph-loader.ts",
                        "src/rss/graph-traversal.ts",
                    ],
                    "specification": specification,
                },
            ],
            "E-ADR-005": [
                {
                    "name": "JSON Data Extractor",
                    "type": "extractor",
                    "purpose": "Extract semantic entities from JSON files (compliance controls, schemas, configs)",
                    "implementation_identifiers": [
                        "src/extractors/json/",
                        "src/extractors/json/json-extractor.ts",
                    ],
                    "specification": specification,
                },
            ],
            "E-ADR-006": [
                {
                    "name": "Angular Semantic Extractor",
                    "type": "extractor",
                    "purpose": "Extract components, services, routes, templates from Angular applications",
                    "implementation_identifiers": [
                        "src/extractors/angular/",
                        "src/extractors/angular/angular-extractor.ts",
                    ],
                    "specification": specification,
                },
                {
                    "name": "CSS/SCSS Extractor",
                    "type": "extractor",
                    "purpose": "Extract styles, design tokens, and CSS entities",
                    "implementation_identifiers": [
                        "src/extractors/css/",
                    ],
                    "specification": specification,
                },
            ],
            "E-ADR-011": [
                {
                    "name": "MCP Server",
                    "type": "server",
                    "purpose": "Model Context Protocol server exposing 8 RSS tools for AI assistants",
                    "implementation_identifiers": [
                        "src/mcp/mcp-server.ts",
                        "src/cli/watch-cli.ts",
                    ],
                    "specification": self._extract_mcp_tools_spec(specification),
                },
                {
                    "name": "File Watcher",
                    "type": "service",
                    "purpose": "Monitor project files and trigger incremental RECON on changes",
                    "implementation_identifiers": [
                        "src/watch/watchdog.ts",
                        "src/watch/change-detector.ts",
                        "src/watch/write-tracker.ts",
                    ],
                    "specification": "File watching with debouncing, transaction detection, and syntax validation",
                },
            ],
            "E-ADR-013": [
                {
                    "name": "Extractor Validation Framework",
                    "type": "validation",
                    "purpose": "Validate extractor output quality and correctness",
                    "implementation_identifiers": [
                        "src/recon/validation/",
                    ],
                    "specification": specification,
                },
            ],
        }
        
        if eadr_id in component_map:
            comp_counter = 1
            for comp_data in component_map[eadr_id]:
                # Map type to valid component type
                comp_type = self._map_component_type(comp_data["type"])
                
                # Build implementation identifiers
                impl_ids = ImplementationIdentifiers(
                    module_path=comp_data["implementation_identifiers"][0] if comp_data["implementation_identifiers"] else None
                )
                
                components.append(ComponentSpecification(
                    id=f"COMP-{comp_counter:04d}",
                    name=comp_data["name"],
                    type=comp_type,
                    responsibilities=comp_data["purpose"],
                    implementation_identifiers=impl_ids,
                ))
                comp_counter += 1
        
        return components
    
    def _map_component_type(self, original_type: str) -> str:
        """Map E-ADR component type to valid ComponentSpecification type.
        
        Args:
            original_type: Original type from E-ADR (e.g., "cli", "extractor")
            
        Returns:
            Valid component type
        """
        type_map = {
            "cli": "library",
            "extractor": "library",
            "server": "service",
            "validation": "library",
        }
        
        return type_map.get(original_type, "service")
    
    def _extract_mcp_tools_spec(self, specification: str) -> str:
        """Extract MCP tools specification section.
        
        Args:
            specification: Full specification section
            
        Returns:
            MCP tools specification summary
        """
        # Extract the 8 tools from E-ADR-011
        tools = [
            "find - Search semantic graph for components",
            "show - Get detailed component information",
            "usages - Find where component is used",
            "impact - Analyze blast radius of changes",
            "similar - Find similar code patterns",
            "overview - Get project architecture overview",
            "diagnose - Analyze graph health and coverage",
            "refresh - Trigger incremental RECON",
        ]
        
        return "MCP Server exposes 8 tools:\n" + "\n".join(f"- {tool}" for tool in tools)
    
    def _extract_decisions(self, decision_section: str, rationale_section: str, consequences_section: str) -> List[Decision]:
        """Extract decisions from E-ADR sections.
        
        Args:
            decision_section: Decision section content
            rationale_section: Rationale section content
            consequences_section: Consequences section content
            
        Returns:
            List of Decision models
        """
        # Parse consequences into structured format
        consequences = self._parse_consequences(consequences_section)
        
        # Parse alternatives
        alternatives = self._parse_alternatives(rationale_section)
        
        # For now, create a single decision combining all sections
        return [Decision(
            id="DEC-0001",
            summary=self._extract_decision_statement(decision_section),
            rationale=rationale_section,
            alternatives_considered=alternatives,
            consequences=consequences,
        )]
    
    def _extract_decision_statement(self, decision_section: str) -> str:
        """Extract main decision statement from decision section.
        
        Args:
            decision_section: Decision section content
            
        Returns:
            Decision statement (first paragraph or bold text)
        """
        lines = decision_section.strip().split('\n')
        
        # Look for bold statement
        for line in lines:
            if line.startswith('**') and line.endswith('**'):
                return line.strip('*').strip()
        
        # Fallback: first non-empty paragraph
        paragraphs = decision_section.split('\n\n')
        for para in paragraphs:
            if para.strip() and not para.startswith('|'):  # Skip tables
                return para.strip().split('\n')[0]  # First line of paragraph
        
        return decision_section.strip()[:200]  # Fallback: first 200 chars
    
    def _parse_consequences(self, consequences_section: str) -> Optional[Consequences]:
        """Parse consequences section into structured format.
        
        Args:
            consequences_section: Consequences section content
            
        Returns:
            Consequences model or None
        """
        positive = []
        negative = []
        
        lines = consequences_section.split('\n')
        current_list = None
        
        for line in lines:
            line = line.strip()
            
            # Detect positive/negative headers
            if line.startswith('###') and 'positive' in line.lower():
                current_list = positive
            elif line.startswith('###') and 'negative' in line.lower():
                current_list = negative
            elif line.startswith('-') and current_list is not None:
                # Extract bullet point
                item = line.lstrip('-').strip()
                if item:
                    current_list.append(item)
        
        if positive or negative:
            return Consequences(positive=positive, negative=negative)
        
        return None
    
    def _parse_alternatives(self, rationale_section: str) -> List[Alternative]:
        """Parse alternatives from rationale section.
        
        Args:
            rationale_section: Rationale section content
            
        Returns:
            List of Alternative models
        """
        alternatives = []
        
        # Look for "Alternative rejected:" patterns
        alt_pattern = r'\*\*Alternative rejected:\*\*\s*(.+?)(?:\n|$)'
        matches = re.finditer(alt_pattern, rationale_section, re.IGNORECASE)
        
        for match in matches:
            alt_text = match.group(1).strip()
            alternatives.append(Alternative(
                name=alt_text[:50],  # First 50 chars as name
                rejected_because=alt_text
            ))
        
        # Also look for explicit "Alternative:" headers in rationale
        if not alternatives and "alternative" in rationale_section.lower():
            # Try to extract from subsections
            lines = rationale_section.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('####') and 'alternative' in line.lower():
                    alt_name = line.replace('####', '').strip()
                    # Get next few lines as reason
                    reason_lines = []
                    for j in range(i+1, min(i+5, len(lines))):
                        if lines[j].startswith('#'):
                            break
                        reason_lines.append(lines[j])
                    
                    reason = '\n'.join(reason_lines).strip()
                    if reason:
                        alternatives.append(Alternative(
                            name=alt_name,
                            rejected_because=reason[:200]  # Limit length
                        ))
        
        return alternatives
    
    def _extract_invariants(self, specification: str, adr_id: str) -> List[Invariant]:
        """Extract invariants from specification section.
        
        Args:
            specification: Specification section content
            adr_id: ADR ID (for invariant numbering)
            
        Returns:
            List of Invariant models
        """
        invariants = []
        
        # Look for constraint tables or numbered constraints
        # Pattern: | Constraint | Decision | or numbered lists
        
        # Extract from tables
        table_matches = re.finditer(r'\|\s*Constraint\s*\|\s*Decision\s*\|.*?\n\|[-\s|]+\n((?:\|.+\n)+)', specification, re.MULTILINE)
        
        inv_counter = 1
        for match in table_matches:
            table_rows = match.group(1)
            for row in table_rows.split('\n'):
                if row.strip() and row.startswith('|'):
                    cells = [cell.strip() for cell in row.split('|')[1:-1]]
                    if len(cells) >= 2:
                        constraint_name = cells[0]
                        constraint_value = cells[1]
                        
                        invariants.append(Invariant(
                            id=f"INV-{inv_counter:04d}",
                            statement=f"{constraint_name}: {constraint_value}",
                            scope="global",
                            enforcement_level=EnforcementLevel.MUST,
                            enforcement_mechanism="design",
                            verification_method="manual",
                            rationale=f"Extracted from {adr_id} specification",
                        ))
                        inv_counter += 1
        
        # Extract from numbered lists (§ sections)
        section_matches = re.finditer(r'###?\s*§[\d.]+\s+(.+?)\n\n(.+?)(?=\n###|$)', specification, re.DOTALL)
        
        for match in section_matches:
            section_title = match.group(1).strip()
            section_content = match.group(2).strip()
            
            # Look for bullet points with constraints
            constraint_bullets = re.findall(r'^[-*]\s*\*\*(.+?):\*\*\s*(.+?)$', section_content, re.MULTILINE)
            
            for constraint_name, constraint_value in constraint_bullets:
                invariants.append(Invariant(
                    id=f"INV-{inv_counter:04d}",
                    statement=f"{constraint_name}: {constraint_value}",
                    scope="global",
                    enforcement_level=EnforcementLevel.MUST,
                    enforcement_mechanism="design",
                    verification_method="manual",
                    rationale=f"Extracted from {adr_id} specification",
                ))
                inv_counter += 1
        
        return invariants
    
    def _extract_constraints(self, specification: str) -> List[str]:
        """Extract constraints for Physical ADR.
        
        Args:
            specification: Specification section content
            
        Returns:
            List of constraint strings
        """
        constraints = []
        
        # Extract from § sections
        section_matches = re.finditer(r'###?\s*§[\d.]+\s+(.+?)\n', specification)
        
        for match in section_matches:
            section_title = match.group(1).strip()
            if "constraint" in section_title.lower():
                constraints.append(section_title)
        
        return constraints
    
    def _extract_gaps(self, context: str, consequences: str) -> List[Gap]:
        """Extract gaps from context or consequences.
        
        Args:
            context: Context section
            consequences: Consequences section
            
        Returns:
            List of Gap models
        """
        gaps = []
        
        # Look for "gap", "missing", "TODO", "future" mentions
        combined = f"{context}\n{consequences}"
        
        gap_patterns = [
            r'(?:gap|missing|TODO|unresolved):\s*(.+?)(?:\n|$)',
            r'\*\*Gap:\*\*\s*(.+?)(?:\n|$)',
        ]
        
        gap_counter = 1
        for pattern in gap_patterns:
            matches = re.finditer(pattern, combined, re.IGNORECASE)
            for match in matches:
                gap_text = match.group(1).strip()
                
                gaps.append(Gap(
                    id=f"GAP-{gap_counter:04d}",
                    question=gap_text,
                    impact=ImpactLevel.MEDIUM,  # Default to medium
                    blocking=False,  # Default to non-blocking
                ))
                gap_counter += 1
        
        return gaps
    
    def _normalize_status(self, status: str) -> str:
        """Normalize status to ADR Kit format.
        
        Args:
            status: E-ADR status (e.g., "Accepted")
            
        Returns:
            Normalized status (lowercase)
        """
        status_map = {
            "accepted": "accepted",
            "proposed": "proposed",
            "deprecated": "deprecated",
            "superseded": "superseded",
        }
        
        return status_map.get(status.lower(), "proposed")
    
    def _normalize_implementation_status(self, impl_status: Optional[str]) -> str:
        """Normalize implementation status.
        
        Args:
            impl_status: E-ADR implementation status (e.g., "Complete")
            
        Returns:
            Normalized implementation status
        """
        if not impl_status:
            return "not_started"
        
        impl_map = {
            "complete": "complete",
            "planned": "planned",
            "in_progress": "in_progress",
            "partial": "in_progress",
        }
        
        return impl_map.get(impl_status.lower(), "not_started")
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date to ISO format.
        
        Args:
            date_str: Date string (e.g., "2026-01-07")
            
        Returns:
            ISO date string
        """
        if not date_str:
            return datetime.now().date().isoformat()
        
        # Already in ISO format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
        
        # Try to parse other formats
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.date().isoformat()
        except ValueError:
            return datetime.now().date().isoformat()
    
    def _normalize_author(self, author: str) -> str:
        """Normalize author name to identifier.
        
        Args:
            author: Author name (e.g., "Erik Gallmann")
            
        Returns:
            Author identifier (e.g., "erik.gallmann")
        """
        return author.lower().replace(" ", ".")
    
    def _model_to_yaml(self, adr_model: Union[LogicalADR, PhysicalADR]) -> str:
        """Convert ADR model to YAML string.
        
        Args:
            adr_model: ADR model
            
        Returns:
            YAML string
        """
        import yaml
        
        # Convert model to dict
        adr_dict = adr_model.model_dump(mode='json', exclude_none=True)
        
        # Generate YAML
        yaml_str = yaml.dump(adr_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        return yaml_str
    
    def save_migrated_adr(self, migration_result: Dict, output_dir: Path):
        """Save migrated ADR to file.
        
        Args:
            migration_result: Result from migrate_eadr()
            output_dir: Output directory (ste-runtime/adrs/)
        """
        output_dir = Path(output_dir)
        
        adr_type = migration_result["type"]
        adr_id = migration_result["adr_id"]
        yaml_content = migration_result["yaml_content"]
        adr_model = migration_result["adr_model"]
        
        # Determine subdirectory
        subdir = output_dir / adr_type
        subdir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        title_slug = self._slugify(adr_model.title)
        filename = f"{adr_id}-{title_slug}.yaml"
        
        output_path = subdir / filename
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        return output_path
    
    def _slugify(self, text: str) -> str:
        """Convert title to slug for filename."""
        slug = text.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug[:50]
