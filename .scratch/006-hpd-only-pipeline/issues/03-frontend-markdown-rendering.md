# 03 — Frontend renders real markdown

**What to build:** The document page stops showing raw markdown source (`| a | b |`, `---`) as literal text. Block content is rendered through a markdown renderer with GFM table support — pipe tables display as actual tables with borders and columns, headings render as headings. This works immediately for already-parsed documents (no re-parse needed).

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Markdown renderer (react-markdown + remark-gfm) added to the frontend; block content renders through it
- [ ] `dangerouslySetInnerHTML` no longer used for block content
- [ ] Component test: content containing a GFM table renders a `<table>` element in the DOM — no literal pipes in the visible text
- [ ] Verified against an existing parsed document (e.g. the Shinkanzen N3 TOC page): the table displays as a real table
- [ ] Existing block styling (left border, type label, page number) preserved
