import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownContentProps {
  content: string;
}

/**
 * Renders stored block markdown (GFM pipe tables) as real HTML.
 *
 * Raw HTML inside the content is intentionally dropped (react-markdown's
 * default — no rehypeRaw): stored content is HPD-generated markdown, and
 * rendering raw HTML would reopen the XSS surface the removed
 * dangerouslySetInnerHTML had.
 */
export function MarkdownContent({ content }: MarkdownContentProps) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>;
}
