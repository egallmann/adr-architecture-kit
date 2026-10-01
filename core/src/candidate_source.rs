//! Internal candidate-source authority for ACC's detached source evidence.
//!
//! This module is deliberately not wired into `execute_json`.  It owns the
//! exact authoring-yaml bytes and basis digest used by a later construction
//! operation, while construction, identity, persistence, and interpretation
//! remain outside this slice.

use std::collections::{BTreeMap, BTreeSet};

use sha2::{Digest, Sha256};

use super::{authoring_construction, schema_validation, semantic_contract, Json};

const SERIALIZATION_PROFILE: &str = "adr-kit.authoring-yaml/v1";
const BASIS_DOMAIN: &str = "adr-kit.candidate-source-basis/v1";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CandidateSourceSelector {
    pub(crate) canonical_resource_key: String,
    pub(crate) json_pointer: String,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct CandidateSourceArtifact {
    pub(crate) request_key: String,
    pub(crate) source_ref: String,
    pub(crate) artifact_kind: String,
    pub(crate) source_schema: CandidateSourceSelector,
    pub(crate) serialization_profile: String,
    pub(crate) content_digest: String,
    pub(crate) bytes: Vec<u8>,
    pub(crate) source_contract: Json,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct CandidateSourceBasis {
    pub(crate) artifacts: Vec<CandidateSourceArtifact>,
    pub(crate) basis_digest: String,
}

#[derive(Clone, Debug)]
enum OrderedValue {
    Null,
    Bool(bool),
    Number,
    String(String),
    Array(Vec<OrderedValue>),
    Object(Vec<(String, OrderedValue)>),
}

impl OrderedValue {
    fn object(&self) -> Option<&[(String, OrderedValue)]> {
        match self {
            Self::Object(value) => Some(value),
            _ => None,
        }
    }

    fn get(&self, key: &str) -> Option<&OrderedValue> {
        self.object()?
            .iter()
            .find(|(name, _)| name == key)
            .map(|(_, value)| value)
    }

    fn string(&self) -> Option<&str> {
        match self {
            Self::String(value) => Some(value),
            _ => None,
        }
    }
}

struct OrderedJsonParser<'a> {
    input: &'a [u8],
    offset: usize,
}

impl<'a> OrderedJsonParser<'a> {
    fn parse(input: &'a str) -> Result<OrderedValue, String> {
        let mut parser = Self {
            input: input.as_bytes(),
            offset: 0,
        };
        let value = parser.value()?;
        parser.whitespace();
        if parser.offset != parser.input.len() {
            return Err("ordered schema JSON has trailing bytes".into());
        }
        Ok(value)
    }

    fn whitespace(&mut self) {
        while self
            .input
            .get(self.offset)
            .is_some_and(|byte| matches!(byte, b' ' | b'\n' | b'\r' | b'\t'))
        {
            self.offset += 1;
        }
    }

    fn value(&mut self) -> Result<OrderedValue, String> {
        self.whitespace();
        match self.input.get(self.offset).copied() {
            Some(b'{') => self.object_value(),
            Some(b'[') => self.array_value(),
            Some(b'"') => Ok(OrderedValue::String(self.string_value()?)),
            Some(b't') if self.consume_literal(b"true") => Ok(OrderedValue::Bool(true)),
            Some(b'f') if self.consume_literal(b"false") => Ok(OrderedValue::Bool(false)),
            Some(b'n') if self.consume_literal(b"null") => Ok(OrderedValue::Null),
            Some(byte) if byte == b'-' || byte.is_ascii_digit() => self.number_value(),
            _ => Err(format!(
                "invalid ordered schema JSON at byte {}",
                self.offset
            )),
        }
    }

    fn consume_literal(&mut self, literal: &[u8]) -> bool {
        if self.input.get(self.offset..self.offset + literal.len()) == Some(literal) {
            self.offset += literal.len();
            true
        } else {
            false
        }
    }

    fn object_value(&mut self) -> Result<OrderedValue, String> {
        self.offset += 1;
        self.whitespace();
        let mut entries = Vec::new();
        if self.input.get(self.offset) == Some(&b'}') {
            self.offset += 1;
            return Ok(OrderedValue::Object(entries));
        }
        loop {
            self.whitespace();
            if self.input.get(self.offset) != Some(&b'"') {
                return Err(format!(
                    "ordered schema object key missing at byte {}",
                    self.offset
                ));
            }
            let key = self.string_value()?;
            if entries.iter().any(|(name, _)| name == &key) {
                return Err(format!("duplicate ordered schema object key: {key}"));
            }
            self.whitespace();
            if self.input.get(self.offset) != Some(&b':') {
                return Err(format!(
                    "ordered schema object colon missing at byte {}",
                    self.offset
                ));
            }
            self.offset += 1;
            let value = self.value()?;
            entries.push((key, value));
            self.whitespace();
            match self.input.get(self.offset).copied() {
                Some(b',') => self.offset += 1,
                Some(b'}') => {
                    self.offset += 1;
                    return Ok(OrderedValue::Object(entries));
                }
                _ => {
                    return Err(format!(
                        "ordered schema object separator missing at byte {}",
                        self.offset
                    ))
                }
            }
        }
    }

    fn array_value(&mut self) -> Result<OrderedValue, String> {
        self.offset += 1;
        self.whitespace();
        let mut values = Vec::new();
        if self.input.get(self.offset) == Some(&b']') {
            self.offset += 1;
            return Ok(OrderedValue::Array(values));
        }
        loop {
            values.push(self.value()?);
            self.whitespace();
            match self.input.get(self.offset).copied() {
                Some(b',') => self.offset += 1,
                Some(b']') => {
                    self.offset += 1;
                    return Ok(OrderedValue::Array(values));
                }
                _ => {
                    return Err(format!(
                        "ordered schema array separator missing at byte {}",
                        self.offset
                    ))
                }
            }
        }
    }

    fn string_value(&mut self) -> Result<String, String> {
        let start = self.offset;
        self.offset += 1;
        while let Some(byte) = self.input.get(self.offset).copied() {
            match byte {
                b'"' => {
                    self.offset += 1;
                    let raw = std::str::from_utf8(&self.input[start..self.offset])
                        .map_err(|error| format!("ordered schema string is not UTF-8: {error}"))?;
                    return serde_json::from_str(raw)
                        .map_err(|error| format!("ordered schema string is invalid: {error}"));
                }
                b'\\' => {
                    self.offset += 1;
                    if self.input.get(self.offset) == Some(&b'u') {
                        self.offset += 4;
                    }
                }
                byte if byte < 0x20 => {
                    return Err("ordered schema string contains a control byte".into())
                }
                _ => self.offset += 1,
            }
        }
        Err("ordered schema string is unterminated".into())
    }

    fn number_value(&mut self) -> Result<OrderedValue, String> {
        let start = self.offset;
        while self.input.get(self.offset).is_some_and(|byte| {
            byte.is_ascii_digit() || matches!(byte, b'-' | b'+' | b'.' | b'e' | b'E')
        }) {
            self.offset += 1;
        }
        let raw = std::str::from_utf8(&self.input[start..self.offset])
            .map_err(|error| format!("ordered schema number is not UTF-8: {error}"))?;
        if raw.parse::<f64>().is_err() {
            return Err(format!("ordered schema number is invalid: {raw}"));
        }
        Ok(OrderedValue::Number)
    }
}

struct SchemaCatalog {
    resources: BTreeMap<&'static str, OrderedValue>,
}

impl SchemaCatalog {
    fn load() -> Result<Self, String> {
        let resources = [
            (
                "authoring/1.7/schema/adr-common.schema",
                authoring_construction::AUTHORING_COMMON_SCHEMA,
            ),
            (
                "authoring/1.7/schema/adr-logical.schema",
                authoring_construction::AUTHORING_LOGICAL_SCHEMA,
            ),
            (
                "authoring/1.7/schema/adr-physical-base.schema",
                authoring_construction::AUTHORING_PHYSICAL_BASE_SCHEMA,
            ),
            (
                "authoring/1.7/schema/adr-physical-component.schema",
                authoring_construction::AUTHORING_PHYSICAL_COMPONENT_SCHEMA,
            ),
            (
                "authoring/1.7/schema/adr-physical-system.schema",
                authoring_construction::AUTHORING_PHYSICAL_SYSTEM_SCHEMA,
            ),
            (
                "authoring/1.7/schema/types.schema",
                authoring_construction::AUTHORING_TYPES_SCHEMA,
            ),
        ]
        .into_iter()
        .map(|(key, source)| OrderedJsonParser::parse(source).map(|value| (key, value)))
        .collect::<Result<BTreeMap<_, _>, _>>()?;
        Ok(Self { resources })
    }

    fn root(&self, key: &str) -> Result<ResolvedSchema<'_>, String> {
        let (resource_key, value) = self
            .resources
            .get_key_value(key)
            .ok_or_else(|| format!("unknown authoring schema resource: {key}"))?;
        Ok(ResolvedSchema {
            resource_key,
            value,
        })
    }

    fn select(&self, selector: &CandidateSourceSelector) -> Result<ResolvedSchema<'_>, String> {
        let root = self.root(&selector.canonical_resource_key)?;
        self.pointer(root, &selector.json_pointer)
    }

    fn pointer<'a>(
        &'a self,
        root: ResolvedSchema<'a>,
        pointer: &str,
    ) -> Result<ResolvedSchema<'a>, String> {
        if pointer.is_empty() {
            return Ok(root);
        }
        if !pointer.starts_with('/') {
            return Err(format!("invalid authoring schema JSON pointer: {pointer}"));
        }
        let mut value = root.value;
        for raw_segment in pointer[1..].split('/') {
            let mut bytes = raw_segment.as_bytes().iter();
            while let Some(byte) = bytes.next() {
                if *byte == b'~' && !matches!(bytes.next(), Some(b'0' | b'1')) {
                    return Err(format!(
                        "invalid authoring schema JSON pointer escape: {raw_segment}"
                    ));
                }
            }
            let segment = raw_segment.replace("~1", "/").replace("~0", "~");
            value = match value {
                OrderedValue::Object(entries) => entries
                    .iter()
                    .find(|(key, _)| key == &segment)
                    .map(|(_, value)| value)
                    .ok_or_else(|| format!("schema pointer segment not found: {segment}"))?,
                OrderedValue::Array(values) => segment
                    .parse::<usize>()
                    .ok()
                    .and_then(|index| values.get(index))
                    .ok_or_else(|| format!("schema pointer array segment not found: {segment}"))?,
                _ => return Err(format!("schema pointer traverses a scalar: {segment}")),
            };
        }
        Ok(ResolvedSchema {
            resource_key: root.resource_key,
            value,
        })
    }

    fn dereference<'a>(&'a self, schema: ResolvedSchema<'a>) -> Result<ResolvedSchema<'a>, String> {
        let mut current = schema;
        for _ in 0..32 {
            let Some(reference) = current.value.get("$ref").and_then(OrderedValue::string) else {
                return Ok(current);
            };
            current = self.reference(current.resource_key, reference)?;
        }
        Err("authoring schema reference depth exceeded".into())
    }

    fn reference<'a>(
        &'a self,
        current_resource: &str,
        reference: &str,
    ) -> Result<ResolvedSchema<'a>, String> {
        let (resource, pointer) = reference
            .split_once('#')
            .map_or((reference, ""), |(resource, pointer)| (resource, pointer));
        let resource_key = if resource.is_empty() {
            current_resource.to_owned()
        } else if resource.ends_with(".json") {
            format!(
                "authoring/1.7/schema/{}",
                resource.trim_end_matches(".json")
            )
        } else {
            resource.to_owned()
        };
        let root = self.root(&resource_key)?;
        self.pointer(root, pointer)
    }

    fn choose<'a>(
        &'a self,
        schema: ResolvedSchema<'a>,
        value: &Json,
    ) -> Result<ResolvedSchema<'a>, String> {
        let schema = self.dereference(schema)?;
        // Null has one unambiguous scalar spelling in the profile. Schema
        // validation remains the caller's separate authority; the renderer
        // only needs to resolve ordering and nested traversal here.
        if matches!(value, Json::Null) {
            return Ok(schema);
        }
        for keyword in ["oneOf", "anyOf"] {
            if let Some(OrderedValue::Array(variants)) = schema.value.get(keyword) {
                let matches = variants
                    .iter()
                    .map(|variant| ResolvedSchema {
                        resource_key: schema.resource_key,
                        value: variant,
                    })
                    .filter(|variant| self.accepts(*variant, value))
                    .collect::<Vec<_>>();
                if matches.len() != 1 {
                    return Err(format!(
                        "authoring schema {keyword} is unresolved or ambiguous for the value"
                    ));
                }
                return self.choose(matches[0], value);
            }
        }
        Ok(schema)
    }

    fn accepts(&self, schema: ResolvedSchema<'_>, value: &Json) -> bool {
        let Ok(schema) = self.dereference(schema) else {
            return false;
        };
        if let Some(OrderedValue::Array(types)) = schema.value.get("type") {
            return types.iter().any(|kind| {
                kind.string()
                    .is_some_and(|kind| self.type_matches(kind, value))
            });
        }
        if let Some(kind) = schema.value.get("type").and_then(OrderedValue::string) {
            return self.type_matches(kind, value);
        }
        if schema.value.get("oneOf").is_some() || schema.value.get("anyOf").is_some() {
            return self.choose(schema, value).is_ok();
        }
        true
    }

    fn type_matches(&self, kind: &str, value: &Json) -> bool {
        match kind {
            "null" => matches!(value, Json::Null),
            "boolean" => matches!(value, Json::Bool(_)),
            "string" => matches!(value, Json::String(_)),
            "integer" | "number" => matches!(value, Json::Number(_)),
            "object" => matches!(value, Json::Object(_)),
            "array" => matches!(value, Json::Array(_)),
            _ => false,
        }
    }

    fn layout<'a>(
        &'a self,
        schema: ResolvedSchema<'a>,
    ) -> Result<(Vec<Field<'a>>, Additional<'a>), String> {
        let schema = self.dereference(schema)?;
        let mut fields = Vec::new();
        let mut additional = Additional::Closed;
        self.collect_layout(schema, &mut fields, &mut additional)?;
        Ok((fields, additional))
    }

    fn collect_layout<'a>(
        &'a self,
        schema: ResolvedSchema<'a>,
        fields: &mut Vec<Field<'a>>,
        additional: &mut Additional<'a>,
    ) -> Result<(), String> {
        let schema = self.dereference(schema)?;
        if let Some(OrderedValue::Object(properties)) = schema.value.get("properties") {
            for (name, value) in properties {
                if fields.iter().any(|field: &Field<'_>| field.name == *name) {
                    continue;
                }
                fields.push(Field {
                    name: name.clone(),
                    schema: ResolvedSchema {
                        resource_key: schema.resource_key,
                        value,
                    },
                });
            }
        }
        if let Some(value) = schema.value.get("additionalProperties") {
            *additional = match value {
                OrderedValue::Bool(true) => Additional::Any,
                OrderedValue::Bool(false) => Additional::Closed,
                OrderedValue::Object(_) => Additional::Schema(ResolvedSchema {
                    resource_key: schema.resource_key,
                    value,
                }),
                _ => return Err("authoring schema additionalProperties is invalid".into()),
            };
        }
        if let Some(OrderedValue::Array(all_of)) = schema.value.get("allOf") {
            for value in all_of {
                self.collect_layout(
                    ResolvedSchema {
                        resource_key: schema.resource_key,
                        value,
                    },
                    fields,
                    additional,
                )?;
            }
        }
        Ok(())
    }

    fn items<'a>(&'a self, schema: ResolvedSchema<'a>) -> Result<ResolvedSchema<'a>, String> {
        let schema = self.dereference(schema)?;
        schema
            .value
            .get("items")
            .map(|value| ResolvedSchema {
                resource_key: schema.resource_key,
                value,
            })
            .ok_or_else(|| "authoring array schema has no items schema".into())
    }
}

