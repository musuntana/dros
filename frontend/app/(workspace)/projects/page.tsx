import { ErrorCard } from "@/components/status/error-card";
import { EmptyState } from "@/components/status/empty-state";
import { ProjectList } from "@/features/projects/project-list";
import { getProjectsIndex } from "@/features/projects/server";

export default async function ProjectsPage() {
  try {
    const response = await getProjectsIndex();
    const projects = response.items.items;

    return (
      <div className="space-y-6">
        <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Projects</p>
          <h1 className="mt-3 font-serif text-4xl text-strong">Research Canvas entry point</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
            This surface only binds to Control Plane REST and keeps the workspace boundary at project scope. Gateway-only
            concerns such as session, signed upload, realtime events, and artifact download stay behind adapter
            interfaces.
          </p>
        </section>

        {projects.length > 0 ? (
          <ProjectList projects={projects} />
        ) : (
          <EmptyState
            title="No projects in the workspace"
            description="Create a project through the control plane before datasets, workflows, assertions, and manuscripts can enter the project-scoped shell."
          />
        )}
      </div>
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} />;
  }
}
