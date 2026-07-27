"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopBar from "@/components/TopBar";
import { api } from "@/lib/api";

type Project = {
  id: string;
  name: string;
  slug: string;
  description: string;
  created_at: string;
};

type Me = { email: string; role: string };
type Stats = { source_listings: number; quarantined: number };

export default function ProjectsPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [meData, projectData, statData] = await Promise.all([
      api("/api/auth/me"),
      api("/api/projects"),
      api("/api/ingestion/stats"),
    ]);
    setMe(meData);
    setProjects(projectData);
    setStats(statData);
  }, []);

  useEffect(() => {
    load().catch(() => router.push("/"));
  }, [load, router]);

  async function createProject(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/api/projects", {
        method: "POST",
        body: JSON.stringify({ name, slug, description: "" }),
      });
      setName("");
      setSlug("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tạo dự án thất bại");
    }
  }

  const canCreate = me?.role === "admin" || me?.role === "marketer";

  return (
    <main className="container">
      <TopBar me={me} />

      {stats && (
        <div className="stats">
          <div className="stat">
            <b>{stats.source_listings.toLocaleString("vi-VN")}</b> tin đã nhập kho (raw zone)
          </div>
          <div className="stat">
            <b>{stats.quarantined.toLocaleString("vi-VN")}</b> bản ghi quarantine
          </div>
        </div>
      )}

      <div className="card">
        <h1>Dự án BĐS</h1>
        {canCreate && (
          <form onSubmit={createProject} style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
            <div style={{ flex: 2 }}>
              <label htmlFor="name">Tên dự án</label>
              <input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div style={{ flex: 1 }}>
              <label htmlFor="slug">Slug (a-z, 0-9, -)</label>
              <input
                id="slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                pattern="[a-z0-9-]+"
                required
              />
            </div>
            <button type="submit">Tạo dự án</button>
          </form>
        )}
        {error && <p className="error">{error}</p>}
        <table>
          <thead>
            <tr>
              <th>Tên</th>
              <th>Slug</th>
              <th>Ngày tạo</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.id}>
                <td>
                  <b>{p.name}</b>
                </td>
                <td>{p.slug}</td>
                <td>{new Date(p.created_at).toLocaleDateString("vi-VN")}</td>
              </tr>
            ))}
            {projects.length === 0 && (
              <tr>
                <td colSpan={3} style={{ color: "var(--muted)" }}>
                  Chưa có dự án — tạo dự án đầu tiên ở trên.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
