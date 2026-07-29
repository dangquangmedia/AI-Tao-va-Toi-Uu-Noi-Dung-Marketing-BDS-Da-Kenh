"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopBar from "@/components/TopBar";
import { api } from "@/lib/api";

type Me = { email: string; role: string };
type Entity = { id: string; key: string; name: string; support_count: number };
type Claim = { text: string; status: string; reason: string };
type Generation = {
  id: string;
  config: string;
  retrieval_config: string;
  channel: string;
  persona: string;
  project_slug: string | null;
  headline: string;
  body: string;
  cta: string;
  claims: Claim[];
  metrics: Record<string, number | Record<string, number>>;
  graph_paths: string[][];
  router_plan: { intent?: string; explain?: string };
  context_fact_ids: string[];
  context_chunk_ids: string[];
  model_name: string;
  prompt_version: string;
  latency_ms: number;
  status: string;
  error: string;
};
type RetrievalItem = {
  chunk_id: string;
  chunk_type: string;
  project_slug: string | null;
  text: string;
  source_url: string;
  score: number;
  retriever: string;
  path: string[] | null;
};

const CHANNELS = [
  { value: "description", label: "Mô tả BĐS" },
  { value: "facebook", label: "Facebook" },
  { value: "email", label: "Email" },
  { value: "landing_seo", label: "Landing SEO" },
];
const PERSONAS = [
  { value: "young_family", label: "Gia đình trẻ" },
  { value: "investor", label: "Nhà đầu tư" },
  { value: "first_home", label: "Mua nhà lần đầu" },
];

function ClaimList({ claims }: { claims: Claim[] }) {
  if (!claims?.length) return <p className="hint">Không có claim nào cần kiểm chứng.</p>;
  return (
    <div>
      {claims.map((claim, i) => (
        <div key={i} style={{ marginBottom: 6 }}>
          <span className={claim.status === "supported" ? "chip" : "chip warn"}>
            {claim.status === "supported" ? "có căn cứ" : claim.status}
          </span>{" "}
          <span style={{ fontSize: 13 }}>{claim.text}</span>
          {claim.reason && <div className="src">↳ {claim.reason}</div>}
        </div>
      ))}
    </div>
  );
}

function Output({ gen }: { gen: Generation | null }) {
  if (!gen) return <p className="hint">Chưa chạy.</p>;
  if (gen.status === "failed") return <p className="error">Lỗi: {gen.error}</p>;
  const rate = (gen.metrics?.unsupported_claim_rate as number) ?? 0;
  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <span className="chip mute">{gen.model_name}</span>
        <span className="chip mute">{gen.prompt_version}</span>
        <span className="chip mute">{(gen.latency_ms / 1000).toFixed(1)}s</span>
        <span className={rate > 0 ? "chip warn" : "chip"}>
          claim không căn cứ: {(rate * 100).toFixed(0)}%
        </span>
        <span className="chip mute">{gen.context_fact_ids.length} fact</span>
      </div>
      <h3 style={{ fontFamily: "Cambria, Georgia, serif", fontSize: 17, marginBottom: 6 }}>
        {gen.headline || "(không có headline)"}
      </h3>
      <div style={{ whiteSpace: "pre-wrap", fontSize: 14, lineHeight: 1.6 }}>{gen.body}</div>
      {gen.cta && <p style={{ marginTop: 8, fontWeight: 600, fontSize: 14 }}>{gen.cta}</p>}
    </div>
  );
}

