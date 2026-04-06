import { describe, expect, it } from "vitest";

import type {
  EvidenceChunkRead,
  EvidenceLinkRead,
  EvidenceSourceRead,
} from "@/lib/api/generated/control-plane";
import { buildEvidencePreview, summarizeEvidencePreview } from "@/features/evidence/evidence-preview";

function makeEvidenceSource(metadataJson: Record<string, unknown>): EvidenceSourceRead {
  return {
    cached_at: "2026-04-06T00:00:00Z",
    external_id_norm: "PMID:12345678",
    id: "src_123",
    license_class: "public",
    metadata_json: metadataJson,
    oa_subset_flag: false,
    source_type: "manual",
    title: "Evidence Source",
  };
}

function makeEvidenceLink(overrides: Partial<EvidenceLinkRead> = {}): EvidenceLinkRead {
  return {
    assertion_id: "ast_123",
    confidence: 0.9,
    created_at: "2026-04-06T00:00:00Z",
    evidence_source_id: "src_123",
    excerpt_hash: null,
    id: "lnk_123",
    project_id: "proj_123",
    relation_type: "supports",
    source_chunk_id: null,
    source_span_end: null,
    source_span_start: null,
    tenant_id: "ten_123",
    verifier_status: "pending",
    ...overrides,
  };
}

function makeEvidenceChunk(overrides: Partial<EvidenceChunkRead> = {}): EvidenceChunkRead {
  return {
    char_end: 54,
    char_start: 0,
    chunk_no: 0,
    created_at: "2026-04-06T00:00:00Z",
    evidence_source_id: "src_123",
    id: "chk_123",
    section_label: "abstract",
    text: "Chunk-native preview text for evidence-link highlighting.",
    token_count: 6,
    ...overrides,
  };
}

describe("buildEvidencePreview", () => {
  it("prefers source chunk text over metadata preview text when available", () => {
    const chunkText = "Chunk-native preview text for evidence-link highlighting.";
    const highlight = "evidence-link";
    const start = chunkText.indexOf(highlight);
    const end = start + highlight.length;

    const preview = buildEvidencePreview(
      makeEvidenceLink({ source_span_end: end, source_span_start: start }),
      makeEvidenceSource({ preview_text: "fallback metadata preview" }),
      makeEvidenceChunk({ text: chunkText }),
    );

    expect(preview.sourceLabel).toBe("abstract");
    expect(preview.highlightText).toBe(highlight);
    expect(preview.displayText).toContain(chunkText.slice(0, start));
  });

  it("extracts preview_text and highlights the configured span", () => {
    const previewText = "The marker improved overall survival in the validation cohort.";
    const highlight = "improved overall survival";
    const start = previewText.indexOf(highlight);
    const end = start + highlight.length;

    const preview = buildEvidencePreview(
      makeEvidenceLink({ source_span_end: end, source_span_start: start }),
      makeEvidenceSource({ preview_text: previewText }),
    );

    expect(preview.sourceLabel).toBe("Preview text");
    expect(preview.highlightText).toBe(highlight);
    expect(preview.displayText).toContain(highlight);
    expect(preview.segments.some((segment) => segment.emphasized && segment.text === highlight)).toBe(true);
    expect(preview.spanLabel).toBe(`Source chars ${start}-${end}`);
  });

  it("falls back to nested abstract metadata when preview_text is absent", () => {
    const preview = buildEvidencePreview(
      makeEvidenceLink(),
      makeEvidenceSource({
        abstract: {
          text: "Nested abstract text for manual evidence sources.",
        },
      }),
    );

    expect(preview.sourceLabel).toBe("Abstract");
    expect(preview.highlightText).toBeNull();
    expect(preview.displayText).toBe("Nested abstract text for manual evidence sources.");
  });

  it("clips long previews around the highlighted span", () => {
    const before = "A".repeat(120);
    const highlight = "hazard ratio improved";
    const after = "B".repeat(140);
    const previewText = `${before}${highlight}${after}`;
    const start = before.length;
    const end = start + highlight.length;

    const preview = buildEvidencePreview(
      makeEvidenceLink({ source_span_end: end, source_span_start: start }),
      makeEvidenceSource({ preview_text: previewText }),
    );

    expect(preview.displayText?.startsWith("...")).toBe(true);
    expect(preview.displayText?.endsWith("...")).toBe(true);
    expect(preview.highlightText).toBe(highlight);
    expect(summarizeEvidencePreview(preview, 16)).toBe("hazard ratio imp...");
  });
});
