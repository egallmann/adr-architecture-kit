# ste-runtime semantic-linkage handoff

ADR-Kit 0.5.0 provides the validation and query seam for the next independent
ste-runtime extraction slice. Runtime is not an implementation dependency of this
release.

## Producer contract

- Prefer evidence-attribution v1.6; retain v1.5 compatibility where promised.
- Emit only `implements`, `enforces`, and `embodies`.
- Emit decorator claims as `confidence: declared`.
- Non-declared `enforces` is invalid in v1.6.
- Preserve extractor-owned `implementation_entity_id` and the existing eleven
  implementation entity types.
- Preserve `source_file`, `extractor`, optional `commit`, and when known an opaque
  `source_pointer` plus 1-based inclusive line span.
- Sort deterministically by implementation ID, relationship order, target UUID, source
  file, pointer, span, extractor, and commit.
- Write evidence to workspace-owned state and pass its path explicitly. ADR-Kit does not
  search `.ste-workspace`.

Current runtime main emits the older evidence form and recognizes legacy syntax. Its
follow-on must add canonical Python/TypeScript decorator extraction and v1.6 provenance
without loading ADR-Kit repository state while extracting.

## Consumer seam

Use only:

```python
from adr_kit.api import EmbodimentLinkageRequest, build_embodiment_linkage

result = build_embodiment_linkage(
    EmbodimentLinkageRequest(project_root=repo_root, evidence_path=evidence_path)
)
```

The operation returns valid/warning links and rejected claims together. Errors in
individual claims produce a partial result with `success=False`; failures that prevent
the document or repository from being processed raise an SDK operation error.

## Prohibitions

Runtime must not infer target UUIDs or target types, strengthen confidence, mint
architecture or graph identities, load repository authority during extraction, write
Architecture IR relationships, treat declarations as proof, or graph-admit the derived
projection.

