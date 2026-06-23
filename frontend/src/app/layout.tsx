import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lokalator - Preservasi & Terjemahan Bahasa Daerah Jawa & Madura",
  description: "Platform AI untuk menerjemahkan Bahasa Indonesia, Jawa, dan Madura sekaligus menganalisis tingkat kesopanan bahasa.",
  icons: {
    icon: "/assets/lokalator_logo_centered.png",
  },
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
