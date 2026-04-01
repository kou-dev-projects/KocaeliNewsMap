import type { Metadata } from "next";

import QueryProvider from "@/components/providers/QueryProvider";

import "./globals.css";

export const metadata: Metadata = {
  title: "PULSE",
  description: "News intelligence and map experience for Kocaeli.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
