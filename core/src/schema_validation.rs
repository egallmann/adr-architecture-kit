//! Deterministic JSON-Schema validation for the sealed semantic boundary.
//!
//! The materializer receives schema resources as part of the qualified
//! semantic-contract definition bundle.  This evaluator deliberately has no
//! filesystem, network, or ambient registry access: every `$ref` must resolve
//! to one of those supplied resources and every resource must already have
//! passed the source-contract digest qualification.  Rust is only the
//! execution mechanism here; the JSON resources remain the governing schema.

use std::collections::{BTreeMap, BTreeSet};

use regex::Regex;

use super::Json;

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct SchemaError {
    pub path: String,
    pub message: String,
}

pub(crate) fn validate(
    resources: &BTreeMap<String, Json>,
    root_key: &str,
    value: &Json,
) -> Result<(), SchemaError> {
    let Some(schema) = resources.get(root_key) else {
        return Err(SchemaError {
            path: String::new(),
            message: format!(
                "schema validation failed: sealed schema resource {root_key} is unavailable"
            ),
        });
    };
    let mut context = Context {
        resources,
        active_refs: BTreeSet::new(),
    };
    context.validate(value, schema, root_key, "")
}

struct Context<'a> {
    resources: &'a BTreeMap<String, Json>,
    active_refs: BTreeSet<String>,
}

impl<'a> Context<'a> {
    fn validate(
        &mut self,
        value: &Json,
        schema: &Json,
        resource_key: &str,
        path: &str,
    ) -> Result<(), SchemaError> {
        let Some(schema) = schema.as_object() else {
            return Err(self.error(path, "schema must be an object"));
        };
        self.reject_unsupported_keywords(schema, path)?;

        if let Some(reference) = schema.get("$ref").and_then(Json::as_str) {
            let reference_key = format!("{resource_key}#{reference}");
            if !self.active_refs.insert(reference_key.clone()) {
                return Err(
                    self.error(path, "schema validation failed: cyclic $ref is unsupported")
                );
            }
            let (target_key, target) = self.resolve_ref(resource_key, reference, path)?;
            let result = self.validate(value, &target, &target_key, path);
            self.active_refs.remove(&reference_key);
            result?;
        }

        if let Some(compositions) = schema.get("allOf").and_then(Json::as_array) {
            for branch in compositions {
                self.validate(value, branch, resource_key, path)?;
            }
        }
        if let Some(compositions) = schema.get("anyOf").and_then(Json::as_array) {
            self.validate_any_of(value, compositions, resource_key, path, false)?;
        }
        if let Some(compositions) = schema.get("oneOf").and_then(Json::as_array) {
            self.validate_any_of(value, compositions, resource_key, path, true)?;
        }
        if let Some(condition) = schema.get("if") {
            let mut probe = Context {
                resources: self.resources,
                active_refs: self.active_refs.clone(),
            };
            let condition_matches = probe.validate(value, condition, resource_key, path).is_ok();
            let selected = if condition_matches {
                schema.get("then")
            } else {
                schema.get("else")
            };
            if let Some(selected) = selected {
                self.validate(value, selected, resource_key, path)?;
            }
        }
        if let Some(prohibited) = schema.get("not") {
            let mut probe = Context {
                resources: self.resources,
                active_refs: self.active_refs.clone(),
            };
            if probe
                .validate(value, prohibited, resource_key, path)
                .is_ok()
            {
                return Err(self.error(
                    path,
                    "schema validation failed: value matches a prohibited schema",
                ));
            }
        }

        if let Some(expected) = schema.get("type") {
            let matches = match expected {
                Json::String(name) => self.type_matches(value, name),
                Json::Array(names) => names.iter().any(|name| {
                    name.as_str()
                        .is_some_and(|name| self.type_matches(value, name))
                }),
                _ => {
                    return Err(
                        self.error(path, "schema validation failed: type keyword is invalid")
                    )
                }
            };
            if !matches {
                return Err(self.error(
                    path,
                    format!(
                        "schema validation failed: expected {}",
                        type_description(expected)
                    ),
                ));
            }
        }
        if let Some(expected) = schema.get("const") {
            if value != expected {
                return Err(self.error(
                    path,
                    format!(
                        "schema validation failed: value must equal {}",
                        display_json(expected)
                    ),
                ));
            }
        }
        if let Some(values) = schema.get("enum").and_then(Json::as_array) {
            if !values.iter().any(|candidate| candidate == value) {
                return Err(self.error(
                    path,
                    "schema validation failed: value is outside the governed enum",
                ));
            }
        }

        if let Some(string_value) = value.as_str() {
            self.validate_string(schema, string_value, path)?;
        }
        if let Some(array_value) = value.as_array() {
            self.validate_array(schema, array_value, resource_key, path)?;
        }
        if let Some(object_value) = value.as_object() {
            self.validate_object(schema, object_value, resource_key, path)?;
        }
        if let Some(number) = value.as_number() {
            self.validate_number(schema, number, path)?;
        }
        Ok(())
    }