#[derive(Clone, Copy)]
struct ResolvedSchema<'a> {
    resource_key: &'a str,
    value: &'a OrderedValue,
}

struct Field<'a> {
    name: String,
    schema: ResolvedSchema<'a>,
}

enum Additional<'a> {
    Closed,
    Any,
    Schema(ResolvedSchema<'a>),
}

pub(crate) fn render_source(
    selector: &CandidateSourceSelector,
    source: &Json,
) -> Result<Vec<u8>, String> {
    let catalog = SchemaCatalog::load()?;
    let schema = catalog.select(selector)?;
    let mut output = String::new();
    render_node(&catalog, source, Some(schema), 0, &mut output)?;
    output.push('\n');
    Ok(output.into_bytes())
}

fn render_node(
    catalog: &SchemaCatalog,
    value: &Json,
    schema: Option<ResolvedSchema<'_>>,
    indent: usize,
    output: &mut String,
) -> Result<(), String> {
    let schema = schema
        .map(|schema| catalog.choose(schema, value))
        .transpose()?;
    match value {
        Json::Null | Json::Bool(_) | Json::Number(_) | Json::String(_) => {
            render_scalar(value, output)
        }
        Json::Object(values) => render_object(catalog, values, schema, indent, output),
        Json::Array(values) => render_array(catalog, values, schema, indent, output),
    }
}

