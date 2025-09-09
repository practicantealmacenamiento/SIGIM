"use client";

import Navbar from "./nabar";
import { LogoPrebel } from "./logoPrebel";
import ToggleTheme from "../theme/toggleTheme";

export const Header = () => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200/60 dark:border-white/10 bg-white/70 dark:bg-slate-900/70 backdrop-blur-lg">
      <div className="h-16 px-4 md:px-6">
        <div className="grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3">
          <h1 className="text-xl md:text-2xl font-bold">Form EyS</h1>

          <div className="min-w-0">
            <Navbar />
          </div>
          <div className="flex items-center gap-3 justify-self-end">
            <ToggleTheme />
            <LogoPrebel />
          </div>
        </div>
      </div>
    </header>
  );
};
