"use client";
import { useEffect } from "react";
import localFont from "next/font/local";
import "./globals.css";
import { Header } from "../../components/header/header";
import { ThemeProvider } from "next-themes";
import { installGlobalAuthFetch } from "@/lib/api.admin";

// Auth wrapper
import { AuthProvider } from "../../components/auth/authProvider";
import AuthGate from "../../components/auth/authGate";
// instala fetch con credenciales en el cliente
import ClientAuthBootstrap from "../../components/auth/clientAuthBootstrap";

const FFFAcid = localFont({ src: "./fonts/FFFAcidGroteskVariableTRIALVF.woff" });
const acidGroteskLight = localFont({ src: "./fonts/acid-grotesk-light.woff" });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    installGlobalAuthFetch();
  }, []);

  return (
    <html lang="es" suppressHydrationWarning className="scroll-smooth">
      <body
        className={`${acidGroteskLight.className} ${FFFAcid.className} antialiased min-h-screen selection:bg-sky-200 selection:text-slate-900 dark:selection:bg-skyBlue/40 dark:selection:text-bone text-[#202020] dark:text-bone bg-radial from-bone via-bone to-white dark:from-skyBlue dark:via-none dark:to-[#202020]`}
      >
        {/* Skip link para accesibilidad */}
        <a
          href="#content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[100] focus:px-4 focus:py-2 focus:rounded-lg focus:bg-white focus:text-slate-900 focus:shadow dark:focus:bg-slate-800 dark:focus:text-white"
        >
          Saltar al contenido
        </a>

        <ThemeProvider attribute="class" enableSystem defaultTheme="system" disableTransitionOnChange>
          {/* Parche global de fetch en el cliente */}
          <ClientAuthBootstrap />

          <AuthProvider>
            <AuthGate>
              <Header />
              {/* Ancla para el skip link; no afecta a las páginas */}
              <div id="content">{children}</div>
            </AuthGate>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

