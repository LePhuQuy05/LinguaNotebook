// Plain jest config (not next/jest): next/jest unconditionally prepends a
// node_modules ignore-all pattern, which cannot be overridden and prevents
// transforming ESM-only deps like react-markdown. babel-jest + next/babel
// gives the same transforms with full control.
module.exports = {
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  testPathIgnorePatterns: ["<rootDir>/node_modules/", "<rootDir>/e2e/"],
  transform: {
    "^.+\\.(js|jsx|ts|tsx)$": ["babel-jest", { presets: ["next/babel"] }],
  },
  // react-markdown and its dependency chain are ESM-only; babel-jest must
  // transform them. The optional `.pnpm/…/node_modules/` segment covers
  // pnpm's virtual store layout. If a new ESM-only transitive dep makes
  // jest fail with "cannot use import statement outside a module", add it
  // to the alternation below.
  transformIgnorePatterns: [
    "node_modules/(?!(?:\\.pnpm/.+/node_modules/)?(react-markdown|remark-gfm|remark-parse|remark-rehype|remark-stringify|unified|unist-util-.*|mdast-util-.*|micromark-.*|micromark|micromark-core-commonmark|trough|stringify-entities|markdown-table|longest-streak|decode-named-character-reference|character-entities|character-entities-html4|character-entities-legacy|hast-util-.*|property-information|hastscript|web-namespaces|space-separated-tokens|comma-separated-tokens|estree-util-.*|zwitch|bail|is-plain-obj|trim-lines|vfile|vfile-message|devlop|ccount|escape-string-regexp|html-url-attributes|@types\\/hast|@types\\/mdast|@types\\/unist|@types\\/estree)/)",
  ],
};
