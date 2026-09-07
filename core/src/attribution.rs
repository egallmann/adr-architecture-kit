use std::collections::BTreeMap;

use super::{diagnostic, simple_result, string, Json};

// The shim is a source projection, not an execution environment. The host
// supplies the ordered vocabulary entries loaded from the canonical schema;
// this module owns the byte-sensitive rendering so Python and Node cannot
// drift by maintaining separate templates. No filesystem, repository, or
// architecture state is consulted here.
pub fn execute(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return failure(
            "",
            "attribution_shim.invalid_request",
            "request must be an object",
        );
    };
    if root.get("core_contract_version").and_then(Json::as_str) != Some("1.0") {
        return failure(
            "",
            "attribution_shim.invalid_request",
            "unsupported core_contract_version; expected 1.0",
        );
    }
    if root.get("operation").and_then(Json::as_str) != Some("generate_attribution_shim") {
        return failure(
            "",
            "attribution_shim.invalid_request",
            "unsupported semantic core operation",
        );
    }
    let language = root.get("language").and_then(Json::as_str).unwrap_or("");
    let Some(vocabulary) = root.get("vocabulary").and_then(Json::as_object) else {
        return failure(
            language,
            "attribution_shim.invalid_request",
            "vocabulary is required",
        );
    };
    let rendered = match language {
        "python" => render_python(vocabulary),
        "typescript" => render_typescript(vocabulary),
        _ => Err(format!(
            "Unsupported shim language: {language:?} (supported: python, typescript)"
        )),
    };
    match rendered {
        Ok(content) => {
            let mut result = simple_result("generate_attribution_shim", true, Vec::new());
            if let Json::Object(values) = &mut result {
                values.insert("language".into(), string(language));
                values.insert("content".into(), string(content));
            }
            result
        }
        Err(message) => failure(language, "attribution_shim.invalid_request", &message),
    }
}

fn failure(language: &str, code: &str, message: &str) -> Json {
    let mut result = simple_result(
        "generate_attribution_shim",
        false,
        vec![diagnostic(code, message, None)],
    );
    if let Json::Object(values) = &mut result {
        values.insert("language".into(), string(language));
        values.insert("content".into(), string(""));
    }
    result
}

fn string_field<'a>(object: &'a BTreeMap<String, Json>, key: &str) -> Result<&'a str, String> {
    object
        .get(key)
        .and_then(Json::as_str)
        .ok_or_else(|| format!("vocabulary entry is missing string field {key:?}"))
}

fn bool_field(object: &BTreeMap<String, Json>, key: &str) -> Result<bool, String> {
    match object.get(key) {
        Some(Json::Bool(value)) => Ok(*value),
        _ => Err(format!("vocabulary entry is missing boolean field {key:?}")),
    }
}

fn entries<'a>(vocabulary: &'a BTreeMap<String, Json>, key: &str) -> Result<&'a Vec<Json>, String> {
    vocabulary
        .get(key)
        .and_then(Json::as_array)
        .ok_or_else(|| format!("vocabulary is missing ordered {key:?}"))
}

fn python_literal(value: &str) -> String {
    // The canonical vocabulary currently contains simple identifiers, but
    // escaping here keeps the projection well-formed if a future vocabulary
    // adds a quote, slash, or control character.
    let mut literal = String::from("'");
    for character in value.chars() {
        match character {
            '\\' => literal.push_str("\\\\"),
            '\'' => literal.push_str("\\'"),
            '\n' => literal.push_str("\\n"),
            '\r' => literal.push_str("\\r"),
            '\t' => literal.push_str("\\t"),
            character => literal.push(character),
        }
    }
    literal.push('\'');
    literal
}

fn python_double_literal(value: &str) -> String {
    let mut literal = String::from("\"");
    for character in value.chars() {
        match character {
            '\\' => literal.push_str("\\\\"),
            '"' => literal.push_str("\\\""),
            '\n' => literal.push_str("\\n"),
            '\r' => literal.push_str("\\r"),
            '\t' => literal.push_str("\\t"),
            character => literal.push(character),
        }
    }
    literal.push('"');
    literal
}

