import type { AssertionRead, EvidenceLinkRead, EvidenceSourceRead } from "@/lib/api/generated/control-plane";

export interface EvidenceLinkRecord {
  assertion: AssertionRead;
  link: EvidenceLinkRead;
  source: EvidenceSourceRead | null;
}
