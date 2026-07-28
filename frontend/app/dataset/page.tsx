"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopBar from "@/components/TopBar";
import { api } from "@/lib/api";

type Me = { email: string; role: string };
type SplitEntry = {
  units: number;
  listings: number;
  unit_pct: number;
  listing_pct: number;
  by_unit_type: Record<string, number>;
  by_stratum: Record<string, number>;
};
type Summary = {
  dataset_version: string;
  splits: Record<string, SplitEntry>;
  leakage: {
    listings_total: number;
    listings_assigned: number;
    listings_unassigned: number;
    clusters_checked: number;
    projects_checked: number;
    leaking_clusters: string[];
    leaking_projects: string[];
    passed: boolean;
  };
  gold_queries: { total: number; by_type: Record<string, number>; needs_review: number };
};
type Fact = {
  id: string;
  predicate: string;
  value_text: string;
  unit: string;
  confidence: number;
  needs_review: boolean;
  evidence: string;
  source_url: string;
  source_listing_id: string;
  original_value_text: string;
};
type GoldQuery = {
  id: string;
  query_type: string;
  question: string;
  project_slug: string | null;
  expected_listing_ids: string[];
  needs_review: boolean;
};

const SPLITS = ["train", "validation", "test"];

export default function DatasetPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [queries, setQueries] = useState<GoldQuery[]>([]);
  const [edited, setEdited] = useState<Record<string, string>>({});
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [meData, summaryData, factData, queryData] = await Promise.all([
      api("/api/auth/me"),
      api("/api/dataset/summary"),
      api("/api/dataset/facts/review?limit=20"),
      api("/api/dataset/queries?limit=12"),
    ]);
    setMe(meData);
    setSummary(summaryData);
    setFacts(factData);
    setQueries(queryData);
  }, []);

  useEffect(() => {
    load().catch(() => router.push("/"));
  }, [load, router]);

  async function reviewFact(fact: Fact, keep: boolean) {
    setError("");
    try {
      await api(`/api/dataset/facts/${fact.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          value_text: keep ? null : edited[fact.id] ?? fact.value_text,
          needs_review: false,
          note: keep ? "xác nhận đúng" : "sửa tay khi review",
        }),
      });
      setFacts((prev) => prev.filter((f) => f.id !== fact.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được");
    }
  }

  return (
    <main className="container">
      <TopBar me={me} />

      <div className="card">
        <h1>Dataset {summary?.dataset_version ?? ""}</h1>
        <p className="hint">
          Chia theo dự án và cụm dedup (không random theo mẫu) nên toàn bộ tin của một dự án
          chỉ nằm ở đúng một split — điều kiện để kết quả thực nghiệm không bị rò rỉ dữ liệu.
        </p>
        <table>
          <thead>
            <tr>
              <th>Split</th>
              <th>Đơn vị chia</th>
              <th>% đơn vị</th>
              <th>Tin</th>
              <th>% tin</th>
              <th>Theo quy mô dự án</th>
            </tr>
          </thead>
          <tbody>
            {SPLITS.map((split) => {
              const entry = summary?.splits[split];
              return (
                <tr key={split}>
                  <td>
                    <b>{split}</b>
                  </td>
                  <td>{entry?.units.toLocaleString("vi-VN") ?? "—"}</td>
                  <td>{entry?.unit_pct ?? "—"}%</td>
                  <td>{entry?.listings.toLocaleString("vi-VN") ?? "—"}</td>
                  <td>{entry?.listing_pct ?? "—"}%</td>
                  <td>
                    {entry &&
                      Object.entries(entry.by_stratum).map(([k, v]) => (
                        <span key={k} className="chip mute">
                          {k}: {v}
                        </span>
                      ))}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {summary && (
        <div className="card">
          <h2>Leakage audit</h2>
          <div className="grid" style={{ marginTop: 12 }}>
            <div className="metric">
              <span>Kết luận</span>
              <b style={{ color: summary.leakage.passed ? "var(--brand)" : "var(--danger)" }}>
                {summary.leakage.passed ? "ĐẠT" : "KHÔNG ĐẠT"}
              </b>
            </div>
            <div className="metric">
              <span>Tin được gán split</span>
              <b>
                {summary.leakage.listings_assigned.toLocaleString("vi-VN")}/
                {summary.leakage.listings_total.toLocaleString("vi-VN")}
              </b>
            </div>
            <div className="metric">
              <span>Cụm dedup rò rỉ</span>
              <b>{summary.leakage.leaking_clusters.length}</b>
            </div>
            <div className="metric">
              <span>Dự án rò rỉ</span>
              <b>{summary.leakage.leaking_projects.length}</b>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <h2>Gold retrieval queries ({summary?.gold_queries.total ?? 0})</h2>
        <p className="hint">
          Sinh bằng template trên split test, nhãn suy ra tất định từ DB.{" "}
          {summary?.gold_queries.needs_review ?? 0} câu đang chờ soát tay trước khi khóa benchmark.
        </p>
        <p>
          {summary &&
            Object.entries(summary.gold_queries.by_type).map(([k, v]) => (
              <span key={k} className="chip">
                {k}: {v}
              </span>
            ))}
        </p>
        <table>
          <thead>
            <tr>
              <th>Nhóm</th>
              <th>Câu hỏi</th>
              <th>Dự án đích</th>
              <th>Tin kỳ vọng</th>
            </tr>
          </thead>
          <tbody>
            {queries.map((q) => (
              <tr key={q.id}>
                <td>
                  <span className="chip mute">{q.query_type}</span>
                </td>
                <td>{q.question}</td>
                <td>{q.project_slug ?? "—"}</td>
                <td>{q.expected_listing_ids.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Fact cần soát ({facts.length} hiển thị)</h2>
        <p className="hint">
          Fact máy tự đánh dấu chưa chắc chắn. Xác nhận hoặc sửa — hệ thống giữ lại giá trị
          máy sinh để đối chiếu, không ghi đè mất dấu.
        </p>
        {error && <p className="error">{error}</p>}
        <table>
          <thead>
            <tr>
              <th>Predicate</th>
              <th>Giá trị</th>
              <th>Bằng chứng</th>
              <th>Độ tin</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {facts.map((f) => (
              <tr key={f.id}>
                <td>
                  <span className="chip warn">{f.predicate}</span>
                </td>
                <td style={{ minWidth: 150 }}>
                  <input
                    value={edited[f.id] ?? f.value_text}
                    onChange={(e) => setEdited({ ...edited, [f.id]: e.target.value })}
                  />
                </td>
                <td className="src">{f.evidence.slice(0, 110)}</td>
                <td>{f.confidence}</td>
                <td style={{ whiteSpace: "nowrap" }}>
                  <button
                    style={{ marginTop: 0, padding: "6px 10px", fontSize: 12 }}
                    onClick={() => reviewFact(f, true)}
                  >
                    Đúng
                  </button>
                  <button
                    className="secondary"
                    style={{ marginTop: 0, marginLeft: 6, padding: "6px 10px", fontSize: 12 }}
                    onClick={() => reviewFact(f, false)}
                  >
                    Lưu sửa
                  </button>
                </td>
              </tr>
            ))}
            {facts.length === 0 && (
              <tr>
                <td colSpan={5} style={{ color: "var(--muted)" }}>
                  Không còn fact nào chờ soát.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
