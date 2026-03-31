# Graph Integration Guide

## Overview

ADR Kit integrates with **ste-runtime** to extract ADRs into a semantic graph during the RECON (Reconciliation) process. This enables AI systems to reason over architecture through graph queries.

## Architecture

```
ADR YAML Files (authoritative)
    ↓ parsed by
ste-runtime RECON (Phase 2: Extraction)
    ↓ generates
Semantic Graph (nodes + edges)
    ↓ queryable via
MCP Interface (graph queries)
```

## Separation of Concerns

**ADR Kit responsibilities:**
- Define ADR YAML structure (JSON Schema)
- Validate schema compliance
- Generate human views (YAML → Markdown)
- Generate manifest (derived discovery index)

**ste-runtime responsibilities:**
- Discover `adrs/` directory during RECON
- Parse ADR YAML files
- Extract graph nodes and edges
- Build semantic graph (ADRs + code + infra)
- Expose graph via MCP for queries

## Graph Extraction Contract

ADR Kit provides structured YAML that ste-runtime can parse:

### Graph Nodes

**From ADR artifacts:**
- `LogicalADR` (from `ADR-L-XXXX.yaml`)
- `PhysicalADR` (from `ADR-P-XXXX.yaml`)
- `Invariant` (from `INV-XXXX.yaml` or embedded)
- `Capability` (from logical ADR body)
- `Component` (from physical ADR body)
- `Interface` (from component specs)
- `Decision` (from ADR body)

### Graph Edges

**From relationship fields:**
- `implements_logical` → Physical implements Logical
- `related_adrs` → ADR relates to ADR
- `enforced_by` → Invariant enforced by Physical ADR
- `dependencies` → Component depends on Component
- `supersedes` → ADR supersedes ADR
- `owned_by` → Component owned by Team

### Example: ADR Graph Structure

```yaml
# Source: ADR-L-0001.yaml
id: ADR-L-0001
adr_type: logical
domains: [architecture]

capabilities:
  - id: CAP-0001  # → Graph node

invariants:
  - id: INV-0001  # → Graph node

# Graph edges
related_adrs: [ADR-L-0002]  # → Edge: ADR-L-0001 --relates_to--> ADR-L-0002
```

**ste-runtime extracts:**

```
Nodes:
- LogicalADR(id="adr-l-0001", type="logical-adr", domain="architecture")
- Capability(id="cap-0001", type="capability", domain="architecture")
- Invariant(id="inv-0001", type="invariant", domain="architecture")

Edges:
- (adr-l-0001) --defines--> (cap-0001)
- (adr-l-0001) --defines--> (inv-0001)
- (adr-l-0001) --relates_to--> (adr-l-0002)
```

## RECON Integration

### Phase 1: Discovery

ste-runtime RECON discovers `adrs/` directory:

```
workspace/
  adrs/
    logical/
      ADR-L-0001.yaml  ← Discovered
      ADR-L-0002.yaml  ← Discovered
    physical/
      ADR-P-0001.yaml  ← Discovered
```

### Phase 2: Extraction

ADR parser (in ste-runtime) extracts:

```python
# Conceptual extraction logic
def extract_adr(adr_file: Path) -> List[GraphNode]:
    adr_data = yaml.safe_load(adr_file.read_text())
    
    nodes = []
    
    # Main ADR node
    adr_node = GraphNode(
        id=adr_data['id'],
        type='logical-adr' if adr_data['adr_type'] == 'logical' else 'physical-adr',
        domain='architecture',
        properties=adr_data,
    )
    nodes.append(adr_node)
    
    # Entity nodes (capabilities, components, invariants)
    for cap in adr_data.get('capabilities', []):
        nodes.append(GraphNode(id=cap['id'], type='capability', ...))
    
    return nodes
```

### Phase 3-5: Normalization, Population, Divergence

ADR nodes integrated with code and infrastructure nodes in unified graph.

### Phase 6: Graph Queries

Query architecture via MCP:

```python
# Example queries (via ste-runtime MCP)
"Show all logical ADRs in the API domain"
"What physical ADRs implement ADR-L-0001?"
"Which components are owned by team-api?"
"Show enforcement chain for INV-0001"
"What is the blast radius for changing ADR-L-0042?"
```

## Iterative Co-Design Workflow

ADR Kit and ste-runtime evolve together:

**Week 1:**
1. Design minimal ADR schema
2. Write ADR-L-0001
3. Add ADR parser to ste-runtime RECON
4. Run RECON → discover missing fields
5. Update schema

**Week 2:**
1. Write ADR-P-0001
2. Run RECON → validate physical ADR extraction
3. Query: "What implements ADR-L-0001?"
4. Iterate schema based on query results

**Week 3:**
1. Write invariants
2. Run RECON → validate invariant nodes
3. Query: "Show enforcement chain for INV-0001"
4. Finalize schema v1.0

## Graph-Ready Schema Design

To be RECON-compatible, ADR schema includes:

### 1. Explicit Relationships

```yaml
# Array fields for graph edges
implements_logical: ["ADR-L-0001"]
related_adrs: ["ADR-L-0002", "ADR-L-0003"]
enforced_by: ["ADR-P-0001", "ADR-P-0005"]
```

### 2. Type-Prefixed IDs

```yaml
# Type visible in ID
id: ADR-L-0001  # Logical ADR
id: ADR-P-0001  # Physical ADR
id: INV-0001    # Invariant
id: CAP-0001    # Capability
```

### 3. Rich Metadata

```yaml
# All metadata in frontmatter
domains: [api, infrastructure]
tags: [gateway, authentication]
technologies: [kong, kubernetes]
ownership:
  architecture_authority: "platform-architecture"
```

### 4. Entity IDs

```yaml
# Every entity has unique ID
capabilities:
  - id: CAP-0001  # Graph node

components:
  - id: COMP-0001  # Graph node
    interfaces:
      - id: IFACE-0001  # Graph node
```

## Testing Graph Extraction

### 1. Run RECON

```bash
# In ste-runtime workspace
ste-runtime recon
```

### 2. Query Graph

```bash
# Query via MCP
ste-runtime query "Show all ADRs"
ste-runtime query "What implements ADR-L-0001?"
```

### 3. Validate Structure

```python
# Check graph structure
graph = load_graph()

# Verify ADR nodes exist
assert "adr-l-0001" in graph.nodes
assert "adr-p-0001" in graph.nodes

# Verify edges exist
assert graph.has_edge("adr-p-0001", "adr-l-0001", type="implements")
```

## Future: EDR Comparison

**Embodied Design Record (EDR)** = Observed architecture from running system.

```
Physical ADR (declared) ↔ EDR (observed) → Violations → Patches
```

Physical ADRs will be compared against EDR to detect drift:
- Declared component doesn't exist → `Doc-Missing-Inventory`
- Component exists but different interface → `Doc-State-Staleness`
- Dependency not declared → `Doc-Implicit-State`

## Further Reading

- `ste-runtime/README.md` - RECON architecture
- `ste-spec/architecture/STE-Architecture.md` - STE specification
- `docs/schema-guide.md` - Schema reference
