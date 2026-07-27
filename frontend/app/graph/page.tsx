"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopBar from "@/components/TopBar";
import { api } from "@/lib/api";

type Me = { email: string; role: string };
type Entity = { id: string; type: string; key: string; name: string; support_count: number };
type PathNode = { id: string; type: string; key: string; name: string };
type PathEdge = { type: string; direction: string; source_url: string; valid_from: string; valid_to: string };
type Path = { depth: number; nodes: PathNode[]; edges: PathEdge[] };
type ProjectPaths = { project: Entity; paths: Path[]; n_via_building: number; n_direct: number };
type Listing = {
  id: string;
  title_clean: string;
  bedrooms: number | null;
  area_m2: number | null;
  total_price_vnd: number | null;
  price_confidence: string;
  building_code: string | null;
  legal_facts: string[];
  amenities: string[];
};
type Fact = {
  id: string;
  predicate: string;
  value_text: string;
  unit: string;
  confidence: number;
  needs_review: boolean;
  source_url: string;
  evidence: string;
  valid_from: string;
  valid_to: string;
};

function tien(vnd: number | null) {
  if (!vnd) return "—";
  return vnd >= 1e9 ? `${(vnd / 1e9).toFixed(2)} tỷ` : `${Math.round(vnd / 1e6)} triệu`;
}

export default function GraphPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [projects, setProjects] = useState<Entity[]>([]);
  const [selected, setSelected] = useState("");
  const [paths, setPaths] = useState<ProjectPaths | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [openListing, setOpenListing] = useState("");
  const [onlyBuilding, setOnlyBuilding] = useState(false);

  useEffect(() => {
    api("/api/auth/me")
      .then(setMe)
      .catch(() => router.push("/"));
  }, [router]);

  useEffect(() => {
    api(`/api/graph/entities?entity_type=Project&limit=100&with_building=${onlyBuilding}`)
      .then((data: Entity[]) => {
        setProjects(data);
        if (data.length > 0) setSelected(data[0].key);
      })
      .catch(() => undefined);
  }, [onlyBuilding]);

  const loadProject = useCallback(async (key: string) => {
    const [pathData, listingData] = await Promise.all([
      api(`/api/graph/projects/${key}/paths`),
      api(`/api/listings?project_slug=${key}&limit=20`),
    ]);
    setPaths(pathData);
    setListings(listingData);
    setFacts([]);
    setOpenListing("");
  }, []);

  useEffect(() => {
    if (selected) loadProject(selected).catch(() => undefined);
  }, [selected, loadProject]);

  async function showFacts(listingId: string) {
    if (openListing === listingId) {
      setOpenListing("");
      return;
    }
    setFacts(await api(`/api/listings/${listingId}/facts`));
    setOpenListing(listingId);
  }

  return (
    <main className="container">
      <TopBar me={me} />

      <div className="card">
        <h1>Property Knowledge Graph</h1>
        <p className="hint">
          Node và cạnh sinh tất định từ dữ liệu đã làm sạch (không do LLM suy ra). Mỗi cạnh truy được
          về tin nguồn. Truy vấn giới hạn ≤2 hop bằng recursive CTE trên PostgreSQL.
        </p>
        <div className="row">
          <div>
            <label htmlFor="project">Dự án ({projects.length} dự án trong graph)</label>
            <select id="project" value={selected} onChange={(e) => setSelected(e.target.value)}>
              {projects.map((p) => (
                <option key={p.id} value={p.key}>
                  {p.name} — {p.support_count} tin
                </option>
              ))}
            </select>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 6, margin: 0, paddingBottom: 12 }}>
            <input
              type="checkbox"
              style={{ width: "auto" }}
              checked={onlyBuilding}
              onChange={(e) => setOnlyBuilding(e.target.checked)}
            />
            Chỉ dự án đã nhận diện được tòa/block
          </label>
        </div>
      </div>

      {paths && (
        <div className="card">
          <h2>Đường đi Project → Building → UnitType</h2>
          <p className="hint">
            {paths.n_via_building} đường qua tòa/block · {paths.n_direct} đường trực tiếp tới loại căn
            (dự án chưa nhận diện được mã tòa).
          </p>
          {paths.paths.map((path, index) => (
            <div key={index} style={{ padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
              <div className="path">
                {path.nodes.map((node, i) => (
                  <span key={node.id} style={{ display: "contents" }}>
                    {i > 0 && <span className="edge">──{path.edges[i - 1].type}──▶</span>}
                    <span className={i === 0 ? "node project" : "node"}>
                      {node.name}
                      <span style={{ color: "var(--muted)", fontSize: 11 }}> · {node.type}</span>
                    </span>
                  </span>
                ))}
              </div>
              <div className="src" style={{ marginTop: 4 }}>
                Nguồn:{" "}
                <a href={path.edges[0].source_url} target="_blank" rel="noreferrer">
                  {path.edges[0].source_url}
                </a>
                {path.edges[0].valid_to && (
                  <span className="chip warn" style={{ marginLeft: 8 }}>
                    hết hiệu lực {path.edges[0].valid_to}
                  </span>
                )}
              </div>
            </div>
          ))}
          {paths.paths.length === 0 && <p className="hint">Dự án này chưa có đường đi nào.</p>}
        </div>
      )}

      <div className="card">
        <h2>Tin đã làm sạch của dự án ({listings.length})</h2>
        <p className="hint">Bấm một tin để xem canonical facts kèm bằng chứng và nguồn.</p>
        <table>
          <thead>
            <tr>
              <th>Tiêu đề</th>
              <th>PN</th>
              <th>Diện tích</th>
              <th>Giá</th>
              <th>Tòa</th>
            </tr>
          </thead>
          <tbody>
            {listings.map((row) => (
              <tr key={row.id} onClick={() => showFacts(row.id)} style={{ cursor: "pointer" }}>
                <td>
                  <b>{row.title_clean.slice(0, 70)}</b>
                  {openListing === row.id && (
                    <div style={{ marginTop: 8 }}>
                      {facts.map((fact) => (
                        <div key={fact.id} style={{ marginBottom: 6 }}>
                          <span className={fact.needs_review ? "chip warn" : "chip"}>
                            {fact.predicate}: {fact.value_text} {fact.unit}
                          </span>
                          <span className="src">
                            {" "}
                            {fact.evidence.slice(0, 90)} · độ tin {fact.confidence}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </td>
                <td>{row.bedrooms ?? "—"}</td>
                <td>{row.area_m2 ? `${row.area_m2} m²` : "—"}</td>
                <td>
                  {tien(row.total_price_vnd)}
                  <span className="chip mute" style={{ marginLeft: 6 }}>
                    {row.price_confidence}
                  </span>
                </td>
                <td>{row.building_code ?? "—"}</td>
              </tr>
            ))}
            {listings.length === 0 && (
              <tr>
                <td colSpan={5} style={{ color: "var(--muted)" }}>
                  Chưa có tin nào cho dự án này.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
