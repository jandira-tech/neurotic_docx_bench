// The five HTML metacharacters, and only those five. Copied from
// jubarte-app's site/layout.ts (commit ad9b73e) so both sites escape the
// same way; a text value that goes through esc() can be dropped into an
// attribute or into text without a second thought.

const ENTITIES: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

/** Escape every HTML metacharacter in a text value. */
export function esc(value: string | number): string {
  if (typeof value !== "string" && typeof value !== "number") {
    throw new TypeError("esc: value must be a string or number");
  }
  return String(value).replace(/[&<>"']/g, (c) => ENTITIES[c]);
}