fn render_scalar(value: &Json, output: &mut String) -> Result<(), String> {
    match value {
        Json::Null => output.push_str("null"),
        Json::Bool(value) => output.push_str(if *value { "true" } else { "false" }),
        Json::Number(value) => output.push_str(&semantic_contract::canonical_number(value)?),
        Json::String(value) => output.push_str(&semantic_contract::canonical_string(value)),
        Json::Object(_) | Json::Array(_) => return Err("value is not a scalar".into()),
    }
    Ok(())
}

fn render_object(
    catalog: &SchemaCatalog,
    values: &BTreeMap<String, Json>,
    schema: Option<ResolvedSchema<'_>>,
    indent: usize,
    output: &mut String,
) -> Result<(), String> {
    if values.is_empty() {
        output.push_str("{}");
        return Ok(());
    }
    let schema = schema.ok_or_else(|| "object has no governing authoring schema".to_owned())?;
    let (fields, additional) = catalog.layout(schema)?;
    let mut entries: Vec<(String, &Json, Option<ResolvedSchema<'_>>)> = Vec::new();
    let mut known = BTreeSet::new();
    for field in fields {
        if let Some(value) = values.get(&field.name) {
            known.insert(field.name.clone());
            entries.push((field.name, value, Some(field.schema)));
        }
    }
    for (name, value) in values {
        if known.contains(name) {
            continue;
        }
        let child_schema = match &additional {
            Additional::Closed => {
                return Err(format!(
                    "unknown property is not authorized by the closed schema: {name}"
                ))
            }
            Additional::Any => None,
            Additional::Schema(schema) => Some(*schema),
        };
        entries.push((name.clone(), value, child_schema));
    }
    if entries.is_empty() {
        output.push_str("{}");
        return Ok(());
    }
    for (index, (name, value, child_schema)) in entries.into_iter().enumerate() {
        if index != 0 {
            output.push('\n');
        }
        write_indent(output, indent);
        output.push_str(&semantic_contract::canonical_string(&name));
        if is_inline(value) {
            output.push_str(": ");
            render_node(catalog, value, child_schema, indent, output)?;
        } else {
            output.push_str(":\n");
            render_node(catalog, value, child_schema, indent + 2, output)?;
        }
    }
    Ok(())
}

fn render_array(
    catalog: &SchemaCatalog,
    values: &[Json],
    schema: Option<ResolvedSchema<'_>>,
    indent: usize,
    output: &mut String,
) -> Result<(), String> {
    if values.is_empty() {
        output.push_str("[]");
        return Ok(());
    }
    let schema = schema.ok_or_else(|| "array has no governing authoring schema".to_owned())?;
    let item_schema = catalog.items(schema)?;
    for (index, value) in values.iter().enumerate() {
        if index != 0 {
            output.push('\n');
        }
        write_indent(output, indent);
        if is_inline(value) {
            output.push_str("- ");
            render_node(catalog, value, Some(item_schema), indent, output)?;
        } else {
            output.push_str("-");
            output.push('\n');
            render_node(catalog, value, Some(item_schema), indent + 2, output)?;
        }
    }
    Ok(())
}

fn is_scalar(value: &Json) -> bool {
    matches!(
        value,
        Json::Null | Json::Bool(_) | Json::Number(_) | Json::String(_)
    )
}

fn is_inline(value: &Json) -> bool {
    is_scalar(value)
        || matches!(value, Json::Object(values) if values.is_empty())
        || matches!(value, Json::Array(values) if values.is_empty())
}

fn write_indent(output: &mut String, indent: usize) {
    output.extend(std::iter::repeat(' ').take(indent));
}

fn sha256_digest(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let digest = hasher.finalize();
    format!(
        "sha256:{}",
        digest
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    )
}

pub(crate) fn seal_candidate_artifact(
    request_key: &str,
    source_ref: &str,
    artifact_kind: &str,
    source_schema: CandidateSourceSelector,
    source_contract: Json,
    source: &Json,
) -> Result<CandidateSourceArtifact, String> {
    if request_key.is_empty() || source_ref.is_empty() {
        return Err("candidate request_key and source_ref must be non-empty".into());
    }
    if !matches!(artifact_kind, "authoring_fragment" | "authoring_document") {
        return Err(format!(
            "unsupported candidate artifact kind: {artifact_kind}"
        ));
    }
    let bytes = render_source(&source_schema, source)?;
    let content_digest = sha256_digest(&bytes);
    Ok(CandidateSourceArtifact {
        request_key: request_key.to_owned(),
        source_ref: source_ref.to_owned(),
        artifact_kind: artifact_kind.to_owned(),
        source_schema,
        serialization_profile: SERIALIZATION_PROFILE.to_owned(),
        content_digest,
        bytes,
        source_contract,
    })
}

pub(crate) fn seal_candidate_source_basis(
    mut artifacts: Vec<CandidateSourceArtifact>,
) -> Result<CandidateSourceBasis, String> {
    if artifacts.is_empty() {
        return Err("candidate source basis must contain at least one artifact".into());
    }
    let mut source_refs = BTreeSet::new();
    for artifact in &artifacts {
        if !source_refs.insert(artifact.source_ref.clone()) {
            return Err(format!(
                "duplicate candidate source_ref: {}",
                artifact.source_ref
            ));
        }
        if artifact.serialization_profile != SERIALIZATION_PROFILE {
            return Err("candidate artifact has an unsupported serialization profile".into());
        }
        if artifact.content_digest != sha256_digest(&artifact.bytes) {
            return Err(format!(
                "candidate content_digest does not match exact bytes: {}",
                artifact.source_ref
            ));
        }
    }
    artifacts.sort_by(|left, right| left.source_ref.cmp(&right.source_ref));
    let descriptor = Json::Object(BTreeMap::from([
        ("domain".into(), Json::String(BASIS_DOMAIN.into())),
        (
            "artifacts".into(),
            Json::Array(
                artifacts
                    .iter()
                    .map(|artifact| {
                        Json::Object(BTreeMap::from([
                            (
                                "request_key".into(),
                                Json::String(artifact.request_key.clone()),
                            ),
                            (
                                "source_ref".into(),
                                Json::String(artifact.source_ref.clone()),
                            ),
                            (
                                "artifact_kind".into(),
                                Json::String(artifact.artifact_kind.clone()),
                            ),
                            (
                                "source_schema".into(),
                                Json::Object(BTreeMap::from([
                                    (
                                        "canonical_resource_key".into(),
                                        Json::String(
                                            artifact.source_schema.canonical_resource_key.clone(),
                                        ),
                                    ),
                                    (
                                        "json_pointer".into(),
                                        Json::String(artifact.source_schema.json_pointer.clone()),
                                    ),
                                ])),
                            ),
                            (
                                "serialization_profile".into(),
                                Json::String(artifact.serialization_profile.clone()),
                            ),
                            (
                                "content_digest".into(),
                                Json::String(artifact.content_digest.clone()),
                            ),
                            ("source_contract".into(), artifact.source_contract.clone()),
                        ]))
                    })
                    .collect(),
            ),
        ),
    ]));
    let mut canonical = String::new();
    semantic_contract::canonicalize_value(&descriptor, &mut canonical)?;
    Ok(CandidateSourceBasis {
        artifacts,
        basis_digest: sha256_digest(canonical.as_bytes()),
    })
}

fn authoring_schema_resources() -> Result<BTreeMap<String, Json>, String> {
    [
        (
            "authoring/1.7/schema/adr-common.schema",
            authoring_construction::AUTHORING_COMMON_SCHEMA,
        ),
        (
            "authoring/1.7/schema/adr-logical.schema",
            authoring_construction::AUTHORING_LOGICAL_SCHEMA,
        ),
        (
            "authoring/1.7/schema/adr-physical-base.schema",
            authoring_construction::AUTHORING_PHYSICAL_BASE_SCHEMA,
        ),
        (
            "authoring/1.7/schema/adr-physical-component.schema",
            authoring_construction::AUTHORING_PHYSICAL_COMPONENT_SCHEMA,
        ),
        (
            "authoring/1.7/schema/adr-physical-system.schema",
            authoring_construction::AUTHORING_PHYSICAL_SYSTEM_SCHEMA,
        ),
        (
            "authoring/1.7/schema/types.schema",
            authoring_construction::AUTHORING_TYPES_SCHEMA,
        ),
    ]
    .into_iter()
    .map(|(key, source)| {
        serde_json::from_str::<Json>(source)
            .map(|value| (key.to_owned(), value))
            .map_err(|error| format!("authoring schema {key} is invalid JSON: {error}"))
    })
    .collect()
}

fn validate_selected_authoring_schema(
    selector: &CandidateSourceSelector,
    source: &Json,
) -> Result<(), String> {
    let resources = authoring_schema_resources()?;
    schema_validation::validate_fragment(
        &resources,
        &selector.canonical_resource_key,
        &selector.json_pointer,
        source,
    )
    .map_err(|error| {
        if error.path.is_empty() {
            error.message
        } else {
            format!("{} at {}", error.message, error.path)
        }
    })
}

fn canonical_yaml_key(line: &str) -> Result<(String, &str), String> {
    if !line.starts_with('"') {
        return Err("canonical YAML mapping keys must be JSON-compatible strings".into());
    }
    let bytes = line.as_bytes();
    let mut offset = 1;
    while offset < bytes.len() {
        match bytes[offset] {
            b'\\' => {
                offset += 2;
                if offset > bytes.len() {
                    return Err("canonical YAML mapping key has an incomplete escape".into());
                }
            }
            b'"' => {
                let raw = &line[..=offset];
                let key = serde_json::from_str::<String>(raw)
                    .map_err(|error| format!("canonical YAML mapping key is invalid: {error}"))?;
                if semantic_contract::canonical_string(&key) != raw {
                    return Err("canonical YAML mapping key is not canonically quoted".into());
                }
                let rest = line[offset + 1..]
                    .strip_prefix(':')
                    .ok_or_else(|| "canonical YAML mapping key must be followed by ':'".to_owned())?;
                if rest.starts_with(' ') {
                    if rest.starts_with("  ") {
                        return Err("canonical YAML mapping separator is not canonical".into());
                    }
                    return Ok((key, &rest[1..]));
                }
                if rest.is_empty() {
                    return Ok((key, rest));
                }
                return Err("canonical YAML mapping has trailing bytes".into());
            }
            byte if byte < 0x20 => {
                return Err("canonical YAML mapping key contains a control byte".into())
            }
            _ => offset += 1,
        }
    }
    Err("canonical YAML mapping key is unterminated".into())
}

fn is_canonical_mapping_line(line: &str) -> bool {
    if !line.starts_with('"') {
        return false;
    }
    let bytes = line.as_bytes();
    let mut offset = 1;
    while offset < bytes.len() {
        match bytes[offset] {
            b'\\' => offset += 2,
            b'"' => return bytes.get(offset + 1) == Some(&b':'),
            byte if byte < 0x20 => return false,
            _ => offset += 1,
        }
    }
    false
}

fn canonical_yaml_scalar(raw: &str) -> Result<Json, String> {
    if raw.is_empty() {
        return Err("canonical YAML scalar is empty".into());
    }
    if raw == "{}" {
        return Ok(Json::Object(BTreeMap::new()));
    }
    if raw == "[]" {
        return Ok(Json::Array(Vec::new()));
    }
    let value = serde_json::from_str::<Json>(raw)
        .map_err(|error| format!("canonical YAML scalar is not JSON-compatible: {error}"))?;
    let rendered = match &value {
        Json::String(value) => semantic_contract::canonical_string(value),
        Json::Bool(true) => "true".to_owned(),
        Json::Bool(false) => "false".to_owned(),
        Json::Null => "null".to_owned(),
        Json::Number(value) => semantic_contract::canonical_number(value)?,
        Json::Object(_) | Json::Array(_) => {
            return Err("non-empty YAML flow values are not in the canonical profile".into())
        }
    };
    if rendered != raw {
        return Err("canonical YAML scalar spelling is not canonical".into());
    }
    Ok(value)
}

struct CanonicalYaml<'a> {
    lines: Vec<&'a str>,
    position: usize,
}

