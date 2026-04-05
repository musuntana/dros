import { createHash, randomUUID } from "node:crypto";
import { readFile } from "node:fs/promises";

import { expect, test, type APIRequestContext } from "@playwright/test";

const AUTH_TENANT_ID = "00000000-0000-0000-0000-000000000901";
const AUTH_ACTOR_ID = "00000000-0000-0000-0000-000000000902";
const AUTH_HEADERS = {
  "X-Dros-Actor-Id": AUTH_ACTOR_ID,
  "X-Dros-Project-Role": "owner",
  "X-Dros-Scopes":
    "projects:read,projects:write,members:write,datasets:read,datasets:write,workflows:read,workflows:write,artifacts:read,artifacts:write,assertions:read,assertions:write,evidence:read,evidence:write,manuscripts:read,manuscripts:write,reviews:read,reviews:write,exports:read,exports:write,uploads:write,events:read,downloads:read,audit:read",
  "X-Dros-Tenant-Id": AUTH_TENANT_ID,
};

async function createProject(api: APIRequestContext) {
  const ownerId = AUTH_ACTOR_ID;
  const response = await api.post("http://127.0.0.1:8000/v1/projects", {
    data: {
      name: `Playwright Project ${randomUUID().slice(0, 8)}`,
      project_type: "public_omics",
      compliance_level: "public",
      owner_id: ownerId,
    },
    headers: AUTH_HEADERS,
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as {
    project: { id: string; name: string };
  };
}

test("project workspace supports real upload registration and artifact download", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop happy path is covered in chromium");

  const createdProject = await createProject(request);
  const uploadBytes = Buffer.from("gene,value\nEGFR,1\nKRAS,0\n", "utf-8");
  const sha256 = createHash("sha256").update(uploadBytes).digest("hex");

  await page.goto("/projects");
  await expect(page.getByRole("link", { name: createdProject.project.name })).toBeVisible();

  await page.goto(`/projects/${createdProject.project.id}/datasets`);
  await page.getByTestId("dataset-upload-input").setInputFiles({
    buffer: uploadBytes,
    mimeType: "text/csv",
    name: "playwright-upload.csv",
  });
  await page.getByTestId("dataset-upload-submit").click();
  await page.waitForURL(new RegExp(`/projects/${createdProject.project.id}/datasets/[^/]+$`));

  const sourceRef = (await page.getByTestId("dataset-source-ref").textContent())?.trim();
  expect(sourceRef).toBeTruthy();

  const artifactResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/artifacts`, {
    data: {
      artifact_type: "log",
      storage_uri: `object://${sourceRef}`,
      mime_type: "text/csv",
      sha256,
      size_bytes: uploadBytes.length,
      metadata_json: {
        source: "playwright-upload",
      },
    },
    headers: AUTH_HEADERS,
  });
  expect(artifactResponse.ok()).toBeTruthy();
  const artifactPayload = (await artifactResponse.json()) as {
    artifact: { id: string };
  };

  await page.goto(`/projects/${createdProject.project.id}/artifacts/${artifactPayload.artifact.id}`);
  const downloadPromise = page.waitForEvent("download");
  await page.getByTestId("artifact-download-link").click();
  const download = await downloadPromise;
  const downloadPath = await download.path();
  expect(downloadPath).toBeTruthy();
  expect(await readFile(downloadPath ?? "")).toEqual(uploadBytes);
  await expect(page.getByText("Download artifact payload")).toBeVisible();
});

test("workspace streams workflow events through the browser gateway path", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "realtime flow is covered in chromium");

  const createdProject = await createProject(request);

  await page.goto(`/projects/${createdProject.project.id}`);
  const eventsFeed = page.getByTestId("workspace-live-events");
  await expect(eventsFeed.getByText("project.created")).toBeVisible();

  const workflowResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/workflows`, {
    data: {
      workflow_type: "public_dataset_standard_analysis",
      runtime_backend: "queue_workers",
    },
    headers: AUTH_HEADERS,
  });
  expect(workflowResponse.ok()).toBeTruthy();
  const workflowPayload = (await workflowResponse.json()) as {
    workflow: { id: string };
  };

  await expect(eventsFeed.getByText("workflow.started")).toBeVisible();
  await page.getByTestId("workspace-live-event:workflow.started").click({ force: true });

  const inspector = page.getByTestId("workspace-inspector");
  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("workflow.started");
  await expect(inspector.getByRole("link", { name: "Workflow" })).toHaveAttribute(
    "href",
    `/projects/${createdProject.project.id}/workflows/${workflowPayload.workflow.id}`,
  );
});

test("workspace inspector collapses on mobile and reveals session context", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium", "mobile workspace checks run in the mobile project");

  const createdProject = await createProject(request);

  await page.goto(`/projects/${createdProject.project.id}`);
  await expect(page.getByTestId("object-rail")).toBeVisible();
  await expect(page.getByTestId("workspace-inspector-toggle")).toBeVisible();
  await expect(page.getByTestId("workspace-inspector").getByText(AUTH_TENANT_ID)).not.toBeVisible();

  await page.getByTestId("workspace-inspector-toggle").click({ force: true });
  const inspector = page.getByTestId("workspace-inspector");
  await expect(inspector.getByText(AUTH_TENANT_ID)).toBeVisible();
  await expect(inspector.getByText(AUTH_ACTOR_ID, { exact: true })).toBeVisible();
  await expect(inspector.getByText("owner", { exact: true })).toBeVisible();

  await page.getByTestId("workspace-inspector-toggle").click({ force: true });
  await expect(inspector.getByText(AUTH_TENANT_ID)).not.toBeVisible();

  const workflowResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/workflows`, {
    data: {
      workflow_type: "public_dataset_standard_analysis",
      runtime_backend: "queue_workers",
    },
    headers: AUTH_HEADERS,
  });
  expect(workflowResponse.ok()).toBeTruthy();

  await expect(page.getByTestId("workspace-live-event:workflow.started")).toBeVisible();
  await page.getByTestId("workspace-live-event:workflow.started").click({ force: true });
  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("workflow.started");
});
