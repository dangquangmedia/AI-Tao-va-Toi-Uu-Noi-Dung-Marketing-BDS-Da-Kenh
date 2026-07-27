"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@cancu.demo");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? "Đăng nhập thất bại");
      }
      const data = await res.json();
      localStorage.setItem("cancu_token", data.access_token);
      router.push("/projects");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không kết nối được máy chủ");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container" style={{ maxWidth: 420, paddingTop: 80 }}>
      <div className="card">
        <div className="logotype" style={{ fontSize: 34 }}>
          Căn<span className="tick"> Cứ</span>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 14, marginBottom: 8 }}>
          Nội dung BĐS có căn cứ — đăng nhập để bắt đầu.
        </p>
        <form onSubmit={onSubmit}>
          <label htmlFor="email">Email</label>
          <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <label htmlFor="password">Mật khẩu</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? "Đang đăng nhập…" : "Đăng nhập"}
          </button>
          {error && <p className="error">{error}</p>}
        </form>
      </div>
    </main>
  );
}
