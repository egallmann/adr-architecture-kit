import { schemaAssets } from "../generated/schema-assets.js";
import { schemaManifest } from "../generated/schema-manifest.js";

export { schemaManifest };
export const canonicalSchemas = schemaAssets;
export function getCanonicalSchema(path: string): unknown {
  const schema = canonicalSchemas[path as keyof typeof canonicalSchemas];
  if (!schema) throw new Error(`Unknown canonical schema asset: ${path}`);
  return schema;
}
export function getSemanticAttributionVocabulary(version: "1.5" | "1.6"): Record<string, unknown> {
  return canonicalSchemas[`evidence-attribution/v${version}/semantic-attribution-vocabulary.json`] as Record<string, unknown>;
}
