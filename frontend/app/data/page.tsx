"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopBar from "@/components/TopBar";
import { api } from "@/lib/api";

type Me = { email: string; role: string };
type Coverage = { n: number; pct: number };
type Report = {
  raw: { source_listings: number };
  clean: {
    total: number;
    by_tier: Record<string, number>;
    by_price_confidence: Record<string, number>;
    field_coverage: Record<string, Coverage>;
  };
  dedup: { clusters: number; representatives: number; duplicates: number };
  quarantine: { total: number; by_error: Record<string, number> };
  facts: { total: number; needs_review: number; by_predicate: Record<string, number> };
  graph: {
    entities: number;
    edges: number;
    by_entity_type: Record<string, number>;
    by_edge_type: Record<string, number>;
    top_projects: { key: string; name: string; listings: number }[];
  };
};
type Job = {
  id: string;
  status: string;
  total_read: number;
  inserted: number;
  unchanged: number;
  updated: number;
  quarantined: number;
  stats: Record<string, number>;
  started_at: string;
};
type Quarantine = { id: string; error_code: string; source_ref: string; raw: Record<string, string> };

const FIELD_LABELS: Record<string, string> = {
  project_slug: "Dự án (từ URL)",
  building_code: "Mã tòa/block",
  ward: "Phường/xã",
  district: "Quận/huyện",
  city: "Tỉnh/thành",
  area_m2: "Diện tích",
  bedrooms: "Phòng ngủ",
  total_price_vnd: "Giá tổng",
  price_per_m2_vnd: "Giá/m²",
  legal_facts: "Pháp lý",
  amenities: "Tiện ích",
};

function vn(n: number | undefined) {
  return (n ?? 0).toLocaleString("vi-VN");
}

