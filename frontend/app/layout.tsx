import type { Metadata } from "next";
import { Sora, JetBrains_Mono } from "next/font/google";
import SmoothScroll from "@/components/ui/smooth-scroll";
import "./globals.css";

const sora = Sora({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sora",
  weight: ["300", "400", "500", "600", "700", "800"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-jetbrains-mono",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "SIH26006 | Ministry of Steel & PSU Freight Decision Support System",
  description:
    "Smart India Hackathon 2026: Intelligent Freight Forecasting Model for Optimized Vessel Chartering in Steel Manufacturing",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${sora.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-[#090a0f] text-slate-200 antialiased font-sans selection:bg-blue-600/30 selection:text-blue-200">
        <SmoothScroll>
          {children}
        </SmoothScroll>
      </body>
    </html>
  );
}
