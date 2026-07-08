import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Gov Bid Sourcing",
  description: "Find, source, and bid on government part solicitations",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-neutral-950 text-neutral-100">
        <header className="border-b border-neutral-800 px-6 py-3 flex items-center gap-6">
          <span className="font-semibold">Gov Bid Sourcing</span>
          <nav className="flex gap-4 text-sm text-neutral-300">
            <Link href="/" className="hover:text-white">
              Solicitations
            </Link>
            <Link href="/outreach" className="hover:text-white">
              Outreach
            </Link>
            <Link href="/bids" className="hover:text-white">
              Bid Drafts
            </Link>
          </nav>
        </header>
        <main className="flex-1 px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
