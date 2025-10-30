import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sin conexión | FormContainers",
  description:
    "Continúa trabajando en FormContainers en cuanto recuperes la conexión a internet.",
};

export default function OfflinePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-white px-6 text-center text-slate-900 dark:bg-[#202020] dark:text-bone">
      <div className="max-w-md space-y-4">
        <h1 className="text-3xl font-semibold">Estás sin conexión</h1>
        <p className="text-base text-slate-600 dark:text-slate-300">
          No pudimos conectar con el servidor de formularios. Revisa tu conexión a internet y
          vuelve a intentarlo. Mientras tanto, puedes seguir revisando la información guardada en el
          caché del navegador.
        </p>
        <p className="text-sm text-slate-400 dark:text-slate-500">
          Cuando la conexión se restablezca, esta ventana se actualizará automáticamente con los
          datos más recientes.
        </p>
      </div>
    </main>
  );
}