impl<'a> CanonicalYaml<'a> {
    fn decode(bytes: &'a [u8]) -> Result<Json, String> {
        if bytes.starts_with(&[0xef, 0xbb, 0xbf]) {
            return Err("canonical candidate source must not contain a UTF-8 BOM".into());
        }
        let text = std::str::from_utf8(bytes)
            .map_err(|error| format!("canonical candidate source is not UTF-8: {error}"))?;
        if !text.ends_with('\n') || text.ends_with("\n\n") {
            return Err("canonical candidate source must have exactly one terminal LF".into());
        }
        if text.contains('\r') {
            return Err("canonical candidate source must use LF line endings".into());
        }
        let body = &text[..text.len() - 1];
        if body.is_empty() {
            return Err("canonical candidate source is empty".into());
        }
        let lines = body.split('\n').collect::<Vec<_>>();
        if lines.iter().any(|line| line.is_empty() || line.trim_end() != *line) {
            return Err("canonical candidate source contains a blank or padded line".into());
        }
        let mut parser = Self {
            lines,
            position: 0,
        };
        let value = parser.node(0)?;
        if parser.position != parser.lines.len() {
            return Err("canonical candidate source contains trailing content".into());
        }
        Ok(value)
    }

    fn indentation(line: &str) -> Result<usize, String> {
        let indent = line.len() - line.trim_start_matches(' ').len();
        if line[..indent].contains('\t') || indent % 2 != 0 {
            return Err("canonical candidate source indentation must use two spaces".into());
        }
        if line.contains('\t') {
            return Err("canonical candidate source must not contain tabs".into());
        }
        Ok(indent)
    }

