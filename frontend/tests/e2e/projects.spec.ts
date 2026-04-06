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

async function createVerifiedManuscriptChain(
  api: APIRequestContext,
  projectId: string,
  title: string,
) {
  const sha256 = createHash("sha256").update(`${title}:${randomUUID()}`).digest("hex");
  const manuscriptResponse = await api.post(`http://127.0.0.1:8000/v1/projects/${projectId}/manuscripts`, {
    data: {
      manuscript_type: "manuscript",
      style_profile_json: {},
      title,
    },
    headers: AUTH_HEADERS,
  });
  expect(manuscriptResponse.ok()).toBeTruthy();
  const manuscriptPayload = (await manuscriptResponse.json()) as {
    manuscript: { id: string };
  };

  const artifactResponse = await api.post(`http://127.0.0.1:8000/v1/projects/${projectId}/artifacts`, {
    data: {
      artifact_type: "result_json",
      storage_uri: `object://artifacts/${manuscriptPayload.manuscript.id}/result.json`,
      sha256,
      metadata_json: {
        kind: "playwright_export_chain",
      },
    },
    headers: AUTH_HEADERS,
  });
  expect(artifactResponse.ok()).toBeTruthy();
  const artifactPayload = (await artifactResponse.json()) as {
    artifact: { id: string };
  };

  const assertionResponse = await api.post(`http://127.0.0.1:8000/v1/projects/${projectId}/assertions`, {
    data: {
      assertion_type: "result",
      claim_hash: sha256,
      numeric_payload_json: {},
      source_artifact_id: artifactPayload.artifact.id,
      source_span_json: {
        path: "playwright_export_chain",
      },
      text_norm: `${title} assertion`,
    },
    headers: AUTH_HEADERS,
  });
  expect(assertionResponse.ok()).toBeTruthy();
  const assertionPayload = (await assertionResponse.json()) as {
    assertion: { id: string };
  };

  const verifyAssertionResponse = await api.post(`http://127.0.0.1:8000/v1/projects/${projectId}/verify`, {
    data: {
      target_ids: [assertionPayload.assertion.id],
    },
    headers: AUTH_HEADERS,
  });
  expect(verifyAssertionResponse.ok()).toBeTruthy();

  const blockResponse = await api.post(
    `http://127.0.0.1:8000/v1/projects/${projectId}/manuscripts/${manuscriptPayload.manuscript.id}/blocks`,
    {
      data: {
        section_key: "results",
        block_order: 0,
        block_type: "text",
        content_md: `${title} block`,
        assertion_ids: [assertionPayload.assertion.id],
      },
      headers: AUTH_HEADERS,
    },
  );
  expect(blockResponse.ok()).toBeTruthy();

  const verifyResponse = await api.post(`http://127.0.0.1:8000/v1/projects/${projectId}/verify`, {
    data: {
      manuscript_id: manuscriptPayload.manuscript.id,
      target_ids: [],
    },
    headers: AUTH_HEADERS,
  });
  expect(verifyResponse.ok()).toBeTruthy();

  return {
    artifactId: artifactPayload.artifact.id,
    assertionId: assertionPayload.assertion.id,
    manuscriptId: manuscriptPayload.manuscript.id,
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
  const inspector = page.getByTestId("workspace-inspector");
  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("Artifact log");
  await expect(inspector.getByText("No assertion currently cites this artifact.")).toBeVisible();

  const assertionResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/assertions`, {
    data: {
      assertion_type: "result",
      claim_hash: sha256,
      numeric_payload_json: {},
      source_artifact_id: artifactPayload.artifact.id,
      source_span_json: {
        column: "value",
      },
      text_norm: "playwright artifact assertion",
    },
    headers: AUTH_HEADERS,
  });
  expect(assertionResponse.ok()).toBeTruthy();
  const assertionPayload = (await assertionResponse.json()) as {
    assertion: { id: string };
  };

  await expect(inspector.getByRole("link", { name: `Assertion ${assertionPayload.assertion.id.slice(0, 8)}` })).toHaveAttribute(
    "href",
    `/projects/${createdProject.project.id}/assertions/${assertionPayload.assertion.id}`,
  );
  await expect(
    page.getByTestId("artifact-lineage-graph").getByRole("link", {
      name: `Assertion ${assertionPayload.assertion.id.slice(0, 8)}`,
    }),
  ).toHaveAttribute("href", `/projects/${createdProject.project.id}/assertions/${assertionPayload.assertion.id}`);

  await page.getByTestId("workspace-stage:analysis").click({ force: true });
  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("Analysis Run");
  await page.getByTestId("workspace-inspector-reset").click({ force: true });
  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("Artifact log");

  const downloadPromise = page.waitForEvent("download");
  await page.getByTestId("artifact-download-link").click();
  const download = await downloadPromise;
  const downloadPath = await download.path();
  expect(downloadPath).toBeTruthy();
  expect(await readFile(downloadPath ?? "")).toEqual(uploadBytes);
  await expect(page.getByText("Download artifact payload")).toBeVisible();
});

test("export detail route and artifact lineage graph stay wired to workspace inspector", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop export chain coverage runs in chromium");

  const createdProject = await createProject(request);
  const chain = await createVerifiedManuscriptChain(request, createdProject.project.id, "Export Detail Focus");

  await page.goto(`/projects/${createdProject.project.id}/exports`);
  await Promise.all([
    page.waitForURL(new RegExp(`/projects/${createdProject.project.id}/exports/[^/]+$`)),
    page.getByRole("button", { name: "Create export job" }).click(),
  ]);

  const exportJobId = page.url().split("/").pop() ?? "";
  expect(exportJobId).not.toBe("");

  const inspector = page.getByTestId("workspace-inspector");
  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("Export Job");
  await expect(inspector.getByRole("link", { name: "Open manuscript" })).toHaveAttribute(
    "href",
    `/projects/${createdProject.project.id}/manuscripts/${chain.manuscriptId}`,
  );

  const outputArtifactLink = page.getByRole("main").getByRole("link", { name: "Open output artifact" });
  await expect(outputArtifactLink).toHaveAttribute(
    "href",
    new RegExp(`/projects/${createdProject.project.id}/artifacts/[^/]+$`),
  );
  await outputArtifactLink.click();

  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("Artifact docx");
  await expect(inspector.getByRole("link", { name: `Export ${exportJobId.slice(0, 8)}` })).toHaveAttribute(
    "href",
    `/projects/${createdProject.project.id}/exports/${exportJobId}`,
  );

  const lineageGraph = page.getByTestId("artifact-lineage-graph");
  await expect(lineageGraph).toContainText("Canonical object adjacency");
  await expect(lineageGraph.getByRole("link", { name: `Export ${exportJobId.slice(0, 8)}` })).toHaveAttribute(
    "href",
    `/projects/${createdProject.project.id}/exports/${exportJobId}`,
  );
  await expect(lineageGraph.getByRole("link", { name: "Export Detail Focus" })).toHaveAttribute(
    "href",
    `/projects/${createdProject.project.id}/manuscripts/${chain.manuscriptId}`,
  );
});

test("artifact lineage graph can open evidence link detail routes", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop evidence graph coverage runs in chromium");

  const createdProject = await createProject(request);
  const assertionHash = createHash("sha256").update(`evidence-link:${randomUUID()}`).digest("hex");
  const previewText = "The marker improved overall survival in the validation cohort.";
  const highlightedSpan = "improved overall survival";
  const sourceSpanStart = previewText.indexOf(highlightedSpan);
  const sourceSpanEnd = sourceSpanStart + highlightedSpan.length;

  const artifactResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/artifacts`, {
    data: {
      artifact_type: "result_json",
      storage_uri: "object://artifacts/evidence-link/result.json",
      sha256: assertionHash,
      metadata_json: {
        kind: "evidence_link_graph",
      },
    },
    headers: AUTH_HEADERS,
  });
  expect(artifactResponse.ok()).toBeTruthy();
  const artifactPayload = (await artifactResponse.json()) as {
    artifact: { id: string };
  };

  const assertionResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/assertions`, {
    data: {
      assertion_type: "result",
      claim_hash: assertionHash,
      numeric_payload_json: {},
      source_artifact_id: artifactPayload.artifact.id,
      source_span_json: {
        path: "evidence_link_graph",
      },
      text_norm: "artifact evidence link assertion",
    },
    headers: AUTH_HEADERS,
  });
  expect(assertionResponse.ok()).toBeTruthy();
  const assertionPayload = (await assertionResponse.json()) as {
    assertion: { id: string };
  };

  const evidenceSourceResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/evidence`, {
    data: {
      source_type: "manual",
      external_id_norm: `PMID:${randomUUID().slice(0, 8)}`,
      title: "Artifact Link Evidence Source",
      license_class: "public",
      metadata_json: {
        kind: "artifact_link_graph",
        preview_text: previewText,
      },
      oa_subset_flag: false,
    },
    headers: AUTH_HEADERS,
  });
  expect(evidenceSourceResponse.ok()).toBeTruthy();
  const evidenceSourcePayload = (await evidenceSourceResponse.json()) as {
    evidence_source: { id: string };
  };

  const evidenceLinkResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/evidence-links`, {
    data: {
      assertion_id: assertionPayload.assertion.id,
      confidence: 0.87,
      evidence_source_id: evidenceSourcePayload.evidence_source.id,
      relation_type: "supports",
      source_span_end: sourceSpanEnd,
      source_span_start: sourceSpanStart,
    },
    headers: AUTH_HEADERS,
  });
  expect(evidenceLinkResponse.ok()).toBeTruthy();
  const evidenceLinkPayload = (await evidenceLinkResponse.json()) as {
    evidence_link: { id: string };
  };

  await page.goto(`/projects/${createdProject.project.id}/artifacts/${artifactPayload.artifact.id}`);
  const lineageGraph = page.getByTestId("artifact-lineage-graph");
  const evidenceLinkAnchor = lineageGraph.getByRole("link", {
    name: `supports ${evidenceLinkPayload.evidence_link.id.slice(0, 8)}`,
  });
  await expect(evidenceLinkAnchor).toHaveAttribute(
    "href",
    `/projects/${createdProject.project.id}/evidence-links/${evidenceLinkPayload.evidence_link.id}`,
  );
  await evidenceLinkAnchor.click();

  await expect(page.getByTestId("workspace-inspector-focus-title")).toHaveText("Evidence Link");
  await expect(page.getByTestId("evidence-link-source-title")).toHaveText("Artifact Link Evidence Source");
  await expect(page.getByTestId("evidence-link-source-chunk")).toContainText("inline_preview");
  await expect(page.getByTestId("evidence-link-verify-submit")).toBeVisible();
  await expect(page.getByTestId("evidence-link-preview")).toContainText(previewText);
  await expect(page.getByTestId("evidence-link-highlight")).toHaveText(highlightedSpan);
  await expect(page.getByTestId("workspace-inspector")).toContainText(highlightedSpan);
  await expect(page.getByTestId("workspace-inspector").getByRole("link", { name: "Open assertion" })).toHaveAttribute(
    "href",
    `/projects/${createdProject.project.id}/assertions/${assertionPayload.assertion.id}`,
  );
});

test("workspace streams workflow events through the browser gateway path", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "realtime flow is covered in chromium");

  const createdProject = await createProject(request);

  await page.goto(`/projects/${createdProject.project.id}`);
  const timeline = page.getByTestId("workspace-stage-timeline");
  await expect(page.getByTestId("workspace-stage:intake")).toBeVisible();
  await page.getByTestId("workspace-stage:workflow").click({ force: true });

  const inspector = page.getByTestId("workspace-inspector");
  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("Workflow Planning");
  await expect(inspector.getByRole("link", { name: "Go to workflows" })).toHaveAttribute(
    "href",
    `/projects/${createdProject.project.id}/workflows`,
  );

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

  await expect(page.getByTestId("workspace-live-event:workflow.started")).toBeVisible();
  await page.getByTestId("workspace-stage:workflow").click({ force: true });
  await expect(inspector.getByRole("link", { name: "Open workflow" })).toHaveAttribute(
    "href",
    `/projects/${createdProject.project.id}/workflows/${workflowPayload.workflow.id}`,
  );
  await page.getByTestId("workspace-live-event:workflow.started").click({ force: true });
  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("workflow.started");
  await expect(inspector.getByRole("link", { name: "Workflow" })).toHaveAttribute(
    "href",
    `/projects/${createdProject.project.id}/workflows/${workflowPayload.workflow.id}`,
  );
});

test("review stage ignores stale manuscript reviews from earlier versions", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop workspace projection checks run in chromium");

  const createdProject = await createProject(request);
  const manuscriptResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/manuscripts`, {
    data: {
      manuscript_type: "manuscript",
      style_profile_json: {},
      title: "Projection Review Boundary",
    },
    headers: AUTH_HEADERS,
  });
  expect(manuscriptResponse.ok()).toBeTruthy();
  const manuscriptPayload = (await manuscriptResponse.json()) as {
    manuscript: { id: string };
  };

  const reviewResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/reviews`, {
    data: {
      review_type: "manuscript",
      target_id: manuscriptPayload.manuscript.id,
      target_kind: "manuscript",
      checklist_json: [],
    },
    headers: AUTH_HEADERS,
  });
  expect(reviewResponse.ok()).toBeTruthy();
  const reviewPayload = (await reviewResponse.json()) as {
    review: { id: string };
  };

  const rejectResponse = await request.post(
    `http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/reviews/${reviewPayload.review.id}/decisions`,
    {
      data: {
        action: "reject",
        comments: "old version reject",
      },
      headers: AUTH_HEADERS,
    },
  );
  expect(rejectResponse.ok()).toBeTruthy();

  const versionResponse = await request.post(
    `http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/manuscripts/${manuscriptPayload.manuscript.id}/versions`,
    {
      data: {
        base_version_no: 1,
        reason: "new draft after rejected review",
      },
      headers: AUTH_HEADERS,
    },
  );
  expect(versionResponse.ok()).toBeTruthy();

  await page.goto(`/projects/${createdProject.project.id}`);
  await page.getByTestId("workspace-stage:review").click({ force: true });
  const inspector = page.getByTestId("workspace-inspector");
  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("Review Gate");
  await expect(inspector.getByText("No review ticket is currently open.")).toBeVisible();
});

test("review stage ignores explicitly versioned historical manuscript reviews", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop workspace projection checks run in chromium");

  const createdProject = await createProject(request);
  const manuscriptResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/manuscripts`, {
    data: {
      manuscript_type: "manuscript",
      style_profile_json: {},
      title: "Explicit Historical Review Scope",
    },
    headers: AUTH_HEADERS,
  });
  expect(manuscriptResponse.ok()).toBeTruthy();
  const manuscriptPayload = (await manuscriptResponse.json()) as {
    manuscript: { id: string };
  };

  const versionResponse = await request.post(
    `http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/manuscripts/${manuscriptPayload.manuscript.id}/versions`,
    {
      data: {
        base_version_no: 1,
        reason: "advance to v2 before back-reviewing v1",
      },
      headers: AUTH_HEADERS,
    },
  );
  expect(versionResponse.ok()).toBeTruthy();

  const reviewResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/reviews`, {
    data: {
      review_type: "manuscript",
      target_id: manuscriptPayload.manuscript.id,
      target_kind: "manuscript",
      target_version_no: 1,
      checklist_json: [],
    },
    headers: AUTH_HEADERS,
  });
  expect(reviewResponse.ok()).toBeTruthy();

  await page.goto(`/projects/${createdProject.project.id}`);
  await page.getByTestId("workspace-stage:review").click({ force: true });
  const inspector = page.getByTestId("workspace-inspector");
  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("Review Gate");
  await expect(inspector.getByText("No review ticket is currently open.")).toBeVisible();
});

test("review stage keeps current-version reviews after later block creation", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop workspace projection checks run in chromium");

  const createdProject = await createProject(request);
  const sha256 = createHash("sha256").update("review-boundary-assertion").digest("hex");
  const manuscriptResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/manuscripts`, {
    data: {
      manuscript_type: "manuscript",
      style_profile_json: {},
      title: "Review Boundary Stability",
    },
    headers: AUTH_HEADERS,
  });
  expect(manuscriptResponse.ok()).toBeTruthy();
  const manuscriptPayload = (await manuscriptResponse.json()) as {
    manuscript: { id: string };
  };

  const reviewResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/reviews`, {
    data: {
      review_type: "manuscript",
      target_id: manuscriptPayload.manuscript.id,
      target_kind: "manuscript",
      checklist_json: [],
    },
    headers: AUTH_HEADERS,
  });
  expect(reviewResponse.ok()).toBeTruthy();

  const artifactResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/artifacts`, {
    data: {
      artifact_type: "result_json",
      storage_uri: "object://artifacts/review-boundary/result.json",
      sha256: sha256,
      metadata_json: {
        kind: "review_boundary",
      },
    },
    headers: AUTH_HEADERS,
  });
  expect(artifactResponse.ok()).toBeTruthy();
  const artifactPayload = (await artifactResponse.json()) as {
    artifact: { id: string };
  };

  const assertionResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/assertions`, {
    data: {
      assertion_type: "result",
      claim_hash: sha256,
      numeric_payload_json: {},
      source_artifact_id: artifactPayload.artifact.id,
      source_span_json: {
        path: "review_boundary",
      },
      text_norm: "review boundary assertion",
    },
    headers: AUTH_HEADERS,
  });
  expect(assertionResponse.ok()).toBeTruthy();
  const assertionPayload = (await assertionResponse.json()) as {
    assertion: { id: string };
  };

  const verifyResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/verify`, {
    data: {
      target_ids: [assertionPayload.assertion.id],
    },
    headers: AUTH_HEADERS,
  });
  expect(verifyResponse.ok()).toBeTruthy();

  const blockResponse = await request.post(
    `http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/manuscripts/${manuscriptPayload.manuscript.id}/blocks`,
    {
      data: {
        section_key: "results",
        block_order: 0,
        block_type: "text",
        content_md: "review boundary assertion",
        assertion_ids: [assertionPayload.assertion.id],
      },
      headers: AUTH_HEADERS,
    },
  );
  expect(blockResponse.ok()).toBeTruthy();

  await page.goto(`/projects/${createdProject.project.id}`);
  await page.getByTestId("workspace-stage:review").click({ force: true });
  const inspector = page.getByTestId("workspace-inspector");
  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("Review Gate");
  await expect(inspector.getByText("1 review(s) are still pending on the current manuscript chain.")).toBeVisible();
});

