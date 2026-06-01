import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HeritageGuard - Preservasi & Terjemahan Bahasa Daerah Jawa & Madura",
  description: "Platform AI untuk menerjemahkan Bahasa Indonesia, Jawa, dan Madura sekaligus menganalisis tingkat kesopanan bahasa.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
