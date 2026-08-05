import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const requestHost = request.headers.get("host")?.split(":")[0];
  if (requestHost !== "127.0.0.1") {
    return NextResponse.next();
  }

  // OAuth callback URLs and local session cookies use localhost. Keep one
  // canonical browser origin so authentication and credentialed API requests
  // do not cross the localhost/127.0.0.1 site boundary.
  const canonicalUrl = request.nextUrl.clone();
  canonicalUrl.hostname = "localhost";
  return NextResponse.redirect(canonicalUrl);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|icon.svg|og.png).*)"],
};
