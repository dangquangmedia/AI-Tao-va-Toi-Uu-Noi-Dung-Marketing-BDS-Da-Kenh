"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopBar from "@/components/TopBar";
import { API_BASE, api, getToken } from "@/lib/api";

type Me = { email: string; role: string };
type Claim = { text: string; status: string; reason: string };
type Version = {
  id: string;
  version_no: number;
  generation_id: string | null;
  config: string;
  model_name: string;
  adapter_name: string;
  prompt_version: string;
  headline: string;
  body: string;
  cta: string;
  edited_by_human: boolean;
  claims: Claim[];
  metrics: Record<string, number>;
  status: string;
  review_note: string;
  reviewed_at: string | null;
  created_at: string;
};
type Item = {
  id: string;
  project_slug: string | null;
  channel: string;
  persona: string;
  title: string;
  status: string;
  current_version: number;
  updated_at: string;
};
type Detail = Item & { versions: Version[] };

const STATUS_LABELS: Record<string, string> = {
  draft: "nháp",
  in_review: "chờ duyệt",
  approved: "đã duyệt",
  rejected: "bị từ chối",
};
const FILTERS = [
  { value: "", label: "Tất cả" },
  { value: "in_review", label: "Chờ duyệt" },
  { value: "draft", label: "Nháp" },
  { value: "approved", label: "Đã duyệt" },
  { value: "rejected", label: "Bị từ chối" },
];

function StatusChip({ status }: { status: string }) {
  const kind = status === "approved" ? "chip" : status === "rejected" ? "chip warn" : "chip mute";
  return <span className={kind}>{STATUS_LABELS[status] ?? status}</span>;
}

