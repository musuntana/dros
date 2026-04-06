import type {
  EvidenceChunkRead,
  EvidenceLinkRead,
  EvidenceSourceRead,
} from "@/lib/api/generated/control-plane";

const INLINE_PREVIEW_KEYS = [
  ["chunk_text", "Chunk text"],
  ["excerpt_text", "Excerpt"],
  ["snippet_text", "Snippet"],
  ["preview_text", "Preview text"],
  ["abstract_text", "Abstract"],
  ["abstract", "Abstract"],
  ["summary", "Summary"],
  ["text", "Text"],
  ["content", "Content"],
  ["body", "Body"],
  ["quote", "Quote"],
] as const;

const OBJECT_TEXT_KEYS = [
  "text",
  "value",
  "content",
  "body",
  "abstract",
  "excerpt",
  "snippet",
  "preview",
  "quote",
] as const;

const WINDOW_BEFORE = 72;
const WINDOW_AFTER = 120;
const FALLBACK_PREVIEW_LENGTH = 220;

export interface EvidencePreviewSegment {
  emphasized: boolean;
  text: string;
}

export interface EvidencePreview {
  displayText: string | null;
  highlightText: string | null;
  segments: EvidencePreviewSegment[];
  sourceLabel: string | null;
  spanLabel: string;
}

function sanitizeText(value: string): string | null {
  const normalized = value.replace(/\r\n/g, "\n").trim();
  return normalized.length > 0 ? normalized : null;
}

function coerceText(value: unknown, depth = 0): string | null {
  if (typeof value === "string") {
    return sanitizeText(value);
  }

  if (Array.isArray(value)) {
    const items = value
      .map((item) => coerceText(item, depth + 1))
      .filter((item): item is string => item !== null);
    if (items.length === 0) {
      return null;
    }
    return sanitizeText(items.join("\n\n"));
  }

  if (value && typeof value === "object" && depth < 2) {
    for (const key of OBJECT_TEXT_KEYS) {
      const candidate = coerceText((value as Record<string, unknown>)[key], depth + 1);
      if (candidate) {
        return candidate;
      }
    }
  }

  return null;
}

function extractPreviewText(source: EvidenceSourceRead): { label: string; text: string } | null {
  for (const [key, label] of INLINE_PREVIEW_KEYS) {
    const candidate = coerceText(source.metadata_json[key]);
    if (candidate) {
      return { label, text: candidate };
    }
  }

  return null;
}

function formatSpanLabel(link: EvidenceLinkRead): string {
  const start = typeof link.source_span_start === "number" ? link.source_span_start : null;
  const end = typeof link.source_span_end === "number" ? link.source_span_end : null;
  const scope = link.source_chunk_id ? "Chunk" : "Source";

  if (start !== null && end !== null) {
    return `${scope} chars ${start}-${end}`;
  }

  if (start !== null) {
    return `${scope} char ${start}+`;
  }

  if (link.source_chunk_id) {
    return `Chunk ${link.source_chunk_id.slice(0, 8)}`;
  }

  return "Full source";
}

function buildFallbackPreview(text: string): { displayText: string; segments: EvidencePreviewSegment[] } {
  if (text.length <= FALLBACK_PREVIEW_LENGTH) {
    return {
      displayText: text,
      segments: [{ emphasized: false, text }],
    };
  }

  const displayText = `${text.slice(0, FALLBACK_PREVIEW_LENGTH).trimEnd()}...`;
  return {
    displayText,
    segments: [{ emphasized: false, text: displayText }],
  };
}

