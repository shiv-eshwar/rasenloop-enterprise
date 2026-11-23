import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RasenLoop War Room",
  description: "Supervisor console for BharatPay voice support",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
