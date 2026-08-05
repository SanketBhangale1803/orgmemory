import type { Metadata } from "next";
import { Inter } from "next/font/google";
import AppShell from "@/components/AppShell";
import "./globals.css";

/* Self-hosted at build time. The stylesheet already asks for Inter by name;
   this makes the request actually resolve instead of silently falling back. */
const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"),
  title: "OrgMemory — Your company already knows the answer",
  description: "The source-backed operating brain for your company. Connect code, conversations, documents, and decisions; retrieve with a specialist agent swarm; act with approval.",
  openGraph: {
    title: "OrgMemory — Your company already knows the answer",
    description: "The source-backed operating brain for your company.",
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "OrgMemory company brain" }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "OrgMemory — Your company already knows the answer",
    description: "The source-backed operating brain for your company.",
    images: ["/og.png"],
  },
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
    shortcut: "/icon.svg",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" data-scroll-behavior="smooth" className={inter.variable}><body><AppShell>{children}</AppShell></body></html>;
}
