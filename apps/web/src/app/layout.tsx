import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KOMRADE",
  description: "Local MVP scaffold",
  icons: {
    icon: "/komrade_logo.png",
    shortcut: "/komrade_logo.png",
    apple: "/komrade_logo.png",
  },
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