test("project overview review summary updates live across review and version changes", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop workspace projection checks run in chromium");

  const createdProject = await createProject(request);
  const manuscriptResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/manuscripts`, {
    data: {
      manuscript_type: "manuscript",
      style_profile_json: {},
      title: "Live Review Summary",
    },
    headers: AUTH_HEADERS,
  });
  expect(manuscriptResponse.ok()).toBeTruthy();
  const manuscriptPayload = (await manuscriptResponse.json()) as {
    manuscript: { id: string };
  };

  await page.goto(`/projects/${createdProject.project.id}`);
  await expect(page.getByTestId("project-header-review-summary")).toHaveText("No current-version reviews");
  await expect(page.getByTestId("project-header-review-scope")).toHaveText("Scoped to Live Review Summary v1.");
  await expect(page.getByTestId("project-overview-review-summary")).toHaveText(
    "No review state is recorded for Live Review Summary v1.",
  );

  const reviewResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/reviews`, {
    data: {
      review_type: "manuscript",
      target_id: manuscriptPayload.manuscript.id,
      target_kind: "manuscript",
      checklist_json: [],
    },
    headers: AUTH_HEADERS,
  });
  expect(reviewResponse.ok()).toBeTruthy();

  await expect(page.getByTestId("project-header-review-summary")).toHaveText("pending:1");
  await expect(page.getByTestId("project-overview-review-summary")).toHaveText("pending: 1");

  const versionResponse = await request.post(
    `http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/manuscripts/${manuscriptPayload.manuscript.id}/versions`,
    {
      data: {
        base_version_no: 1,
        reason: "advance to live v2",
      },
      headers: AUTH_HEADERS,
    },
  );
  expect(versionResponse.ok()).toBeTruthy();

  await expect(page.getByTestId("project-header-review-summary")).toHaveText("No current-version reviews");
  await expect(page.getByTestId("project-header-review-scope")).toHaveText("Scoped to Live Review Summary v2.");
  await expect(page.getByTestId("project-overview-review-summary")).toHaveText(
    "No review state is recorded for Live Review Summary v2.",
  );
});