fn render_python(vocabulary: &BTreeMap<String, Json>) -> Result<String, String> {
    let claims_attr = string_field(vocabulary, "canonical_claims_attribute")?;
    let legacy = entries(vocabulary, "legacy_decorators")?;
    let relationships = entries(vocabulary, "relationships")?;
    let mut legacy_blocks = Vec::new();
    for entry in legacy {
        let item = entry
            .as_object()
            .ok_or_else(|| "legacy decorator must be an object".to_string())?;
        let name = string_field(item, "name")?;
        let attribute = string_field(item, "attribute")?;
        let label = string_field(item, "label")?;
        let variadic = bool_field(item, "variadic")?;
        let (signature, normalize, type_error) = if variadic {
            (
                format!("def {name}(*ids: str) -> Callable[[Decorated], Decorated]:"),
                format!("_normalize_ids(ids, label={})", python_literal(label)),
                String::new(),
            )
        } else {
            (
                format!("def {name}(ids: Sequence[str]) -> Callable[[Decorated], Decorated]:"),
                format!("_normalize_ids(tuple(ids), label={})", python_literal(label)),
                format!(
                    "    if isinstance(ids, str):\n        raise TypeError(\"{name} expects a sequence of strings, not a single str\")\n"
                ),
            )
        };
        legacy_blocks.push(format!(
            "{signature}\n    \"\"\"Attach legacy {label} attribution metadata.\"\"\"\n\n{type_error}    normalized = {normalize}\n\n    def decorator(target: Decorated) -> Decorated:\n        setattr(target, {}, normalized)\n        return target\n\n    return decorator\n",
            python_literal(attribute)
        ));
    }

    let mut uuid_blocks = Vec::new();
    let mut relationship_order = Vec::new();
    for (index, entry) in relationships.iter().enumerate() {
        let item = entry
            .as_object()
            .ok_or_else(|| "relationship must be an object".to_string())?;
        let relationship = string_field(item, "name")?;
        let uuid_decorator = string_field(item, "uuid_decorator")?;
        let uuid_sequence_decorator = string_field(item, "uuid_sequence_decorator")?;
        relationship_order.push(format!(
            "{}: {}",
            python_double_literal(relationship),
            index
        ));
        uuid_blocks.push(format!(
            "def {uuid_decorator}(*target_entity_ids: str) -> Callable[[Decorated], Decorated]:\n    \"\"\"Attach UUID {relationship} claims with confidence declared.\"\"\"\n\n    return _uuid_claim_decorator({relationship_literal}, target_entity_ids)\n",
            relationship_literal = python_literal(relationship)
        ));
        uuid_blocks.push(format!(
            "def {uuid_sequence_decorator}(target_entity_ids: Sequence[str]) -> Callable[[Decorated], Decorated]:\n    \"\"\"Attach UUID {relationship} claims with confidence declared.\"\"\"\n\n    if isinstance(target_entity_ids, str):\n        raise TypeError(\"{uuid_sequence_decorator} expects a sequence of strings, not a single str\")\n    return _uuid_claim_decorator({relationship_literal}, tuple(target_entity_ids))\n",
            relationship_literal = python_literal(relationship)
        ));
    }

    let mut output = format!(
        "\"\"\"No-op architecture intent decorators for implementation attribution.\n\nGenerated by `adr attribution generate-shim --lang python`. Aligns with\n``adr_kit.decorators`` semantics for RECON extraction.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport re\nfrom collections.abc import Callable, Sequence\nfrom typing import TypeVar\n\nDecorated = TypeVar(\"Decorated\")\n\nUUIDV7_PATTERN = re.compile('^[0-9a-f]{{8}}-[0-9a-f]{{4}}-7[0-9a-f]{{3}}-[89ab][0-9a-f]{{3}}-[0-9a-f]{{12}}$')\nCANONICAL_CLAIMS_ATTR = {}\nRELATIONSHIP_ORDER = {{{}}}\n\n\n{}\n{}\ndef _uuid_claim_decorator(\n",
        python_literal(claims_attr),
        relationship_order.join(", "),
        legacy_blocks.join("\n"),
        uuid_blocks.join("\n")
    );
    output.push_str(
        "    relationship: str,\n    target_entity_ids: tuple[str, ...],\n) -> Callable[[Decorated], Decorated]:\n    normalized = _normalize_uuids(target_entity_ids, label=relationship)\n\n    def decorator(target: Decorated) -> Decorated:\n        existing = getattr(target, CANONICAL_CLAIMS_ATTR, ())\n        composed = list(existing) if isinstance(existing, (list, tuple)) else []\n        existing_pairs = {\n            (claim.get(\"relationship\"), claim.get(\"target_entity_id\"))\n            for claim in composed\n            if isinstance(claim, dict)\n        }\n        incoming_pairs = {(relationship, value) for value in normalized}\n        duplicates = sorted(existing_pairs & incoming_pairs)\n        if duplicates:\n            duplicate_relationship, duplicate_target = duplicates[0]\n            raise ValueError(\n                \"duplicate architecture attribution claim: \"\n                f\"({duplicate_relationship}, {duplicate_target})\"\n            )\n        for target_entity_id in normalized:\n            composed.append(\n                {\n                    \"relationship\": relationship,\n                    \"target_entity_id\": target_entity_id,\n                    \"confidence\": \"declared\",\n                }\n            )\n        composed.sort(\n            key=lambda claim: (\n                RELATIONSHIP_ORDER.get(str(claim.get(\"relationship\")), 99),\n                str(claim.get(\"target_entity_id\", \"\")),\n            )\n        )\n        setattr(target, CANONICAL_CLAIMS_ATTR, tuple(composed))\n        return target\n\n    return decorator\n\n\ndef _normalize_uuids(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:\n    if not values:\n        raise ValueError(f\"{label} decorator requires at least one identifier\")\n    normalized: list[str] = []\n    seen: set[str] = set()\n    for value in values:\n        if not isinstance(value, str):\n            raise TypeError(f\"{label} decorator identifiers must be strings\")\n        item = value.strip()\n        if not item:\n            raise ValueError(f\"{label} decorator identifiers must not be empty\")\n        if not UUIDV7_PATTERN.match(item):\n            raise ValueError(f\"Not a valid lowercase UUIDv7: {item!r}\")\n        if item in seen:\n            raise ValueError(f\"{label} decorator identifiers must be unique after normalization\")\n        seen.add(item)\n        normalized.append(item)\n    return tuple(normalized)\n\n\ndef _normalize_ids(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:\n    if not values:\n        raise ValueError(f\"{label} decorator requires at least one identifier\")\n\n    normalized: list[str] = []\n    seen: set[str] = set()\n    for value in values:\n        if not isinstance(value, str):\n            raise TypeError(f\"{label} decorator identifiers must be strings\")\n        item = value.strip()\n        if not item:\n            raise ValueError(f\"{label} decorator identifiers must not be empty\")\n        if item in seen:\n            raise ValueError(f\"{label} decorator identifiers must be unique after normalization\")\n        seen.add(item)\n        normalized.append(item)\n\n    return tuple(normalized)\n"
    );
    Ok(output)
}

