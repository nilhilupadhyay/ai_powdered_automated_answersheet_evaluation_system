import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Teacher Dashboard",
  description: "Answer Sheet Evaluation Teacher Dashboard"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
