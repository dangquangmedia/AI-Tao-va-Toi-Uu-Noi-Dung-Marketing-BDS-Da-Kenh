import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Căn Cứ — Nội dung BĐS có căn cứ",
  description: "Hệ thống AI tạo nội dung marketing BĐS đa kênh — ĐATN UIT 2026",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
