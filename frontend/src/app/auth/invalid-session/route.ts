import { NextResponse } from "next/server";

import { SESSION_COOKIE_NAMES } from "@/lib/session/cookies";

export function GET(): NextResponse {
  const response = new NextResponse(null, {
    status: 307,
    headers: { Location: "/login?sessionInvalid=1" },
  });
  for (const cookieName of SESSION_COOKIE_NAMES) {
    response.cookies.delete(cookieName);
  }
  return response;
}
