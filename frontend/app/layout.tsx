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
  title: "OrgMemory — The memory layer for engineering organizations",
  description: "Every incident, decision, owner, and dependency your engineering org already learned, tied to its source — and briefed to the people and AI agents about to change something, before they change it.",
  openGraph: {
    title: "OrgMemory — The memory layer for engineering organizations",
    description: "Your organization remembers. Give every engineer and every browser agent source-backed context before they act.",
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "OrgMemory company brain" }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "OrgMemory — The memory layer for engineering organizations",
    description: "Source-backed memory for engineering teams and the agents working alongside them.",
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
