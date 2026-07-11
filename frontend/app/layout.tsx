import type { Metadata } from "next";
import Nav from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = { title: "Runbook", description: "Verified operational knowledge for production systems" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><div className="shell"><Nav/><main className="main"><header className="topbar"><span className="crumb">Production runbook reliability</span><span className="env">Local workspace</span></header>{children}</main></div></body></html>;
}