    fn node(&mut self, indent: usize) -> Result<Json, String> {
        let line = *self
            .lines
            .get(self.position)
            .ok_or_else(|| "canonical candidate source ended before a value".to_owned())?;
        let actual = Self::indentation(line)?;
        if actual != indent {
            return Err(format!(
                "canonical candidate source indentation {actual} does not equal expected {indent}"
            ));
        }
        let content = &line[indent..];
        if content == "-" || content.starts_with("- ") {
            self.sequence(indent)
        } else if is_canonical_mapping_line(content) {
            self.mapping(indent)
        } else if content.starts_with('"') {
            self.scalar_line(content)
        } else if content == "{}"
            || content == "[]"
            || content == "true"
            || content == "false"
            || content == "null"
            || content.starts_with('-')
            || content
                .as_bytes()
                .first()
                .is_some_and(|byte| byte.is_ascii_digit())
        {
            self.scalar_line(content)
        } else {
            self.mapping(indent)
        }
    }

    fn scalar_line(&mut self, content: &str) -> Result<Json, String> {
        self.position += 1;
        canonical_yaml_scalar(content)
    }

    fn mapping(&mut self, indent: usize) -> Result<Json, String> {
        let mut values = BTreeMap::new();
        while let Some(line) = self.lines.get(self.position).copied() {
            let actual = Self::indentation(line)?;
            if actual != indent || line[indent..].starts_with('-') {
                break;
            }
            let (key, rest) = canonical_yaml_key(&line[indent..])?;
            self.position += 1;
            let value = if rest.is_empty() {
                let next = self.lines.get(self.position).copied().ok_or_else(|| {
                    "canonical YAML mapping value is missing".to_owned()
                })?;
                let child_indent = Self::indentation(next)?;
                if child_indent != indent + 2 {
                    return Err("canonical YAML nested value must be indented by two spaces".into());
                }
                self.node(child_indent)?
            } else {
                canonical_yaml_scalar(rest)?
            };
            if values.insert(key.clone(), value).is_some() {
                return Err(format!("duplicate canonical YAML mapping key: {key}"));
            }
        }
        if values.is_empty() {
            return Err("canonical YAML mapping is empty".into());
        }
        Ok(Json::Object(values))
    }