    fn validate_any_of(
        &mut self,
        value: &Json,
        branches: &[Json],
        resource_key: &str,
        path: &str,
        exactly_one: bool,
    ) -> Result<(), SchemaError> {
        let mut matches = 0;
        let mut first_error = None;
        for branch in branches {
            let mut probe = Context {
                resources: self.resources,
                active_refs: self.active_refs.clone(),
            };
            match probe.validate(value, branch, resource_key, path) {
                Ok(()) => matches += 1,
                Err(error) => {
                    if first_error.is_none() {
                        first_error = Some(error);
                    }
                }
            }
        }
        let valid = if exactly_one {
            matches == 1
        } else {
            matches > 0
        };
        if valid {
            Ok(())
        } else if exactly_one {
            Err(self.error(
                path,
                "schema validation failed: exactly one schema branch must match",
            ))
        } else {
            Err(first_error.unwrap_or_else(|| {
                self.error(
                    path,
                    "schema validation failed: one schema branch must match",
                )
            }))
        }
    }

    fn validate_string(
        &self,
        schema: &BTreeMap<String, Json>,
        value: &str,
        path: &str,
    ) -> Result<(), SchemaError> {
        let length = value.chars().count() as u64;
        if let Some(minimum) = schema.get("minLength").and_then(Json::as_u64) {
            if length < minimum {
                return Err(self.error(
                    path,
                    format!("schema validation failed: string length must be at least {minimum}"),
                ));
            }
        }
        if let Some(maximum) = schema.get("maxLength").and_then(Json::as_u64) {
            if length > maximum {
                return Err(self.error(
                    path,
                    format!("schema validation failed: string length must be at most {maximum}"),
                ));
            }
        }
        if let Some(pattern) = schema.get("pattern").and_then(Json::as_str) {
            let regex = Regex::new(pattern).map_err(|_| {
                self.error(
                    path,
                    "schema validation failed: governed pattern is invalid",
                )
            })?;
            if !regex.is_match(value) {
                return Err(self.error(
                    path,
                    format!("schema validation failed: string does not match pattern {pattern}"),
                ));
            }
        }
        Ok(())
    }

    fn validate_array(
        &mut self,
        schema: &BTreeMap<String, Json>,
        values: &[Json],
        resource_key: &str,
        path: &str,
    ) -> Result<(), SchemaError> {
        let length = values.len() as u64;
        if let Some(minimum) = schema.get("minItems").and_then(Json::as_u64) {
            if length < minimum {
                return Err(self.error(
                    path,
                    format!(
                        "schema validation failed: array must contain at least {minimum} item(s)"
                    ),
                ));
            }
        }
        if let Some(maximum) = schema.get("maxItems").and_then(Json::as_u64) {
            if length > maximum {
                return Err(self.error(
                    path,
                    format!(
                        "schema validation failed: array must contain at most {maximum} item(s)"
                    ),
                ));
            }
        }
        if let Some(item_schema) = schema.get("items") {
            match item_schema {
                Json::Object(_) => {
                    for (index, item) in values.iter().enumerate() {
                        self.validate(item, item_schema, resource_key, &index_path(path, index))?;
                    }
                }
                Json::Array(tuple) => {
                    for (index, item) in values.iter().enumerate() {
                        if let Some(item_schema) = tuple.get(index) {
                            self.validate(
                                item,
                                item_schema,
                                resource_key,
                                &index_path(path, index),
                            )?;
                        }
                    }
                }
                _ => {
                    return Err(
                        self.error(path, "schema validation failed: items keyword is invalid")
                    )
                }
            }
        }
        Ok(())
    }

