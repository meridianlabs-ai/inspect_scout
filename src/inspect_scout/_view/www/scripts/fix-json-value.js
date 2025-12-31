/**
 * Post-process generated.ts to fix JsonValue type.
 *
 * openapi-typescript inlines recursive $refs, causing TS2502 errors.
 * This script replaces the inline JsonValue definition with an import
 * from our manually-defined recursive type.
 */
import { readFileSync, writeFileSync } from "fs";

const GENERATED_PATH = "./src/types/generated.ts";

const content = readFileSync(GENERATED_PATH, "utf-8");

// Pattern matches the inline JsonValue type definition
const jsonValuePattern =
  /JsonValue: null \| boolean \| number \| string \| unknown\[\] \| \{\s*\[key: string\]: unknown;\s*\};/;

if (!jsonValuePattern.test(content)) {
  console.error("Could not find JsonValue pattern to replace in generated.ts");
  process.exit(1);
}

// Add import at top and replace inline definition with re-export
const importStatement = 'import { JsonValue } from "./json-value";\n';
const hasImport = content.includes('from "./json-value"');

let updated = content.replace(jsonValuePattern, "JsonValue: JsonValue;");

if (!hasImport) {
  updated = importStatement + updated;
}

writeFileSync(GENERATED_PATH, updated);
console.log("Fixed JsonValue type in generated.ts");
