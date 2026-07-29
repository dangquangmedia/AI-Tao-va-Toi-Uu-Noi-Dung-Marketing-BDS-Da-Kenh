"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopBar from "@/components/TopBar";
import { api } from "@/lib/api";

type Me = { email: string; role: string };

type ConfigSummary = {
  n: number;
  n_failed?: number;
  unsupported_claim_rate?: number | null;
  outputs_with_unsupported?: number | null;
  n_claims?: number | null;
  n_forbidden?: number | null;
  structured_ok?: number | null;
  // null khi mọi bài đều bị cắt vì hết ngân sách token — không kết luận được về độ dài
  length_ok?: number | null;
  length_ok_n?: number;
  words?: number | null;
  latency_s?: number | null;
};

type MetricComparison = {
  label: string;
  direction: "lower" | "higher";
  n: number;
  mean_before: number;
  mean_after: number;
  mean_diff: number;
  wins: number;
  losses: number;
  ties: number;
  cohens_dz: number | null;
  ci: { low: number | null; high: number | null; level: number };
  test_p_value: number | null;
  test_method?: string;
};

type Comparison = { pair: string; factor: string; metrics: Record<string, MetricComparison> };

type Summary = {
  by_config: Record<string, ConfigSummary>;
  comparisons: Comparison[];
  primary_metric: string;
};

type Snapshot = {
  git_commit?: string;
  taken_at?: string;
  split_units?: Record<string, number>;
  gold_queries?: Record<string, number>;
  knowledge_base?: Record<string, string | number>;
  retrieval?: {
    default_weights?: Record<string, number>;
    discovery_weights?: Record<string, number>;
  };
  generation?: Record<string, string | number | boolean>;
  adapter?: { name: string; base_model: string; fingerprint: string } | null;
};

type Run = {
  id: string;
  run_key: string;
  label: string;
  dataset_version: string;
  configs: string[];
  skipped: Record<string, string>;
  n_briefs: number;
  status: string;
  error: string;
  started_at: string;
  finished_at: string | null;
  summary: Summary | null;
  snapshot?: Snapshot;
};

type Item = {
  id: string;
  config: string;
  channel: string;
  persona: string;
  project_slug: string | null;
  headline: string;
  body: string;
  status: string;
  metrics: Record<string, number | string>;
};

const CONFIG_LABELS: Record<string, string> = {
  A: "A · prompt-only",
  B: "B · RAG",
  C: "C · QLoRA",
  D: "D · RAG + QLoRA",
};

// Nhãn + chiều tốt của từng dòng trong bảng chỉ số. `lower` = càng nhỏ càng tốt.
const METRIC_ROWS: { key: keyof ConfigSummary; label: string; better: "lower" | "higher" | null; pct?: boolean }[] = [
  { key: "n", label: "Số bài chạy được", better: null },
  { key: "unsupported_claim_rate", label: "Tỷ lệ claim không có căn cứ", better: "lower" },
  { key: "outputs_with_unsupported", label: "Bài có ≥1 claim vô căn cứ", better: "lower" },
  { key: "n_claims", label: "Số claim mỗi bài", better: null },
  { key: "n_forbidden", label: "Câu chứa từ cấm", better: "lower" },
  { key: "structured_ok", label: "Đúng định dạng 3 phần", better: "higher", pct: true },
  { key: "length_ok", label: "Đúng khoảng độ dài kênh", better: "higher", pct: true },
  { key: "words", label: "Số từ trung bình", better: null },
  { key: "latency_s", label: "Thời gian sinh (giây)", better: "lower" },
];

function fmt(value: number | string | undefined | null, pct = false): string {
  if (value === undefined || value === null) return "—";
  if (typeof value === "string") return value;
  if (pct) return `${(value * 100).toFixed(0)}%`;
  return Number.isInteger(value) ? String(value) : value.toFixed(3);
}