    fn sequence(&mut self, indent: usize) -> Result<Json, String> {
        let mut values = Vec::new();
        while let Some(line) = self.lines.get(self.position).copied() {
            let actual = Self::indentation(line)?;
            if actual != indent || !line[indent..].starts_with('-') {
                break;
            }
            let content = &line[indent..];
            if content != "-" && !content.starts_with("- ") {
                return Err("canonical YAML sequence marker is malformed".into());
            }
            let rest = content.strip_prefix('-').unwrap();
            self.position += 1;
            if rest.is_empty() {
                let next = self.lines.get(self.position).copied().ok_or_else(|| {
                    "canonical YAML sequence item is missing".to_owned()
                })?;
                let child_indent = Self::indentation(next)?;
                if child_indent != indent + 2 {
                    return Err("canonical YAML sequence item must be indented by two spaces".into());
                }
                values.push(self.node(child_indent)?);
            } else {
                values.push(canonical_yaml_scalar(rest.strip_prefix(' ').unwrap())?);
            }
        }
        if values.is_empty() {
            return Err("canonical YAML sequence is empty".into());
        }
        Ok(Json::Array(values))
    }
}

pub(crate) fn decode_canonical_candidate(bytes: &[u8]) -> Result<Json, String> {
    CanonicalYaml::decode(bytes)
}

