import { NextResponse, NextRequest } from "next/server";

const PUBLIC_PATHS = ["/admin/login", "/public"];

function hasAuth(req: NextRequest) {
  const session = req.cookies.get("sessionid")?.value;
  const token = req.cookies.get("auth_token")?.value;
  return Boolean(session || token);
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) return NextResponse.next();

  if (!hasAuth(req)) {
    const loginUrl = req.nextUrl.clone();
    loginUrl.pathname = "/admin/login";
    loginUrl.search = `?next=${encodeURIComponent(pathname)}`;
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    // Protege todo menos las rutas públicas y estáticos:
    "/((?!api|_next|static|assets|favicon.ico|robots.txt|sitemap.xml|admin/login).*)",
  ],
};
