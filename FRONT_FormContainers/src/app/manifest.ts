import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FormContainers",
    short_name: "FormContainers",
    description:
      "Portal interno de formularios regulados de Prebel: captura, seguimiento por fases y panel administrativo.",
    lang: "es-CO",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#1E40AF",
    theme_color: "#1E40AF",
    categories: ["productivity", "business"],
    icons: [
      {
        src: "/icons/icon-96x96.png",
        sizes: "96x96",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-180x180.png",
        sizes: "180x180",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-192x192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512x512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-maskable-512x512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
    shortcuts: [
      {
        name: "Historial de formularios",
        short_name: "Historial",
        url: "/historial",
        description: "Accede directamente al historial de formularios por fases.",
        icons: [
          {
            src: "/icons/icon-96x96.png",
            sizes: "96x96",
            type: "image/png",
          },
        ],
      },
    ],
    screenshots: [
      {
        src: "/screenshots/screenshot-wide-1280x720.png",
        sizes: "1280x720",
        type: "image/png",
        form_factor: "wide",
        label: "Panel principal con historial de formularios",
      },
      {
        src: "/screenshots/screenshot-mobile-750x1334.png",
        sizes: "750x1334",
        type: "image/png",
        form_factor: "narrow",
        label: "Vista móvil del listado de formularios",
      },
    ],
  };
}