fn render_typescript(vocabulary: &BTreeMap<String, Json>) -> Result<String, String> {
    let legacy = entries(vocabulary, "legacy_decorators")?;
    let relationships = entries(vocabulary, "relationships")?;
    let mut lines: Vec<String> = vec![
        "/**".into(),
        " * No-op decorator factories for compile-time traceability. RECON extracts".into(),
        " * `implements_*` / `enforces_*` / UUID claim arguments from the AST; runtime".into(),
        " * behavior is unchanged.".into(),
        " *".into(),
        " * Generated by `adr attribution generate-shim --lang typescript`.".into(),
        " */".into(),
        "".into(),
    ];
    for entry in legacy {
        let item = entry
            .as_object()
            .ok_or_else(|| "legacy decorator must be an object".to_string())?;
        let name = string_field(item, "name")?;
        let label = string_field(item, "label")?;
        let variadic = bool_field(item, "variadic")?;
        let parameter = if variadic {
            format!("..._{label}Ids: string[]")
        } else {
            format!("_{label}Ids: string[]")
        };
        lines.push(format!(
            "export function {name}({parameter}): MethodDecorator & ClassDecorator {{"
        ));
        lines.push("  return (): void => {};".into());
        lines.push("}".into());
        lines.push("".into());
    }
    for entry in relationships {
        let item = entry
            .as_object()
            .ok_or_else(|| "relationship must be an object".to_string())?;
        let uuid_decorator = string_field(item, "uuid_decorator")?;
        let uuid_sequence_decorator = string_field(item, "uuid_sequence_decorator")?;
        lines.push(format!(
            "export function {uuid_decorator}(..._targetEntityIds: string[]): MethodDecorator & ClassDecorator {{"
        ));
        lines.push("  return (): void => {};".into());
        lines.push("}".into());
        lines.push("".into());
        lines.push(format!(
            "export function {uuid_sequence_decorator}(_targetEntityIds: string[]): MethodDecorator & ClassDecorator {{"
        ));
        lines.push("  return (): void => {};".into());
        lines.push("}".into());
        lines.push("".into());
    }
    Ok(lines.join("\n").trim_end().to_string() + "\n")
}
