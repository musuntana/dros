import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Newsreader } from "next/font/google";
import type { ReactNode } from "react";

import { QueryProvider } from "@/lib/query/provider";

import "./globals.css";

const uiFont = IBM_Plex_Sans({
  subsets: ["latin"],
  variable: "--font-ui",
});

const displayFont = Newsreader({
  subsets: ["latin"],
  variable: "--font-display",
});

const monoFont = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "DR-OS Research Canvas",
  description: "Project-scoped frontend workspace for DR-OS control plane objects.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      className={`${uiFont.variable} ${displayFont.variable} ${monoFont.variable}`}
      lang="zh-CN"
    >
      <body>
        <QueryProvider>
          <div className="mx-auto min-h-screen max-w-[1600px] px-4 py-6 md:px-6 xl:px-10">{children}</div>
        </QueryProvider>
      </body>
    </html>
  );
}