export default function DataPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [quarantine, setQuarantine] = useState<Quarantine[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [meData, reportData, jobData, quarantineData] = await Promise.all([
      api("/api/auth/me"),
      api("/api/pipeline/data-quality"),
      api("/api/pipeline/jobs"),
      api("/api/pipeline/quarantine?limit=50"),
    ]);
    setMe(meData);
    setReport(reportData);
    setJobs(jobData);
    setQuarantine(quarantineData);
  }, []);

  useEffect(() => {
    load().catch(() => router.push("/"));
  }, [load, router]);

  async function runPipeline() {
    setRunning(true);
    setError("");
    try {
      await api("/api/pipeline/run", { method: "POST", body: JSON.stringify({}) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chạy pipeline thất bại");
    } finally {
      setRunning(false);
    }
  }

  const coverage = report?.clean.field_coverage ?? {};

  return (
    <main className="container">
      <TopBar me={me} />

      <div className="card">
        <h1>Kho dữ liệu và pipeline làm sạch</h1>
        <p className="hint">
          Raw zone bất biến → D1 re-parse → D2 chuẩn hóa → D3 dedup → D4 canonical facts → D5 graph.
          Chạy lại trên cùng batch cho đúng cùng kết quả (idempotent).
        </p>
        {me?.role === "admin" && (
          <button onClick={runPipeline} disabled={running}>
            {running ? "Đang chạy D1–D5…" : "Chạy lại pipeline D1–D5"}
          </button>
        )}
        {error && <p className="error">{error}</p>}

        {report && (
          <div className="grid" style={{ marginTop: 16 }}>
            <div className="metric">
              <span>Tin raw</span>
              <b>{vn(report.raw.source_listings)}</b>
            </div>
            <div className="metric">
              <span>Tin đã làm sạch</span>
              <b>{vn(report.clean.total)}</b>
            </div>
            <div className="metric">
              <span>Canonical facts</span>
              <b>{vn(report.facts.total)}</b>
            </div>
            <div className="metric">
              <span>Node / cạnh graph</span>
              <b>
                {vn(report.graph.entities)} / {vn(report.graph.edges)}
              </b>
            </div>
            <div className="metric">
              <span>Cụm dedup</span>
              <b>{vn(report.dedup.clusters)}</b>
            </div>
            <div className="metric">
              <span>Quarantine</span>
              <b>{vn(report.quarantine.total)}</b>
            </div>
          </div>
        )}
      </div>

      {report && (
        <div className="card">
          <h2>Độ phủ trường sau re-parse</h2>
          <p className="hint">
            Trường nào không khôi phục được thì để trống và gắn flag — không suy diễn giá trị.
          </p>
          <table>
            <thead>
              <tr>
                <th>Trường</th>
                <th>Số tin</th>
                <th>Tỷ lệ</th>
                <th style={{ width: "35%" }}>Độ phủ</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(FIELD_LABELS).map(([field, label]) => (
                <tr key={field}>
                  <td>{label}</td>
                  <td>{vn(coverage[field]?.n)}</td>
                  <td>{coverage[field]?.pct ?? 0}%</td>
                  <td>
                    <div className="bar">
                      <i style={{ width: `${coverage[field]?.pct ?? 0}%` }} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ marginTop: 12 }}>
            <span className="chip">Tier A: {vn(report.clean.by_tier.A)}</span>
            <span className="chip mute">Tier B: {vn(report.clean.by_tier.B)}</span>
            <span className="chip mute">Tier C: {vn(report.clean.by_tier.C)}</span>
            <span className="chip warn">Fact cần review: {vn(report.facts.needs_review)}</span>
          </p>
        </div>
      )}

      <div className="card">
        <h2>Lần chạy pipeline</h2>
        <table>
          <thead>
            <tr>
              <th>Bắt đầu</th>
              <th>Trạng thái</th>
              <th>Đọc</th>
              <th>Thêm</th>
              <th>Giữ nguyên</th>
              <th>Cập nhật</th>
              <th>Quarantine</th>
              <th>Facts / node / cạnh</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{new Date(job.started_at).toLocaleString("vi-VN")}</td>
                <td>{job.status}</td>
                <td>{vn(job.total_read)}</td>
                <td>
                  <b>{vn(job.inserted)}</b>
                </td>
                <td>{vn(job.unchanged)}</td>
                <td>{vn(job.updated)}</td>
                <td>{vn(job.quarantined)}</td>
                <td>
                  +{vn(job.stats?.facts_inserted)} / {vn(job.stats?.entities)} / {vn(job.stats?.edges)}
                </td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr>
                <td colSpan={8} style={{ color: "var(--muted)" }}>
                  Chưa chạy pipeline lần nào.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <p className="hint" style={{ marginTop: 8 }}>
          Chạy lần hai trên cùng batch phải cho <b>Thêm = 0</b> và <b>Giữ nguyên = toàn bộ</b>.
        </p>
      </div>

      <div className="card">
        <h2>Quarantine ({vn(report?.quarantine.total)})</h2>
        <p className="hint">
          Bản ghi vi phạm data contract v1 — giữ lại để truy vết, không chặn batch.
        </p>
        <table>
          <thead>
            <tr>
              <th>Mã lỗi</th>
              <th>Tin nguồn</th>
              <th>Thông tin giữ lại</th>
            </tr>
          </thead>
          <tbody>
            {quarantine.map((row) => (
              <tr key={row.id}>
                <td>
                  <span className="chip warn">{row.error_code}</span>
                </td>
                <td>{row.source_ref || "—"}</td>
                <td className="src">
                  {row.raw?.canonical_url ? (
                    <a href={row.raw.canonical_url} target="_blank" rel="noreferrer">
                      {row.raw.canonical_url}
                    </a>
                  ) : (
                    JSON.stringify(row.raw).slice(0, 120)
                  )}
                </td>
              </tr>
            ))}
            {quarantine.length === 0 && (
              <tr>
                <td colSpan={3} style={{ color: "var(--muted)" }}>
                  Không có bản ghi nào bị quarantine.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
