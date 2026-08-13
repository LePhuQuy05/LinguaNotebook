"use client";

interface ChapterStructure {
  id: string;
  part: string;
  chapter_num: number;
  chapter_title: string;
  page_start: number;
  page_end: number;
  order: number;
}

interface CurriculumMapProps {
  structures: ChapterStructure[];
}

/**
 * The book's curriculum map: chapters extracted from the TOC during parse,
 * grouped by part. Renders nothing when the document has no map yet.
 */
export function CurriculumMap({ structures }: CurriculumMapProps) {
  if (!structures || structures.length === 0) return null;

  // Group by part, preserving TOC order.
  const parts: { part: string; chapters: ChapterStructure[] }[] = [];
  for (const s of structures) {
    const group = parts.find((p) => p.part === s.part);
    if (group) group.chapters.push(s);
    else parts.push({ part: s.part, chapters: [s] });
  }

  return (
    <div className="space-y-6 rounded-xl border border-border bg-surface p-6">
      <div>
        <h2 className="font-heading text-lg font-semibold text-foreground">
          Curriculum Map
        </h2>
        <p className="mt-1 text-sm text-foreground-muted">
          Chapters detected from this book's table of contents. Daily lessons
          are drawn from one chapter at a time, in order.
        </p>
      </div>

      {parts.map((part) => (
        <div key={part.part} className="space-y-2">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground-muted">
            {part.part}
          </h3>
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted text-left text-xs uppercase text-foreground-muted">
                <tr>
                  <th className="w-12 px-3 py-2 font-medium">#</th>
                  <th className="px-3 py-2 font-medium">Chapter</th>
                  <th className="w-20 px-3 py-2 font-medium">Pages</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {part.chapters.map((c) => (
                  <tr key={c.id}>
                    <td className="px-3 py-2 text-foreground-muted">{c.chapter_num}</td>
                    <td className="px-3 py-2 text-foreground">{c.chapter_title}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-foreground-muted">
                      {c.page_start}–{c.page_end}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