export default function StudioPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [projects, setProjects] = useState<Entity[]>([]);
  const [projectSlug, setProjectSlug] = useState("");
  const [channel, setChannel] = useState("description");
  const [persona, setPersona] = useState("young_family");
  const [retrievalConfig, setRetrievalConfig] = useState("R3");
  const [brief, setBrief] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [genA, setGenA] = useState<Generation | null>(null);
  const [genB, setGenB] = useState<Generation | null>(null);
  const [evidence, setEvidence] = useState<RetrievalItem[]>([]);
  const [plan, setPlan] = useState<{ intent?: string; explain?: string } | null>(null);

  useEffect(() => {
    Promise.all([api("/api/auth/me"), api("/api/graph/entities?entity_type=Project&limit=60")])
      .then(([meData, projectData]: [Me, Entity[]]) => {
        setMe(meData);
        setProjects(projectData);
        if (projectData.length) {
          setProjectSlug(projectData[0].key);
          setBrief(`Giới thiệu căn hộ tại dự án ${projectData[0].name}`);
        }
      })
      .catch(() => router.push("/"));
  }, [router]);

  const loadEvidence = useCallback(async () => {
    const data = await api("/api/generation/retrieve", {
      method: "POST",
      body: JSON.stringify({ query: `${projectSlug} ${brief}`, config: retrievalConfig, k: 6 }),
    });
    setEvidence(data.results);
    setPlan(data.plan);
  }, [projectSlug, brief, retrievalConfig]);

  async function run(configs: string[]) {
    setRunning(true);
    setError("");
    try {
      await loadEvidence();
      for (const config of configs) {
        const result = await api("/api/generation", {
          method: "POST",
          body: JSON.stringify({
            brief,
            channel,
            persona,
            config,
            retrieval_config: retrievalConfig,
            project_slug: projectSlug || null,
            k: 6,
          }),
        });
        if (config === "A") setGenA(result);
        else setGenB(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sinh nội dung thất bại");
    } finally {
      setRunning(false);
    }
  }

  const canRun = me?.role === "admin" || me?.role === "marketer";

  return (
    <main className="container" style={{ maxWidth: 1180 }}>
      <TopBar me={me} />

      <div className="card">
        <h1>Content Studio</h1>
        <p className="hint">
          A = prompt-only · B = RAG (cùng prompt, cùng model, cùng seed — chỉ khác khối dữ kiện
          truy xuất). Mọi câu có số liệu đều được đối chiếu ngược về fact có nguồn.
        </p>
        <div className="row">
          <div style={{ flex: 2, minWidth: 240 }}>
            <label htmlFor="project">Dự án</label>
            <select
              id="project"
              value={projectSlug}
              onChange={(e) => {
                setProjectSlug(e.target.value);
                const found = projects.find((p) => p.key === e.target.value);
                if (found) setBrief(`Giới thiệu căn hộ tại dự án ${found.name}`);
              }}
            >
              {projects.map((p) => (
                <option key={p.id} value={p.key}>
                  {p.name} — {p.support_count} tin
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="channel">Kênh</label>
            <select id="channel" value={channel} onChange={(e) => setChannel(e.target.value)}>
              {CHANNELS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="persona">Khách hàng</label>
            <select id="persona" value={persona} onChange={(e) => setPersona(e.target.value)}>
              {PERSONAS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="retrieval">Truy xuất (cho B)</label>
            <select
              id="retrieval"
              value={retrievalConfig}
              onChange={(e) => setRetrievalConfig(e.target.value)}
            >
              <option value="R3">R3 — hybrid + graph</option>
              <option value="R1">R1 — bm25 + vector</option>
              <option value="R2">R2 — graph only</option>
            </select>
          </div>
        </div>
        <label htmlFor="brief">Yêu cầu nội dung</label>
        <textarea id="brief" rows={2} value={brief} onChange={(e) => setBrief(e.target.value)} />
        {canRun && (
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={() => run(["A", "B"])} disabled={running}>
              {running ? "Đang sinh…" : "Chạy A và B"}
            </button>
            <button className="secondary" onClick={() => run(["B"])} disabled={running}>
              Chỉ chạy B (RAG)
            </button>
            <button className="secondary" onClick={() => loadEvidence().catch(() => undefined)}>
              Xem trước dữ kiện
            </button>
          </div>
        )}
        {error && <p className="error">{error}</p>}
        {running && (
          <p className="hint" style={{ marginTop: 8 }}>
            Model chạy trên GPU máy local nên mỗi bài mất khoảng 1–3 phút.
          </p>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
        <div className="card" style={{ marginTop: 0 }}>
          <h2>A — prompt-only</h2>
          <p className="hint">Không có dữ kiện truy xuất.</p>
          <Output gen={genA} />
          {genA && (
            <>
              <h3 style={{ fontSize: 14, marginTop: 12 }}>Đối chiếu claim</h3>
              <ClaimList claims={genA.claims} />
            </>
          )}
        </div>
        <div className="card" style={{ marginTop: 0 }}>
          <h2>B — RAG ({retrievalConfig})</h2>
          <p className="hint">{plan?.explain ?? "Có khối dữ kiện truy xuất kèm nguồn."}</p>
          <Output gen={genB} />
          {genB && (
            <>
              <h3 style={{ fontSize: 14, marginTop: 12 }}>Đối chiếu claim</h3>
              <ClaimList claims={genB.claims} />
            </>
          )}
        </div>
      </div>

      <div className="card">
        <h2>Evidence panel</h2>
        <p className="hint">
          Dữ kiện mà cấu hình B nhìn thấy — mỗi dòng truy được về tin gốc. Đường đi graph
          giải thích vì sao tin được chọn.
        </p>
        {genB?.graph_paths?.length ? (
          <div style={{ marginBottom: 12 }}>
            {genB.graph_paths.map((path, i) => (
              <div key={i} className="path" style={{ marginBottom: 4 }}>
                {path.map((node, j) =>
                  node.startsWith("--") ? (
                    <span key={j} className="edge">
                      {node}
                    </span>
                  ) : (
                    <span key={j} className={j === 0 ? "node project" : "node"}>
                      {node}
                    </span>
                  )
                )}
              </div>
            ))}
          </div>
        ) : null}
        <table>
          <thead>
            <tr>
              <th>Loại</th>
              <th>Nguồn lấy</th>
              <th>Nội dung</th>
              <th>Điểm</th>
            </tr>
          </thead>
          <tbody>
            {evidence.map((item) => (
              <tr key={item.chunk_id}>
                <td>
                  <span className="chip mute">{item.chunk_type}</span>
                </td>
                <td>
                  <span className="chip">{item.retriever}</span>
                </td>
                <td>
                  <div style={{ fontSize: 13 }}>{item.text.slice(0, 180)}</div>
                  <a className="src" href={item.source_url} target="_blank" rel="noreferrer">
                    {item.source_url}
                  </a>
                </td>
                <td>{item.score.toFixed(4)}</td>
              </tr>
            ))}
            {evidence.length === 0 && (
              <tr>
                <td colSpan={4} style={{ color: "var(--muted)" }}>
                  Bấm "Xem trước dữ kiện" hoặc chạy B để xem.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
