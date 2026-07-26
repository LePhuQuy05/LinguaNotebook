import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "LinguaNotebook",
    short_name: "LinguaNotebook",
    description: "Learn languages from your own documents. 100% free and open source.",
    start_url: "/",
    display: "standalone",
    background_color: "#FAF5FF",
    theme_color: "#7C3AED",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
