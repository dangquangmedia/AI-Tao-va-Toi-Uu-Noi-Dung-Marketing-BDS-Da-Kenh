"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

type Me = { email: string; role: string } | null;

const LINKS = [
  { href: "/projects", label: "Dự án" },
  { href: "/data", label: "Dữ liệu" },
  { href: "/graph", label: "Tri thức" },
  { href: "/search", label: "Truy xuất" },
  { href: "/studio", label: "Studio" },
  { href: "/dataset", label: "Dataset" },
];

export default function TopBar({ me }: { me: Me }) {
  const router = useRouter();
  const pathname = usePathname();

  function logout() {
    localStorage.removeItem("cancu_token");
    router.push("/");
  }

  return (
    <div className="topbar">
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <div className="logotype" style={{ fontSize: 24 }}>
          Căn<span className="tick"> Cứ</span>
        </div>
        <nav className="nav">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={pathname === link.href ? "nav-link active" : "nav-link"}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
      <div style={{ fontSize: 13, color: "var(--muted)" }}>
        {me ? `${me.email} · ${me.role}` : "…"}{" "}
        <button className="secondary" style={{ marginTop: 0, marginLeft: 8 }} onClick={logout}>
          Đăng xuất
        </button>
      </div>
    </div>
  );
}
