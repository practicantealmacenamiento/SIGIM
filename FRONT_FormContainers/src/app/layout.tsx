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
    <html lang="es" suppressHydrationWarning>
      <body
        className={`${acidGroteskLight.className} ${FFFAcid.className} antialiased text-[#202020] dark:text-bone bg-radial from-bone via-bone to-white dark:from-skyBlue dark:via-none dark:to-[#202020]`}
      >
        <ThemeProvider attribute="class" enableSystem defaultTheme="system">
          {/* Parche global de fetch en el cliente */}
          <ClientAuthBootstrap />
          <AuthProvider>
            <AuthGate>
              <Header />
              {children}
            </AuthGate>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
