import { mkdir, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

export async function uploadSignedBuffer(
  uploadUrl: string,
  buffer: Buffer,
  contentType: string,
): Promise<void> {
  if (uploadUrl.startsWith("file://")) {
    const uploadPath = fileURLToPath(uploadUrl);
    await mkdir(dirname(uploadPath), { recursive: true });
    await writeFile(uploadPath, buffer);
    return;
  }

  const response = await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "Content-Type": contentType || "application/octet-stream",
    },
    body: new Uint8Array(buffer),
  });
  if (!response.ok) {
    throw new Error(`Signed upload failed with ${response.status} ${response.statusText}`);
  }
}
