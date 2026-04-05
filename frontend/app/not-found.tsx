import { EmptyState } from "@/components/status/empty-state";

export default function NotFound() {
  return (
    <EmptyState
      title="Object not found"
      description="The requested project-scoped resource does not exist in the current workspace view."
      actionHref="/projects"
      actionLabel="Back to projects"
    />
  );
}