export default function ReviewPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [filter, setFilter] = useState("in_review");
  const [detail, setDetail] = useState<Detail | null>(null);
  const [note, setNote] = useState("");
  const [draft, setDraft] = useState({ headline: "", body: "", cta: "" });
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadList = useCallback(async (status: string) => {
    const rows = await api(`/api/content${status ? `?status=${status}` : ""}`);
    setItems(rows);
    return rows as Item[];
  }, []);

  const openItem = useCallback(async (id: string) => {
    const data: Detail = await api(`/api/content/${id}`);
    setDetail(data);
    setEditing(false);
    setNote("");
    const latest = data.versions[data.versions.length - 1];
    if (latest) setDraft({ headline: latest.headline, body: latest.body, cta: latest.cta });
  }, []);

  useEffect(() => {
    api("/api/auth/me")
      .then((data: Me) => setMe(data))
      .catch(() => router.push("/"));
  }, [router]);

  useEffect(() => {
    loadList(filter)
      .then((rows) => {
        const wanted = new URLSearchParams(window.location.search).get("item");
        if (wanted) return openItem(wanted);
        if (rows.length && !detail) return openItem(rows[0].id);
      })
      .catch((err) => setError(err.message));
    // detail cố ý không nằm trong deps: mở lại danh sách không được nhảy khỏi bài đang xem
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, loadList, openItem]);

  async function act(path: string, body?: unknown) {
    if (!detail) return;
    setBusy(true);
    setError("");
    try {
      await api(`/api/content/${detail.id}/${path}`, {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
      });
      await openItem(detail.id);
      await loadList(filter);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Thao tác thất bại");
    } finally {
      setBusy(false);
    }
  }

  /** Tải file xuất bản — dùng fetch tay vì endpoint trả markdown chứ không phải JSON. */
  async function exportMarkdown() {
    if (!detail) return;
    setError("");
    const res = await fetch(`${API_BASE}/api/content/${detail.id}/export`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      setError(payload.detail ?? "Không xuất được");
      return;
    }
    const url = URL.createObjectURL(await res.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `${detail.id}-v${detail.current_version}.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const latest = detail?.versions[detail.versions.length - 1] ?? null;
  const canEdit = me?.role === "admin" || me?.role === "marketer";
  const canReview = me?.role === "admin" || me?.role === "reviewer";
  const unsupported = latest?.claims?.filter((c) => c.status !== "supported") ?? [];

  return (
    <main className="container" style={{ maxWidth: 1180 }}>
      <TopBar me={me} />

      <div className="card">
        <h1>Duyệt nội dung</h1>
        <p className="hint">
          Hàng rào cuối trước khi nội dung ra ngoài. Mỗi lần sửa tạo một phiên bản mới — bản đã
          duyệt không bao giờ bị ghi đè. Từ chối bắt buộc kèm lý do, và người viết không tự duyệt
          bài của mình.
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {FILTERS.map((f) => (
            <button
              key={f.value}
              className={filter === f.value ? "" : "secondary"}
              onClick={() => setFilter(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>
        {error && <p className="error">{error}</p>}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 16, marginTop: 16 }}>
        <div className="card" style={{ marginTop: 0 }}>
          <h2>Hàng chờ ({items.length})</h2>
          {items.length === 0 && <p className="hint">Không có nội dung nào ở trạng thái này.</p>}
          {items.map((item) => (
            <div
              key={item.id}
              onClick={() => openItem(item.id)}
              style={{
                padding: "8px 0",
                borderBottom: "1px solid var(--line)",
                cursor: "pointer",
                opacity: detail?.id === item.id ? 1 : 0.75,
              }}
            >
              <div style={{ fontSize: 14, fontWeight: detail?.id === item.id ? 600 : 400 }}>
                {item.title || "(chưa có tiêu đề)"}
              </div>
              <div style={{ marginTop: 4 }}>
                <StatusChip status={item.status} />
                <span className="chip mute">{item.channel}</span>
                <span className="chip mute">v{item.current_version}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="card" style={{ marginTop: 0 }}>
          {!detail || !latest ? (
            <p className="hint">Chọn một nội dung ở cột trái.</p>
          ) : (
            <>
              <h2>{detail.title || "(chưa có tiêu đề)"}</h2>
              <div style={{ marginBottom: 10 }}>
                <StatusChip status={detail.status} />
                <span className="chip mute">phiên bản {latest.version_no}</span>
                <span className="chip mute">{detail.channel}</span>
                <span className="chip mute">{detail.persona}</span>
                {latest.config && <span className="chip mute">cấu hình {latest.config}</span>}
                <span className="chip mute">{latest.model_name}</span>
                {latest.adapter_name && <span className="chip">adapter {latest.adapter_name}</span>}
                {latest.edited_by_human && <span className="chip">người sửa</span>}
                <span className={unsupported.length ? "chip warn" : "chip"}>
                  {unsupported.length} claim chưa có căn cứ
                </span>
              </div>

              {editing ? (
                <>
                  <label htmlFor="headline">Tiêu đề</label>
                  <input
                    id="headline"
                    value={draft.headline}
                    onChange={(e) => setDraft({ ...draft, headline: e.target.value })}
                  />
                  <label htmlFor="body">Thân bài</label>
                  <textarea
                    id="body"
                    rows={10}
                    value={draft.body}
                    onChange={(e) => setDraft({ ...draft, body: e.target.value })}
                  />
                  <label htmlFor="cta">CTA</label>
                  <input
                    id="cta"
                    value={draft.cta}
                    onChange={(e) => setDraft({ ...draft, cta: e.target.value })}
                  />
                  <div style={{ display: "flex", gap: 10 }}>
                    <button disabled={busy} onClick={() => act("versions", draft).then(() => setEditing(false))}>
                      Lưu thành phiên bản mới
                    </button>
                    <button className="secondary" onClick={() => setEditing(false)}>
                      Hủy
                    </button>
                  </div>
                  <p className="hint">
                    Bản sửa được chấm lại claim trên đúng tập dữ kiện của lần sinh gốc — người viết
                    thêm số không có căn cứ cũng bị bắt như model.
                  </p>
                </>
              ) : (
                <>
                  <h3 style={{ fontFamily: "Cambria, Georgia, serif", fontSize: 18 }}>
                    {latest.headline || "(không có headline)"}
                  </h3>
                  <div style={{ whiteSpace: "pre-wrap", fontSize: 14, lineHeight: 1.65 }}>
                    {latest.body}
                  </div>
                  {latest.cta && <p style={{ marginTop: 8, fontWeight: 600 }}>{latest.cta}</p>}
                </>
              )}

              {latest.review_note && (
                <p className="error" style={{ marginTop: 10 }}>
                  Ý kiến người duyệt: {latest.review_note}
                </p>
              )}

              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 14 }}>
                {canEdit && detail.status !== "approved" && !editing && (
                  <button className="secondary" onClick={() => setEditing(true)}>
                    Sửa nội dung
                  </button>
                )}
                {canEdit && detail.status !== "in_review" && detail.status !== "approved" && (
                  <button disabled={busy} onClick={() => act("submit")}>
                    Gửi duyệt
                  </button>
                )}
                {canReview && detail.status === "in_review" && (
                  <>
                    <button disabled={busy} onClick={() => act("review", { approve: true, note })}>
                      Duyệt
                    </button>
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={() => act("review", { approve: false, note })}
                    >
                      Từ chối
                    </button>
                  </>
                )}
                {detail.status === "approved" && (
                  <button className="secondary" onClick={exportMarkdown}>
                    Xuất bản (.md)
                  </button>
                )}
              </div>
              {canReview && detail.status === "in_review" && (
                <>
                  <label htmlFor="note">Ý kiến (bắt buộc khi từ chối)</label>
                  <input id="note" value={note} onChange={(e) => setNote(e.target.value)} />
                </>
              )}

              <h3 style={{ fontSize: 14, marginTop: 16 }}>Đối chiếu claim</h3>
              {latest.claims?.length ? (
                latest.claims.map((claim, i) => (
                  <div key={i} style={{ marginBottom: 6 }}>
                    <span className={claim.status === "supported" ? "chip" : "chip warn"}>
                      {claim.status === "supported" ? "có căn cứ" : claim.status}
                    </span>{" "}
                    <span style={{ fontSize: 13 }}>{claim.text}</span>
                    {claim.reason && <div className="src">↳ {claim.reason}</div>}
                  </div>
                ))
              ) : (
                <p className="hint">Không có claim nào cần kiểm chứng.</p>
              )}

              <h3 style={{ fontSize: 14, marginTop: 16 }}>Lịch sử phiên bản</h3>
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Nguồn</th>
                    <th>Trạng thái</th>
                    <th>Claim chưa có căn cứ</th>
                    <th>Thời điểm</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.versions.map((v) => (
                    <tr key={v.id}>
                      <td>v{v.version_no}</td>
                      <td>
                        {v.edited_by_human ? (
                          <span className="chip mute">người sửa</span>
                        ) : (
                          <span className="chip mute">model {v.config}</span>
                        )}
                      </td>
                      <td>
                        <StatusChip status={v.status} />
                      </td>
                      <td>{v.claims?.filter((c) => c.status !== "supported").length ?? 0}</td>
                      <td className="src">{new Date(v.created_at).toLocaleString("vi-VN")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