pub(crate) fn decode_and_validate_candidate(
    artifact: &CandidateSourceArtifact,
) -> Result<Json, String> {
    if artifact.serialization_profile != SERIALIZATION_PROFILE {
        return Err("candidate serialization profile is not adr-kit.authoring-yaml/v1".into());
    }
    if sha256_digest(&artifact.bytes) != artifact.content_digest {
        return Err("candidate content_digest does not match exact source bytes".into());
    }
    let source = decode_canonical_candidate(&artifact.bytes)?;
    let rendered = render_source(&artifact.source_schema, &source)?;
    if rendered != artifact.bytes {
        return Err("candidate source bytes are not canonical under their exact schema selector".into());
    }
    validate_selected_authoring_schema(&artifact.source_schema, &source)?;
    Ok(source)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn json_string(value: &Json) -> Option<&str> {
        value.as_str()
    }

    fn base64_decode(input: &str) -> Result<Vec<u8>, String> {
        fn value(byte: u8) -> Result<u8, String> {
            match byte {
                b'A'..=b'Z' => Ok(byte - b'A'),
                b'a'..=b'z' => Ok(byte - b'a' + 26),
                b'0'..=b'9' => Ok(byte - b'0' + 52),
                b'+' => Ok(62),
                b'/' => Ok(63),
                _ => Err(format!("invalid base64 byte: {byte}")),
            }
        }
        let bytes = input.as_bytes();
        if bytes.len() % 4 != 0 {
            return Err("base64 length is not a multiple of four".into());
        }
        let mut result = Vec::new();
        for chunk in bytes.chunks_exact(4) {
            let a = value(chunk[0])? as u32;
            let b = value(chunk[1])? as u32;
            let c = if chunk[2] == b'=' {
                0
            } else {
                value(chunk[2])? as u32
            };
            let d = if chunk[3] == b'=' {
                0
            } else {
                value(chunk[3])? as u32
            };
            result.push(((a << 2) | (b >> 4)) as u8);
            if chunk[2] != b'=' {
                result.push((((b & 0xf) << 4) | (c >> 2)) as u8);
            }
            if chunk[3] != b'=' {
                result.push((((c & 0x3) << 6) | d) as u8);
            }
        }
        Ok(result)
    }

    fn frozen_conformance() -> Json {
        serde_json::from_str(include_str!(
            "../../contracts/authoring-construction/v1.0/resources/conformance.json"
        ))
        .expect("frozen ACC conformance is valid JSON")
    }

    fn selector(value: &Json) -> CandidateSourceSelector {
        let object = value.as_object().expect("source schema object");
        CandidateSourceSelector {
            canonical_resource_key: json_string(
                object.get("canonical_resource_key").expect("resource key"),
            )
            .expect("resource key string")
            .to_owned(),
            json_pointer: json_string(object.get("json_pointer").expect("JSON pointer"))
                .expect("JSON pointer string")
                .to_owned(),
        }
    }

    fn seal_frozen_artifact(value: &Json) -> CandidateSourceArtifact {
        let object = value.as_object().expect("candidate artifact object");
        let bytes = base64_decode(
            json_string(object.get("bytes").expect("candidate bytes"))
                .expect("candidate bytes string"),
        )
        .expect("candidate bytes base64");
        let source = decode_canonical_candidate(&bytes).expect("frozen candidate bytes parse");
        let source_schema = selector(object.get("source_schema").expect("source schema"));
        let source_contract = object
            .get("source_contract")
            .expect("source contract")
            .clone();
        let artifact = seal_candidate_artifact(
            json_string(object.get("request_key").expect("request key"))
                .expect("request key string"),
            json_string(object.get("source_ref").expect("source ref")).expect("source ref string"),
            json_string(object.get("artifact_kind").expect("artifact kind"))
                .expect("artifact kind string"),
            source_schema.clone(),
            source_contract.clone(),
            &source,
        )
        .expect("frozen candidate source seals");
        assert_eq!(artifact.bytes, bytes);
        assert_eq!(
            artifact.content_digest,
            object
                .get("content_digest")
                .and_then(Json::as_str)
                .expect("content digest string")
        );
        assert_eq!(artifact.serialization_profile, SERIALIZATION_PROFILE);
        assert_eq!(
            artifact.request_key,
            object
                .get("request_key")
                .and_then(Json::as_str)
                .expect("request key")
        );
        assert_eq!(
            artifact.source_ref,
            object
                .get("source_ref")
                .and_then(Json::as_str)
                .expect("source ref")
        );
        assert_eq!(
            artifact.artifact_kind,
            object
                .get("artifact_kind")
                .and_then(Json::as_str)
                .expect("artifact kind")
        );
        assert_eq!(artifact.source_schema, source_schema);
        assert_eq!(artifact.source_contract, source_contract);
        artifact
    }

    #[test]
    fn rust_renderer_reproduces_every_frozen_candidate_artifact() {
        let corpus = frozen_conformance();
        let cases = corpus
            .get("cases")
            .and_then(Json::as_array)
            .expect("ACC cases");
        let mut artifact_count = 0;
        for case in cases {
            let result = case
                .get("expected")
                .and_then(Json::as_object)
                .and_then(|value| value.get("result"))
                .and_then(Json::as_object)
                .expect("ACC expected result");
            let artifacts = result
                .get("candidate_artifacts")
                .and_then(Json::as_array)
                .cloned()
                .unwrap_or_default();
            for artifact in &artifacts {
                seal_frozen_artifact(artifact);
                artifact_count += 1;
            }
        }
        assert_eq!(artifact_count, 32, "ACC artifact corpus remains complete");
    }

    #[test]
    fn rust_basis_sealer_reproduces_every_frozen_basis_digest_and_order() {
        let corpus = frozen_conformance();
        let cases = corpus
            .get("cases")
            .and_then(Json::as_array)
            .expect("ACC cases");
        for case in cases {
            let result = case
                .get("expected")
                .and_then(Json::as_object)
                .and_then(|value| value.get("result"))
                .and_then(Json::as_object)
                .expect("ACC expected result");
            let artifacts = result
                .get("candidate_artifacts")
                .and_then(Json::as_array)
                .cloned()
                .unwrap_or_default();
            let sealed = artifacts
                .iter()
                .map(seal_frozen_artifact)
                .collect::<Vec<_>>();
            let Some(basis) = result
                .get("candidate_source_basis")
                .filter(|value| !matches!(value, Json::Null))
            else {
                continue;
            };
            let case_id = case.get("id").and_then(Json::as_str).unwrap_or("case");
            let basis_object = basis.as_object().expect("basis object");
            let selected_refs = basis_object
                .get("artifacts")
                .and_then(Json::as_array)
                .expect("basis artifacts")
                .iter()
                .map(|artifact| {
                    artifact
                        .get("source_ref")
                        .and_then(Json::as_str)
                        .expect("basis source ref")
                })
                .collect::<Vec<_>>();
            if case_id == "C05" {
                assert_eq!(selected_refs, vec!["candidate/C05/parent"]);
                assert_eq!(sealed.len(), 2, "C05 retains its child artifact");
            }
            if case_id == "C07" {
                assert_eq!(selected_refs, vec!["candidate/C07/adr"]);
                assert_eq!(sealed.len(), 2, "C07 retains its child artifact");
            }
            let selected = sealed
                .iter()
                .filter(|artifact| selected_refs.contains(&artifact.source_ref.as_str()))
                .cloned()
                .collect::<Vec<_>>();
            let actual = seal_candidate_source_basis(selected).expect("frozen basis seals");
            assert_eq!(
                actual
                    .artifacts
                    .iter()
                    .map(|artifact| artifact.source_ref.as_str())
                    .collect::<Vec<_>>(),
                selected_refs,
                "{} basis artifact order remains frozen",
                case_id
            );
            assert_eq!(
                actual.basis_digest,
                basis_object
                    .get("basis_digest")
                    .and_then(Json::as_str)
                    .expect("basis digest"),
                "{} basis digest remains frozen",
                case_id
            );
        }
    }

    #[test]
    fn canonical_profile_handles_open_maps_scalars_and_exact_newlines() {
        let properties = Json::Object(BTreeMap::from([
            ("z".into(), Json::Number(serde_json::Number::from(2))),
            ("a".into(), Json::String("café \"x\"\\\n".into())),
            ("flag".into(), Json::Bool(false)),
            (
                "arr".into(),
                Json::Array(vec![
                    Json::String("first".into()),
                    Json::Number(serde_json::Number::from(1)),
                ]),
            ),
        ]));
        let source = Json::Object(BTreeMap::from([("properties".into(), properties)]));
        let selector = CandidateSourceSelector {
            canonical_resource_key: "authoring/1.7/schema/adr-common.schema".into(),
            json_pointer: "/definitions/custom_entity".into(),
        };
        let artifact = seal_candidate_artifact(
            "edge",
            "candidate/edge",
            "authoring_fragment",
            selector,
            Json::Null,
            &source,
        )
        .expect("edge source seals");
        let text = std::str::from_utf8(&artifact.bytes).expect("UTF-8 candidate bytes");
        assert_eq!(
            text,
            "\"properties\":\n  \"a\": \"café \\\"x\\\"\\\\\\n\"\n  \"arr\":\n    - \"first\"\n    - 1\n  \"flag\": false\n  \"z\": 2\n"
        );
        assert_eq!(artifact.bytes.last(), Some(&b'\n'));
        assert_eq!(
            artifact.bytes.iter().filter(|byte| **byte == b'\n').count(),
            7
        );
        assert!(!artifact.bytes.windows(2).any(|pair| pair == b"\r\n"));
        assert!(!artifact.bytes.starts_with(&[0xef, 0xbb, 0xbf]));
        assert!(!text.contains("---") && !text.contains("#"));
        let mut null = String::new();
        render_scalar(&Json::Null, &mut null).expect("null scalar is canonical");
        assert_eq!(null, "null");
        let repeated = seal_candidate_artifact(
            "edge",
            "candidate/edge",
            "authoring_fragment",
            artifact.source_schema.clone(),
            Json::Null,
            &source,
        )
        .expect("repeat edge source seals");
        assert_eq!(artifact, repeated);
    }

    #[test]
    fn strict_inverse_rejects_noncanonical_profile_spellings() {
        let valid = b"\"a\":\n  - true\n  - null\n";
        let decoded = decode_canonical_candidate(valid).expect("valid canonical profile");
        assert_eq!(
            decoded,
            Json::Object(BTreeMap::from([(
                "a".into(),
                Json::Array(vec![Json::Bool(true), Json::Null]),
            )]))
        );

        let invalid_inputs: &[&[u8]] = &[
            b"\xef\xbb\xbf\"a\": \"b\"\n",
            b"\"a\": \"b\"\r\n",
            b"\"a\": \"b\"",
            b"\"a\": \"b\"\n\n",
            b"\"a\": \"b\"\n \n",
            b"---\n\"a\": \"b\"\n",
            b"%YAML 1.2\n\"a\": \"b\"\n",
            b"\"a\": \"b\" # comment\n",
            b"\"a\": &anchor\n",
            b"\"a\": *anchor\n",
            b"\"a\": !tag\n",
            b"\"a\":\n   \"b\"\n",
            b"\"a\": \"one\"\n\"a\": \"two\"\n",
            b"\"a\": True\n",
            b"\"a\": 01\n",
            b"'a': \"b\"\n",
        ];
        for bytes in invalid_inputs {
            assert!(
                decode_canonical_candidate(bytes).is_err(),
                "noncanonical bytes were accepted: {:?}",
                String::from_utf8_lossy(bytes)
            );
        }
        assert!(decode_canonical_candidate(&[0xff, b'\n']).is_err());
    }

    #[test]
    fn closed_schema_and_basis_integrity_fail_closed() {
        let source = Json::Object(BTreeMap::from([("unknown".into(), Json::Null)]));
        let selector = CandidateSourceSelector {
            canonical_resource_key: "authoring/1.7/schema/adr-common.schema".into(),
            json_pointer: "/definitions/decision".into(),
        };
        assert!(seal_candidate_artifact(
            "decision",
            "candidate/decision",
            "authoring_fragment",
            selector,
            Json::Null,
            &source,
        )
        .is_err());

        let valid_source = Json::Object(BTreeMap::from([(
            "id".into(),
            Json::String("019109a0-b1c2-7def-8a00-112233445566".into()),
        )]));
        let selector = CandidateSourceSelector {
            canonical_resource_key: "authoring/1.7/schema/adr-common.schema".into(),
            json_pointer: "/definitions/decision".into(),
        };
        let artifact = seal_candidate_artifact(
            "decision",
            "candidate/decision",
            "authoring_fragment",
            selector,
            Json::Null,
            &valid_source,
        )
        .expect("valid detached artifact");
        let mut duplicate = artifact.clone();
        duplicate.bytes.push(b'x');
        assert!(seal_candidate_source_basis(vec![artifact.clone(), artifact]).is_err());
        assert!(seal_candidate_source_basis(vec![duplicate]).is_err());
    }
}