test("reviews page queue updates live after review creation", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop workspace projection checks run in chromium");

  const createdProject = await createProject(request);
  const manuscriptResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/manuscripts`, {
    data: {
      manuscript_type: "manuscript",
      style_profile_json: {},
      title: "Live Reviews Queue",
    },
    headers: AUTH_HEADERS,
  });
  expect(manuscriptResponse.ok()).toBeTruthy();
  const manuscriptPayload = (await manuscriptResponse.json()) as {
    manuscript: { id: string };
  };

  await page.goto(`/projects/${createdProject.project.id}/reviews`);
  await expect(page.getByText("No review record exists yet.")).toBeVisible();

  const reviewResponse = await request.post(`http://127.0.0.1:8000/v1/projects/${createdProject.project.id}/reviews`, {
    data: {
      review_type: "manuscript",
      target_id: manuscriptPayload.manuscript.id,
      target_kind: "manuscript",
      checklist_json: [],
      comments: "live queue item",
    },
    headers: AUTH_HEADERS,
  });
  expect(reviewResponse.ok()).toBeTruthy();

  await expect(page.getByText("live queue item")).toBeVisible();
  await expect(page.getByText(manuscriptPayload.manuscript.id, { exact: true })).toBeVisible();
});

test("workspace inspector collapses on mobile and reveals session context", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium", "mobile workspace checks run in the mobile project");

  const createdProject = await createProject(request);

  await page.goto(`/projects/${createdProject.project.id}`);
  await expect(page.getByTestId("object-rail")).toBeVisible();
  await expect(page.getByTestId("workspace-stage-timeline")).toBeVisible();
  await expect(page.getByTestId("workspace-inspector-toggle")).toBeVisible();
  await expect(page.getByTestId("workspace-inspector").getByText(AUTH_TENANT_ID)).not.toBeVisible();

  await page.getByTestId("workspace-inspector-toggle").click({ force: true });
  const inspector = page.getByTestId("workspace-inspector");
  await expect(inspector.getByText(AUTH_TENANT_ID)).toBeVisible();
  await expect(inspector.getByText(AUTH_ACTOR_ID, { exact: true })).toBeVisible();
  await expect(inspector.getByText("owner", { exact: true })).toBeVisible();

  await page.getByTestId("workspace-inspector-toggle").click({ force: true });
  await expect(inspector.getByText(AUTH_TENANT_ID)).not.toBeVisible();

  await page.getByTestId("workspace-stage:workflow").click({ force: true });
  await expect(inspector.getByTestId("workspace-inspector-focus-title")).toHaveText("Workflow Planning");

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
