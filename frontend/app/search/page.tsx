"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopBar from "@/components/TopBar";
import { api } from "@/lib/api";

type Me = { email: string; role: string };
type Stats = { chunks: number; embedded: number; by_type: Record<string, number>; embedding_model: string };
type Result = {
  chunk_id: string;
  clean_listing_id: string;
  chunk_type: string;
  project_slug: string | null;
  tier: string;
  text: string;
  source_listing_id: string;
  source_url: string;
  score: number;
  rank: number;
  retriever: string;
  path: string[] | null;
};

const MODES = [
  { id: "r1-hybrid", label: "R1 hybrid (FTS + vector)" },
  { id: "r1-fts", label: "R1 FTS (từ khóa)" },
  { id: "r1-vector", label: "R1 vector (ngữ nghĩa)" },
  { id: "r2-graph", label: "R2 graph (≤2 hop)" },
];

const VI_DU = [
  "Căn hộ 2 phòng ngủ có sổ hồng gần công viên",
  "Dự án Vinhomes Central Park nằm ở khu vực nào?",
  "So sánh giá căn hộ Mizuki Park và Akari City",
];

export default function SearchPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [query, setQuery] = useState(VI_DU[0]);
  const [mode, setMode] = useState("r1-hybrid");
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [ran, setRan] = useState(false);

  useEffect(() => {
    Promise.all([api("/api/auth/me"), api("/api/search/stats")])
      .then(([meData, statData]) => {
        setMe(meData);
        setStats(statData);
      })
      .catch(() => router.push("/"));
  }, [router]);

  const run = useCallback(
    async (q: string, m: string) => {
      setLoading(true);
      setError("");
      try {
        const data = await api(`/api/search?q=${encodeURIComponent(q)}&mode=${m}&k=8`);
        setResults(data.results);
        setRan(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Truy vấn thất bại");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return (
    <main className="container">
      <TopBar me={me} />

      <div className="card">
        <h1>Truy xuất có căn cứ</h1>
        <p className="hint">
          Cùng một câu hỏi chạy được trên nhiều cấu hình retrieval để so sánh — R1 dùng
          từ khóa/ngữ nghĩa trên chunk, R2 chỉ dùng Property Knowledge Graph. Mỗi kết quả
          đều trả về nguồn gốc.
        </p>
        {stats && (
          <p style={{ marginBottom: 8 }}>
            <span className="chip">{stats.chunks.toLocaleString("vi-VN")} chunk</span>
            <span className="chip">{stats.embedded.toLocaleString("vi-VN")} đã embed</span>
            <span className="chip mute">model: {stats.embedding_model || "—"}</span>
          </p>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            run(query, mode);
          }}
        >
          <label htmlFor="q">Câu hỏi</label>
          <input id="q" value={query} onChange={(e) => setQuery(e.target.value)} required />
          <div className="row" style={{ marginTop: 12 }}>
            <div>
              <label htmlFor="mode">Cấu hình</label>
              <select id="mode" value={mode} onChange={(e) => setMode(e.target.value)}>
                {MODES.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" disabled={loading}>
              {loading ? "Đang tìm…" : "Tìm"}
            </button>
          </div>
        </form>
        <p style={{ marginTop: 10 }}>
          {VI_DU.map((v) => (
            <button
              key={v}
              className="secondary"
              style={{ marginTop: 6, marginRight: 6, fontSize: 12, padding: "6px 10px" }}
              onClick={() => {
                setQuery(v);
                run(v, mode);
              }}
            >
              {v}
            </button>
          ))}
        </p>
        {error && <p className="error">{error}</p>}
      </div>

      {ran && (
        <div className="card">
          <h2>Kết quả ({results.length})</h2>
          {results.length === 0 && <p className="hint">Không có kết quả cho cấu hình này.</p>}
          {results.map((r) => (
            <div key={r.chunk_id} style={{ padding: "12px 0", borderBottom: "1px solid var(--line)" }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <b>#{r.rank}</b>
                <span className="chip">{r.chunk_type}</span>
                <span className="chip mute">{r.retriever}</span>
                <span className="chip mute">điểm {r.score}</span>
                {r.project_slug && <span className="chip">{r.project_slug}</span>}
                <span className="chip mute">tier {r.tier}</span>
              </div>
              {r.path && (
                <div className="path" style={{ marginTop: 6 }}>
                  {r.path.map((step, i) =>
                    step.startsWith("--") ? (
                      <span key={i} className="edge">
                        {step}
                      </span>
                    ) : (
                      <span key={i} className={i === 0 ? "node project" : "node"}>
                        {step}
                      </span>
                    )
                  )}
                </div>
              )}
              <p style={{ whiteSpace: "pre-wrap", fontSize: 14, marginTop: 6 }}>
                {r.text.slice(0, 380)}
                {r.text.length > 380 ? "…" : ""}
              </p>
              <div className="src">
                Nguồn:{" "}
                <a href={r.source_url} target="_blank" rel="noreferrer">
                  {r.source_url || "—"}
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