    fn validate_object(
        &mut self,
        schema: &BTreeMap<String, Json>,
        value: &BTreeMap<String, Json>,
        resource_key: &str,
        path: &str,
    ) -> Result<(), SchemaError> {
        if let Some(required) = schema.get("required").and_then(Json::as_array) {
            for property in required {
                let Some(property) = property.as_str() else {
                    return Err(self.error(
                        path,
                        "schema validation failed: required keyword is invalid",
                    ));
                };
                if !value.contains_key(property) {
                    return Err(self.error(
                        &property_path(path, property),
                        format!(
                            "schema validation failed: required property '{property}' is missing"
                        ),
                    ));
                }
            }
        }
        if let Some(property_names) = schema.get("propertyNames") {
            for property in value.keys() {
                self.validate(
                    &Json::String(property.clone()),
                    property_names,
                    resource_key,
                    &property_path(path, property),
                )?;
            }
        }
        let properties = schema.get("properties").and_then(Json::as_object);
        for (property, property_schema) in properties
            .into_iter()
            .flat_map(|properties| properties.iter())
        {
            if let Some(property_value) = value.get(property) {
                self.validate(
                    property_value,
                    property_schema,
                    resource_key,
                    &property_path(path, property),
                )?;
            }
        }
        if let Some(additional) = schema.get("additionalProperties") {
            for (property, property_value) in value {
                if properties.is_some_and(|properties| properties.contains_key(property)) {
                    continue;
                }
                match additional {
                    Json::Bool(true) => {}
                    Json::Bool(false) => {
                        return Err(self.error(
                            &property_path(path, property),
                            format!(
                                "schema validation failed: property '{property}' is not allowed"
                            ),
                        ));
                    }
                    Json::Object(_) => self.validate(
                        property_value,
                        additional,
                        resource_key,
                        &property_path(path, property),
                    )?,
                    _ => {
                        return Err(self.error(
                            path,
                            "schema validation failed: additionalProperties keyword is invalid",
                        ))
                    }
                }
            }
        }
        Ok(())
    }

    fn validate_number(
        &self,
        schema: &BTreeMap<String, Json>,
        value: &serde_json::Number,
        path: &str,
    ) -> Result<(), SchemaError> {
        let Some(value) = value.as_f64() else {
            return Ok(());
        };
        for (keyword, comparison) in [("minimum", true), ("maximum", false)] {
            if let Some(limit) = schema.get(keyword).and_then(Json::as_f64) {
                if (comparison && value < limit) || (!comparison && value > limit) {
                    return Err(self.error(
                        path,
                        format!("schema validation failed: number violates {keyword}"),
                    ));
                }
            }
        }
        Ok(())
    }

    fn type_matches(&self, value: &Json, name: &str) -> bool {
        match name {
            "null" => matches!(value, Json::Null),
            "boolean" => matches!(value, Json::Bool(_)),
            "object" => matches!(value, Json::Object(_)),
            "array" => matches!(value, Json::Array(_)),
            "string" => matches!(value, Json::String(_)),
            "number" => matches!(value, Json::Number(_)),
            "integer" => matches!(value, Json::Number(value) if value.is_i64() || value.is_u64()),
            _ => false,
        }
    }

    fn resolve_ref(
        &self,
        resource_key: &str,
        reference: &str,
        path: &str,
    ) -> Result<(String, Json), SchemaError> {
        let (resource_ref, fragment) = reference.split_once('#').unwrap_or((reference, ""));
        let target_key = if resource_ref.is_empty() {
            resource_key.to_owned()
        } else {
            let directory = resource_key
                .rsplit_once('/')
                .map(|(directory, _)| directory)
                .unwrap_or("");
            let mut key = if resource_ref.ends_with(".json") {
                resource_ref.trim_end_matches(".json").to_owned()
            } else {
                resource_ref.to_owned()
            };
            if !key.starts_with("authoring/") && !directory.is_empty() {
                key = format!("{directory}/{key}");
            }
            key
        };
        let Some(resource) = self.resources.get(&target_key) else {
            return Err(self.error(
                path,
                format!("schema validation failed: sealed $ref target {target_key} is unavailable"),
            ));
        };
        if fragment.is_empty() {
            return Ok((target_key, resource.clone()));
        }
        let pointer = fragment.strip_prefix('/').ok_or_else(|| {
            self.error(
                path,
                "schema validation failed: only JSON Pointer $ref fragments are supported",
            )
        })?;
        let mut current = resource;
        for segment in pointer.split('/') {
            let segment = segment.replace("~1", "/").replace("~0", "~");
            current = current
                .as_object()
                .and_then(|object| object.get(&segment))
                .ok_or_else(|| self.error(path, format!("schema validation failed: sealed $ref pointer {reference} is unresolved")))?;
        }
        Ok((target_key, current.clone()))
    }