export function buildEvidencePreview(
  evidenceLink: EvidenceLinkRead,
  evidenceSource: EvidenceSourceRead,
  sourceChunk?: EvidenceChunkRead | null,
): EvidencePreview {
  if (sourceChunk) {
    const spanLabel = sourceChunk.section_label
      ? `${sourceChunk.section_label} · chars ${sourceChunk.char_start}-${sourceChunk.char_end}`
      : `Chunk ${sourceChunk.chunk_no} · chars ${sourceChunk.char_start}-${sourceChunk.char_end}`;
    const chunkSourceLabel = sourceChunk.section_label ?? `Chunk ${sourceChunk.chunk_no}`;
    const start =
      typeof evidenceLink.source_span_start === "number" && evidenceLink.source_span_start >= 0
        ? evidenceLink.source_span_start
        : null;
    const end =
      typeof evidenceLink.source_span_end === "number" && evidenceLink.source_span_end >= 0
        ? evidenceLink.source_span_end
        : null;

    if (start === null || end === null || start >= sourceChunk.text.length) {
      const fallback = buildFallbackPreview(sourceChunk.text);
      return {
        displayText: fallback.displayText,
        highlightText: null,
        segments: fallback.segments,
        sourceLabel: chunkSourceLabel,
        spanLabel,
      };
    }

    const clampedEnd = Math.min(Math.max(end, start), sourceChunk.text.length);
    if (clampedEnd <= start) {
      const fallback = buildFallbackPreview(sourceChunk.text);
      return {
        displayText: fallback.displayText,
        highlightText: null,
        segments: fallback.segments,
        sourceLabel: chunkSourceLabel,
        spanLabel,
      };
    }

    const windowStart = Math.max(0, start - WINDOW_BEFORE);
    const windowEnd = Math.min(sourceChunk.text.length, clampedEnd + WINDOW_AFTER);
    const prefix = windowStart > 0 ? "..." : "";
    const suffix = windowEnd < sourceChunk.text.length ? "..." : "";
    const before = sourceChunk.text.slice(windowStart, start);
    const highlight = sourceChunk.text.slice(start, clampedEnd);
    const after = sourceChunk.text.slice(clampedEnd, windowEnd);
    const segments = [
      { emphasized: false, text: `${prefix}${before}` },
      { emphasized: true, text: highlight },
      { emphasized: false, text: `${after}${suffix}` },
    ].filter((segment) => segment.text.length > 0);

    return {
      displayText: segments.map((segment) => segment.text).join(""),
      highlightText: highlight,
      segments,
      sourceLabel: chunkSourceLabel,
      spanLabel,
    };
  }

  const preview = extractPreviewText(evidenceSource);
  const spanLabel = formatSpanLabel(evidenceLink);

  if (!preview) {
    return {
      displayText: null,
      highlightText: null,
      segments: [],
      sourceLabel: null,
      spanLabel,
    };
  }

  const start =
    typeof evidenceLink.source_span_start === "number" && evidenceLink.source_span_start >= 0
      ? evidenceLink.source_span_start
      : null;
  const end =
    typeof evidenceLink.source_span_end === "number" && evidenceLink.source_span_end >= 0
      ? evidenceLink.source_span_end
      : null;

  if (start === null || end === null || start >= preview.text.length) {
    const fallback = buildFallbackPreview(preview.text);
    return {
      displayText: fallback.displayText,
      highlightText: null,
      segments: fallback.segments,
      sourceLabel: preview.label,
      spanLabel,
    };
  }

  const clampedEnd = Math.min(Math.max(end, start), preview.text.length);
  if (clampedEnd <= start) {
    const fallback = buildFallbackPreview(preview.text);
    return {
      displayText: fallback.displayText,
      highlightText: null,
      segments: fallback.segments,
      sourceLabel: preview.label,
      spanLabel,
    };
  }

  const windowStart = Math.max(0, start - WINDOW_BEFORE);
  const windowEnd = Math.min(preview.text.length, clampedEnd + WINDOW_AFTER);
  const prefix = windowStart > 0 ? "..." : "";
  const suffix = windowEnd < preview.text.length ? "..." : "";
  const before = preview.text.slice(windowStart, start);
  const highlight = preview.text.slice(start, clampedEnd);
  const after = preview.text.slice(clampedEnd, windowEnd);
  const segments = [
    { emphasized: false, text: `${prefix}${before}` },
    { emphasized: true, text: highlight },
    { emphasized: false, text: `${after}${suffix}` },
  ].filter((segment) => segment.text.length > 0);

  return {
    displayText: segments.map((segment) => segment.text).join(""),
    highlightText: highlight,
    segments,
    sourceLabel: preview.label,
    spanLabel,
  };
}

export function summarizeEvidencePreview(preview: EvidencePreview, maxLength = 140): string | null {
  const candidate = preview.highlightText ?? preview.displayText;
  if (!candidate) {
    return null;
  }

  if (candidate.length <= maxLength) {
    return candidate;
  }

  return `${candidate.slice(0, maxLength).trimEnd()}...`;
}
