import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "PULSE | Live Scrape Monitor",
  description: "Real-time scrape activity and operations dashboard for PULSE.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
