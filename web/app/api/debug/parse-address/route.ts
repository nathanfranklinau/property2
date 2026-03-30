import { NextRequest, NextResponse } from "next/server";

const PYTHON_SERVICE = process.env.PYTHON_SERVICE_URL ?? "http://localhost:8001";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const res = await fetch(`${PYTHON_SERVICE}/parse-address`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
