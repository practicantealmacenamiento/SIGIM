import { NextResponse, NextRequest } from "next/server";

const PUBLIC_FILE = /\.(.*)$/;

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;

  // Permitir estáticos y API
  if (
    pathname.startsWith("/api") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/static") ||
    PUBLIC_FILE.test(pathname)
  ) {
    return NextResponse.next();
  }

  // Cookies que colocan DRF y nuestro front
  const hasSession = Boolean(req.cookies.get("sessionid")?.value);
  const hasToken = Boolean(req.cookies.get("auth_token")?.value);
  const isLogged = hasSession || hasToken;

  // /login es público; si ya hay sesión, redirige al home
  if (pathname === "/login") {
    if (isLogged) {
      const url = req.nextUrl.clone();
      url.pathname = "/";
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  // Si no hay sesión/token, manda a /login preservando next
  if (!isLogged) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(pathname + (search || ""))}`;
    return NextResponse.redirect(url);
  }

  // Guardado rápido para rutas admin (comodidad visual; la seguridad real ya la hace el backend)
  if (pathname.startsWith("/admin")) {
    const isStaff = req.cookies.get("is_staff")?.value === "1";
    if (!isStaff) {
      const url = req.nextUrl.clone();
      url.pathname = "/";
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next();
}

export const config = {
  // Evita correr en /api y en assets; el resto pasa por el middleware
  matcher: ["/((?!api|_next|static|assets|favicon.ico|robots.txt|sitemap.xml).*)"],
};
