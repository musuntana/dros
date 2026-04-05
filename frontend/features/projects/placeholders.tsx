import { EmptyState } from "@/components/status/empty-state";
import { titleFromSegment } from "@/lib/format/text";

export function ProjectSectionPlaceholder({
  projectId,
  segment,
}: {
  projectId: string;
  segment: string;
}) {
  const title = titleFromSegment(segment);

  return (
    <EmptyState
      title={`${title} surface is scaffolded`}
      description={`The ${title} route already sits inside the project-scoped workspace shell. Next phase can connect Control Plane reads and mutations without changing navigation or layout boundaries.`}
      actionHref={`/projects/${projectId}`}
      actionLabel="Back to overview"
    />
  );
}

export function ProjectDetailPlaceholder({
  projectId,
  objectLabel,
  objectId,
}: {
  projectId: string;
  objectLabel: string;
  objectId: string;
}) {
  return (
    <EmptyState
      title={`${objectLabel} detail is reserved`}
      description={`Detail route for ${objectLabel.toLowerCase()} ${objectId} already exists inside the project workspace. Next phase can attach truth, lineage, and next-action panels without changing the route contract.`}
      actionHref={`/projects/${projectId}`}
      actionLabel="Back to overview"
    />
  );
}
