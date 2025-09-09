"use client";

import localFont from "next/font/local";
import "./globals.css";
import { ThemeProvider } from "next-themes";
import { Header } from "@/components/header/header";
import AuthGate from "@/components/auth/authGate";

const FFFAcid = localFont({ src: "./fonts/FFFAcidGroteskVariableTRIALVF.woff" });
const acidGroteskLight = localFont({ src: "./fonts/acid-grotesk-light.woff" });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body
        className={`${acidGroteskLight.className} ${FFFAcid.className} antialiased text-[#202020] dark:text-bone bg-radial from-bone via-bone to-white dark:from-skyBlue dark:via-none dark:to-[#202020]`}
      >
        <ThemeProvider attribute="class" enableSystem defaultTheme="system">
          {/* Solo para UI (saludo, etc.). El acceso lo decide el middleware. */}
          <AuthGate>
            <Header />
            {children}
          </AuthGate>
        </ThemeProvider>
      </body>
    </html>
  );
}
