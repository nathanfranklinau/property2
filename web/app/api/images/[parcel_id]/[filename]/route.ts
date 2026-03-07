/**
 * GET /api/images/[parcel_id]/[filename]
 *
 * Proxies property analysis images from the local filesystem.
 * Images are written by the Python analysis service to IMAGES_DIR.
 *
 * Only serves the four known filenames to prevent path traversal.
 */

import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";

const ALLOWED = new Set([
  "roadmap.png",
  "satellite.png",
  "markup.png",
  "mask.png",
  "mask2.png",
  "satellite_masked.jpg",
  "street_view.jpg",
]);
const IMAGES_DIR = process.env.IMAGES_DIR ?? "";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ parcel_id: string; filename: string }> }
) {
  const { parcel_id, filename } = await params;

  if (!ALLOWED.has(filename)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  // Validate parcel_id is a UUID (no path traversal)
  if (!/^[0-9a-f-]{36}$/.test(parcel_id)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  if (!IMAGES_DIR) {
    return NextResponse.json({ error: "IMAGES_DIR not configured" }, { status: 500 });
  }

  const filePath = path.join(IMAGES_DIR, parcel_id, filename);

  const contentType = filename.endsWith(".jpg") ? "image/jpeg" : "image/png";

  try {
    const data = await readFile(filePath);
    return new NextResponse(data, {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=86400, immutable",
      },
    });
  } catch {
    return NextResponse.json({ error: "Image not found" }, { status: 404 });
  }
}
