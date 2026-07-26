import type { Metadata } from "next";
import { Inter, Crimson_Pro, Cormorant_Garamond } from "next/font/google";
import { Providers } from "./providers";
import { Navbar } from "../components/ui/Navbar";
import { NetworkStatus } from "../components/ui/NetworkStatus";
import "../styles/globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-ui" });
const crimsonPro = Crimson_Pro({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["300", "400", "600"],
});
const cormorantGaramond = Cormorant_Garamond({
  subsets: ["latin"],
  variable: "--font-heading",
  weight: ["300", "500", "700"],
});

export const metadata: Metadata = {
  title: "LinguaNotebook — Learn languages from your own documents",
  description:
    "Upload your PDFs, get personalized daily lessons with flashcards, reading, grammar, and listening — all from your own materials. 100% free and open source.",
  manifest: "/manifest.json",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${crimsonPro.variable} ${cormorantGaramond.variable}`}
    >
      <body className="min-h-screen bg-background font-body text-foreground antialiased">
        <Providers>
          <Navbar />
          {children}
          <NetworkStatus />
        </Providers>
      </body>
    </html>
  );
}
