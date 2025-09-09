"use client";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Se asegura de que el componente solo se monte en el cliente
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null; // Evita el error de Hydration

  return (
    <button
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="border-b-4 hover:border-current border-transparent flex gap-1 items-center"
    >
      {theme === "dark" ? "Claro ☀️" : "Oscuro 🌙"}
    </button>
  );
}
