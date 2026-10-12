// Deliberate deep imports into vendored node_modules trees (the exact jszip
// instance @ansonlai/docx-redline-js resolves against) carry no usable types:
// jszip's declarations sit at the package root, not next to lib/index.js. Every
// consumer types the values as `any`, so declare the deep specifier here instead
// of changing the runtime resolution. (@xmldom's deep import is suppressed at its
// call site — its index.d.ts resolves and wins over an ambient declaration.)
declare module "*/jszip/lib/index.js";
