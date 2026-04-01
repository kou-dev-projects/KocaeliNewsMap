import type { Metadata, Viewport } from "next";

<<<<<<< feature/s2-tanstack-query
import QueryProvider from "@/components/providers/QueryProvider";

=======
import { PwaBootstrap } from "@/components/pwa/PwaBootstrap";
>>>>>>> develop
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "PULSE",
    template: "%s | PULSE",
  },
  description: "News intelligence, mapping, and field operations for Kocaeli.",
  applicationName: "PULSE",
  manifest: "/manifest.json",
  formatDetection: {
    telephone: false,
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "PULSE",
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/icons/apple-touch-icon.png",
    shortcut: "/icons/icon-192.png",
  },
};

export const viewport: Viewport = {
  themeColor: "#0a0a0a",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
<<<<<<< feature/s2-tanstack-query
        <QueryProvider>{children}</QueryProvider>
=======
        {children}
        <PwaBootstrap />
>>>>>>> develop
      </body>
    </html>
  );
}
