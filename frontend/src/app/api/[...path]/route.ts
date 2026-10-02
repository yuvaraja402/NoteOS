import { NextRequest } from "next/server";

const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const target = `${API_INTERNAL_URL}/${path.join("/")}${request.nextUrl.search}`;
  const body = ["GET", "HEAD"].includes(request.method)
    ? undefined
    : await request.text();

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      body,
      headers: {
        "Content-Type": request.headers.get("Content-Type") ?? "application/json",
        Cookie: request.headers.get("Cookie") ?? "",
        ...(request.headers.get("Origin") ? { Origin: request.headers.get("Origin")! } : {}),
      },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
  } catch {
    return Response.json({ detail: "Cloud sync is unavailable." }, {
      status: 503, headers: { "Cache-Control": "no-store" },
    });
  }

  const headers = new Headers({ "Cache-Control": "no-store" });
  const contentType = upstream.headers.get("Content-Type");
  if (contentType) headers.set("Content-Type", contentType);
  const revision = upstream.headers.get("X-NoteOS-Revision");
  if (revision) headers.set("X-NoteOS-Revision", revision);
  for (const cookie of upstream.headers.getSetCookie()) headers.append("Set-Cookie", cookie);
  return new Response(upstream.body, { status: upstream.status, headers });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