export default function ExperimentsPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [active, setActive] = useState<Run | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [showItems, setShowItems] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [meData, runData] = await Promise.all([api("/api/auth/me"), api("/api/experiments")]);
    setMe(meData);
    setRuns(runData.items);
    if (runData.items.length) {
      setActive(await api(`/api/experiments/${runData.items[0].id}`));
    }
  }, []);

  useEffect(() => {
    load().catch(() => router.push("/"));
  }, [load, router]);

  async function select(run: Run) {
    setError("");
    setShowItems(false);
    setItems([]);
    try {
      setActive(await api(`/api/experiments/${run.id}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được lượt chạy");
    }
  }

  async function loadItems() {
    if (!active) return;
    try {
      const data = await api(`/api/experiments/${active.id}/items`);
      setItems(data.items);
      setShowItems(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được danh sách bài");
    }
  }

  const configs = active?.summary ? Object.keys(active.summary.by_config) : [];
  const snapshot = active?.snapshot ?? {};

  // Cấu hình tốt nhất theo chỉ số chính — tô đậm để đọc bảng nhanh, không thay số.
  function bestConfig(key: keyof ConfigSummary, better: "lower" | "higher" | null): string | null {
    if (!better || !active?.summary) return null;
    const entries = configs
      .map((c) => [c, active.summary!.by_config[c][key]] as const)
      .filter((e): e is readonly [string, number] => typeof e[1] === "number");
    if (entries.length < 2) return null;
    return entries.reduce((acc, cur) =>
      better === "lower" ? (cur[1] < acc[1] ? cur : acc) : cur[1] > acc[1] ? cur : acc,
    )[0];
  }

  return (
    <main className="container">
      <TopBar me={me} />

      <div className="card">
        <h1>So sánh cấu hình A–D</h1>
        <p className="hint">
          Mỗi lượt chạy đóng băng một bộ brief lấy từ split test và chạy mọi cấu hình trên
          <b> cùng brief, cùng thứ tự, cùng seed</b>. Bảng dưới đọc thẳng từ bản ghi
          <code> experiment_runs</code>, không nhập tay.
        </p>
        {runs.length === 0 && (
          <p className="hint">
            Chưa có lượt chạy nào. Chạy <code>python -m app.experiment_cli --briefs 12</code> ở thư
            mục <code>backend</code>.
          </p>
        )}
        <div className="row" style={{ gap: 8 }}>
          {runs.map((run) => (
            <button
              key={run.id}
              className={active?.id === run.id ? "" : "secondary"}
              style={{ marginTop: 0 }}
              onClick={() => select(run)}
            >
              {run.run_key} · {run.n_briefs} brief · {run.configs.join("")}
              {run.status !== "done" ? ` · ${run.status}` : ""}
            </button>
          ))}
        </div>
        {error && <p className="error">{error}</p>}
      </div>

      {active && (
        <div className="card">
          <h2>Điều kiện chạy (snapshot)</h2>
          <p className="hint">
            Số liệu chỉ so sánh được với lượt chạy khác khi các dòng dưới đây trùng nhau. Đổi model,
            đổi prompt version hay đổi adapter là một thí nghiệm khác.
          </p>
          <table>
            <tbody>
              <tr>
                <td>Commit</td>
                <td>
                  <code>{snapshot.git_commit ?? "—"}</code> · {snapshot.taken_at ?? ""}
                </td>
              </tr>
              <tr>
                <td>Dataset</td>
                <td>
                  <code>{active.dataset_version}</code> — split{" "}
                  {JSON.stringify(snapshot.split_units ?? {})} · gold query{" "}
                  {JSON.stringify(snapshot.gold_queries ?? {})}
                </td>
              </tr>
              <tr>
                <td>Knowledge base</td>
                <td>
                  {snapshot.knowledge_base?.chunks ?? "—"} chunk (
                  {snapshot.knowledge_base?.chunks_embedded ?? "—"} đã embed) ·{" "}
                  {snapshot.knowledge_base?.facts ?? "—"} fact · embedding{" "}
                  <code>{snapshot.knowledge_base?.embedding_model ?? "—"}</code>
                </td>
              </tr>
              <tr>
                <td>Model sinh</td>
                <td>
                  <code>{String(snapshot.generation?.model ?? "—")}</code> · provider{" "}
                  {String(snapshot.generation?.provider ?? "—")} · seed{" "}
                  {String(snapshot.generation?.seed ?? "—")} · prompt{" "}
                  <code>{String(snapshot.generation?.prompt_version ?? "—")}</code>
                </td>
              </tr>
              <tr>
                <td>Adapter</td>
                <td>
                  {snapshot.adapter ? (
                    <>
                      <code>{snapshot.adapter.name}</code> trên{" "}
                      <code>{snapshot.adapter.base_model}</code> · fingerprint{" "}
                      <code>{snapshot.adapter.fingerprint}</code>
                    </>
                  ) : (
                    <span className="chip warn">chưa có adapter</span>
                  )}
                </td>
              </tr>
              <tr>
                <td>Trọng số RRF</td>
                <td>
                  có tên dự án: {JSON.stringify(snapshot.retrieval?.default_weights ?? {})} · tìm
                  theo mô tả: {JSON.stringify(snapshot.retrieval?.discovery_weights ?? {})}
                </td>
              </tr>
            </tbody>
          </table>
          {Object.keys(active.skipped ?? {}).length > 0 && (
            <p className="hint" style={{ marginTop: 12 }}>
              <b>Bỏ qua:</b>{" "}
              {Object.entries(active.skipped).map(([config, reason]) => (
                <span key={config} className="chip warn">
                  {config}: {reason}
                </span>
              ))}
            </p>
          )}
        </div>
      )}

      {active?.summary && (
        <div className="card">
          <h2>Kết quả theo cấu hình</h2>
          <table>
            <thead>
              <tr>
                <th>Chỉ số</th>
                {configs.map((c) => (
                  <th key={c} style={{ textAlign: "right" }}>
                    {CONFIG_LABELS[c] ?? c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {METRIC_ROWS.map((row) => {
                const best = bestConfig(row.key, row.better);
                return (
                  <tr key={row.key}>
                    <td>{row.label}</td>
                    {configs.map((c) => {
                      const value = active.summary!.by_config[c][row.key];
                      return (
                        <td
                          key={c}
                          style={{
                            textAlign: "right",
                            fontWeight: best === c ? 700 : 400,
                            color: best === c ? "var(--brand)" : undefined,
                          }}
                        >
                          {fmt(value, row.pct)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="hint" style={{ marginTop: 12 }}>
            Bài bị cắt vì chạm trần token không được tính vào “đúng khoảng độ dài” — không phân
            biệt được model viết sai độ dài hay chỉ hết ngân sách sinh.
            {active.summary.by_config[configs[0]]?.length_ok_n !== undefined &&
              ` Chỉ ${active.summary.by_config[configs[0]].length_ok_n}/${active.summary.by_config[configs[0]].n} bài đo được.`}
          </p>
        </div>
      )}

      {active?.summary && active.summary.comparisons.length > 0 && (
        <div className="card">
          <h2>So sánh từng cặp</h2>
          <p className="hint">
            Chỉ so những cặp khác nhau <b>đúng một biến</b>, bắt cặp theo từng brief. `p` từ kiểm
            định hoán vị bắt cặp; khoảng tin cậy 95% bootstrap 10.000 lần, seed 42. Với n ={" "}
            {active.n_briefs}, p nhỏ nhất có thể đạt là {(1 / 2 ** active.n_briefs).toFixed(4)} —
            cỡ mẫu nhỏ thì cột p chỉ để tham chiếu. Cột <b>số cặp</b> nhỏ hơn số brief khi một
            bên không đo được chỉ số đó (bài bị cắt vì hết token) — cặp đó bị loại chứ không
            thay bằng 0.
          </p>
          <table>
            <thead>
              <tr>
                <th>Cặp</th>
                <th>Biến</th>
                <th>Chỉ số</th>
                <th style={{ textAlign: "right" }}>Số cặp</th>
                <th style={{ textAlign: "right" }}>Trước</th>
                <th style={{ textAlign: "right" }}>Sau</th>
                <th style={{ textAlign: "right" }}>Chênh</th>
                <th>KTC 95%</th>
                <th style={{ textAlign: "right" }}>Thắng/Thua</th>
                <th style={{ textAlign: "right" }}>dz</th>
                <th style={{ textAlign: "right" }}>p</th>
              </tr>
            </thead>
            <tbody>
              {active.summary.comparisons.flatMap((cmp) =>
                Object.entries(cmp.metrics)
                  .filter(([, m]) => m.n > 0)
                  .map(([key, m]) => {
                    const improved =
                      m.direction === "lower" ? m.mean_diff < 0 : m.mean_diff > 0;
                    return (
                      <tr key={`${cmp.pair}-${key}`}>
                        <td>
                          <b>{cmp.pair}</b>
                        </td>
                        <td>{cmp.factor}</td>
                        <td>{m.label}</td>
                        <td style={{ textAlign: "right" }}>{m.n}</td>
                        <td style={{ textAlign: "right" }}>{fmt(m.mean_before)}</td>
                        <td style={{ textAlign: "right" }}>{fmt(m.mean_after)}</td>
                        <td
                          style={{
                            textAlign: "right",
                            color: m.mean_diff === 0 ? undefined : improved ? "var(--brand)" : "var(--danger)",
                          }}
                        >
                          {m.mean_diff > 0 ? "+" : ""}
                          {fmt(m.mean_diff)}
                        </td>
                        <td>
                          {m.ci.low === null ? "—" : `[${m.ci.low}; ${m.ci.high}]`}
                        </td>
                        <td style={{ textAlign: "right" }}>
                          {m.wins}/{m.losses}
                        </td>
                        <td style={{ textAlign: "right" }}>{fmt(m.cohens_dz)}</td>
                        <td style={{ textAlign: "right" }}>{fmt(m.test_p_value)}</td>
                      </tr>
                    );
                  }),
              )}
            </tbody>
          </table>
        </div>
      )}

      {active && (
        <div className="card">
          <h2>Từng bài trong lượt chạy</h2>
          {!showItems ? (
            <button className="secondary" onClick={loadItems}>
              Xem {active.n_briefs * (active.configs?.length ?? 0)} bài
            </button>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Cấu hình</th>
                  <th>Kênh</th>
                  <th>Dự án</th>
                  <th>Tiêu đề</th>
                  <th style={{ textAlign: "right" }}>Claim vô căn cứ</th>
                  <th style={{ textAlign: "right" }}>Số từ</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <b>{item.config}</b>
                    </td>
                    <td>{item.channel}</td>
                    <td>{item.project_slug ?? "—"}</td>
                    <td style={{ maxWidth: 280 }}>{item.headline || item.body.slice(0, 60)}</td>
                    <td style={{ textAlign: "right" }}>
                      {fmt(item.metrics.unsupported_claim_rate as number)}
                    </td>
                    <td style={{ textAlign: "right" }}>{fmt(item.metrics.words as number)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </main>
  );
}