    fn reject_unsupported_keywords(
        &self,
        schema: &BTreeMap<String, Json>,
        path: &str,
    ) -> Result<(), SchemaError> {
        const SUPPORTED: &[&str] = &[
            "$id",
            "$ref",
            "$schema",
            "title",
            "description",
            "definitions",
            "type",
            "allOf",
            "anyOf",
            "oneOf",
            "if",
            "then",
            "else",
            "not",
            "const",
            "enum",
            "pattern",
            "minLength",
            "maxLength",
            "minItems",
            "maxItems",
            "items",
            "required",
            "properties",
            "propertyNames",
            "additionalProperties",
            "minimum",
            "maximum",
        ];
        for keyword in schema.keys() {
            if !SUPPORTED.contains(&keyword.as_str()) {
                return Err(self.error(
                    path,
                    format!("schema validation failed: unsupported schema keyword {keyword}"),
                ));
            }
        }
        Ok(())
    }

    fn error(&self, path: &str, message: impl Into<String>) -> SchemaError {
        SchemaError {
            path: path.to_owned(),
            message: message.into(),
        }
    }
}

fn property_path(path: &str, property: &str) -> String {
    if path.is_empty() {
        property.to_owned()
    } else {
        format!("{path}.{property}")
    }
}

fn index_path(path: &str, index: usize) -> String {
    if path.is_empty() {
        format!("[{index}]")
    } else {
        format!("{path}[{index}]")
    }
}

fn type_description(value: &Json) -> String {
    match value {
        Json::String(value) => format!("type {value}"),
        Json::Array(values) => format!(
            "one of {}",
            values
                .iter()
                .filter_map(Json::as_str)
                .collect::<Vec<_>>()
                .join(", ")
        ),
        _ => "a valid schema type".to_owned(),
    }
}

fn display_json(value: &Json) -> String {
    serde_json::to_string(value).unwrap_or_else(|_| "<invalid-json>".to_owned())
}

#[cfg(test)]
mod tests {
    use super::{validate, Json};
    use std::collections::BTreeMap;

    fn parsed(value: &str) -> Json {
        serde_json::from_str(value).expect("test JSON is valid")
    }

    #[test]
    fn resolves_only_the_supplied_resource_closure() {
        let resources = BTreeMap::from([
            (
                "authoring/1.6/schema/root.schema".to_owned(),
                parsed(
                    r#"{"type":"object","properties":{"name":{"$ref":"types.schema.json#/definitions/name"}},"required":["name"]}"#,
                ),
            ),
            (
                "authoring/1.6/schema/types.schema".to_owned(),
                parsed(r#"{"definitions":{"name":{"type":"string","minLength":3}}}"#),
            ),
        ]);
        assert!(validate(
            &resources,
            "authoring/1.6/schema/root.schema",
            &parsed(r#"{"name":"valid"}"#)
        )
        .is_ok());
        let error = validate(
            &resources,
            "authoring/1.6/schema/root.schema",
            &parsed(r#"{"name":"x"}"#),
        )
        .expect_err("short name must fail");
        assert_eq!(error.path, "name");
        let missing = BTreeMap::from([(
            "authoring/1.6/schema/root.schema".to_owned(),
            parsed(r#"{"$ref":"missing.schema.json"}"#),
        )]);
        assert!(validate(
            &missing,
            "authoring/1.6/schema/root.schema",
            &parsed("null")
        )
        .is_err());
    }

    #[test]
    fn enforces_nested_type_pattern_not_and_additional_properties() {
        let resources = BTreeMap::from([(
            "root.schema".to_owned(),
            parsed(
                r#"{"type":"object","properties":{"alias":{"type":"string","pattern":"^COMP-[0-9]{4}$"},"nested":{"type":"object","required":["name"],"properties":{"name":{"type":"string"}},"additionalProperties":false}},"required":["alias","nested"],"not":{"required":["component_topology"]},"additionalProperties":false}"#,
            ),
        )]);
        assert!(validate(
            &resources,
            "root.schema",
            &parsed(r#"{"alias":"COMP-0001","nested":{"name":"ok"}}"#)
        )
        .is_ok());
        for invalid in [
            r#"{"alias":"BAD-0001","nested":{"name":"ok"}}"#,
            r#"{"alias":"COMP-0001","nested":{"name":42}}"#,
            r#"{"alias":"COMP-0001","nested":{},"component_topology":{}}"#,
            r#"{"alias":"COMP-0001","nested":{"name":"ok","extra":true}}"#,
        ] {
            assert!(
                validate(&resources, "root.schema", &parsed(invalid)).is_err(),
                "{invalid}"
            );
        }
    }
}
