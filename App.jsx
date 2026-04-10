import { useState, useEffect, useCallback } from "react";

const API = "http://localhost:8000/api/v1";

// ── Colour tokens ──────────────────────────────────────────────
const C = {
  bg: "var(--color-background-primary)",
  surface: "var(--color-background-secondary)",
  border: "var(--color-border-tertiary)",
  borderMd: "var(--color-border-secondary)",
  text: "var(--color-text-primary)",
  muted: "var(--color-text-secondary)",
  hint: "var(--color-text-tertiary)",
  success: "var(--color-background-success)",
  successText: "var(--color-text-success)",
  warn: "var(--color-background-warning)",
  warnText: "var(--color-text-warning)",
  danger: "var(--color-background-danger)",
  dangerText: "var(--color-text-danger)",
  info: "var(--color-background-info)",
  infoText: "var(--color-text-info)",
};

// ── Tiny helpers ───────────────────────────────────────────────
const fmt = (n) => typeof n === "number" ? `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}` : "—";
const card = { background: C.bg, border: `0.5px solid ${C.border}`, borderRadius: 12, padding: "16px 20px" };
const metric = { background: C.surface, borderRadius: 8, padding: "12px 16px", flex: 1 };

function Badge({ type = "info", children }) {
  const styles = {
    info:    { background: C.info,    color: C.infoText },
    success: { background: C.success, color: C.successText },
    warn:    { background: C.warn,    color: C.warnText },
    danger:  { background: C.danger,  color: C.dangerText },
  };
  return (
    <span style={{ ...styles[type], fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: 4, whiteSpace: "nowrap" }}>
      {children}
    </span>
  );
}

function Loader() {
  return <div style={{ color: C.muted, fontSize: 13, padding: "40px 0", textAlign: "center" }}>Loading…</div>;
}

function ErrorMsg({ msg }) {
  return (
    <div style={{ background: C.danger, color: C.dangerText, borderRadius: 8, padding: "10px 14px", fontSize: 13, margin: "12px 0" }}>
      {msg}
    </div>
  );
}

// ── Order Submit Form ──────────────────────────────────────────
function SubmitOrder({ onSuccess }) {
  const [form, setForm] = useState({ shopkeeper_name: "", shopkeeper_phone: "", raw_text: "", source: "api" });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async () => {
    if (!form.raw_text.trim()) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const res = await fetch(`${API}/orders/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      setResult(data);
      if (data.success) { setForm((f) => ({ ...f, raw_text: "" })); onSuccess?.(); }
    } catch (e) {
      setError("Could not reach the API. Is the server running?");
    } finally {
      setLoading(false);
    }
  };

  const preview = async () => {
    if (!form.raw_text.trim()) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const res = await fetch(`${API}/orders/parse-preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      setResult({ ...data, _preview: true });
    } catch (e) {
      setError("Could not reach the API.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={card}>
      <p style={{ fontSize: 13, fontWeight: 500, color: C.text, marginBottom: 14 }}>Submit order</p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
        <div>
          <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 4 }}>Shopkeeper name</label>
          <input value={form.shopkeeper_name} onChange={set("shopkeeper_name")} placeholder="Ram General Store" style={{ width: "100%", fontSize: 13 }} />
        </div>
        <div>
          <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 4 }}>Phone</label>
          <input value={form.shopkeeper_phone} onChange={set("shopkeeper_phone")} placeholder="9876543210" style={{ width: "100%", fontSize: 13 }} />
        </div>
      </div>
      <div style={{ marginBottom: 10 }}>
        <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 4 }}>Order text</label>
        <textarea
          value={form.raw_text}
          onChange={set("raw_text")}
          rows={5}
          placeholder={"Sugar 5 kg @40\nRice 10 kg 35\nDal Chana 25 kg rate 65"}
          style={{ width: "100%", fontSize: 13, fontFamily: "var(--font-mono)", resize: "vertical" }}
        />
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={preview} disabled={loading} style={{ fontSize: 13 }}>Preview parse</button>
        <button onClick={submit} disabled={loading || !form.raw_text.trim()} style={{ fontSize: 13 }}>
          {loading ? "Saving…" : "Save to Sheets →"}
        </button>
      </div>

      {error && <ErrorMsg msg={error} />}

      {result && (
        <div style={{ marginTop: 14, background: C.surface, borderRadius: 8, padding: "12px 14px", fontSize: 13 }}>
          {result._preview ? (
            <>
              <p style={{ fontWeight: 500, color: C.text, marginBottom: 8 }}>Parse preview — {result.item_count} item(s)</p>
              {result.items?.map((item, i) => (
                <div key={i} style={{ display: "flex", gap: 10, padding: "4px 0", borderBottom: `0.5px solid ${C.border}`, fontSize: 12 }}>
                  <span style={{ color: C.text, minWidth: 140 }}>{item.item_name}</span>
                  <span style={{ color: C.muted }}>{item.quantity} {item.unit || ""}</span>
                  <span style={{ color: C.muted, marginLeft: "auto" }}>{item.price_per_unit ? `₹${item.price_per_unit}` : "no price"}</span>
                </div>
              ))}
              {result.warnings?.length > 0 && (
                <div style={{ marginTop: 8, color: C.warnText, background: C.warn, borderRadius: 6, padding: "6px 10px" }}>
                  {result.warnings.join(" · ")}
                </div>
              )}
            </>
          ) : (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <Badge type={result.success ? "success" : result.duplicate_detected ? "warn" : "danger"}>
                  {result.success ? "Saved" : result.duplicate_detected ? "Duplicate" : "Failed"}
                </Badge>
                <span style={{ color: C.text }}>{result.message}</span>
              </div>
              {result.order_id && <p style={{ color: C.muted, fontSize: 12 }}>Order ID: {result.order_id}</p>}
              {result.warnings?.length > 0 && <p style={{ color: C.warnText, fontSize: 12, marginTop: 4 }}>{result.warnings.join(" · ")}</p>}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Summary Metrics ────────────────────────────────────────────
function Summary({ refresh }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/analytics/summary`);
      setData(await res.json());
    } catch { setErr("Could not load summary."); }
  }, []);

  useEffect(() => { load(); }, [refresh, load]);

  if (err) return <ErrorMsg msg={err} />;
  if (!data) return <Loader />;

  const metrics = [
    { label: "Total orders", value: data.unique_orders },
    { label: "Line items", value: data.total_line_items },
    { label: "Shopkeepers", value: data.active_shopkeepers },
    { label: "Revenue", value: fmt(data.total_revenue) },
  ];

  return (
    <div>
      <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
        {metrics.map((m) => (
          <div key={m.label} style={metric}>
            <p style={{ fontSize: 11, color: C.muted, marginBottom: 4 }}>{m.label}</p>
            <p style={{ fontSize: 22, fontWeight: 500, color: C.text }}>{m.value}</p>
          </div>
        ))}
      </div>
      {data.top_items?.length > 0 && (
        <div style={card}>
          <p style={{ fontSize: 13, fontWeight: 500, color: C.text, marginBottom: 10 }}>Top items by quantity</p>
          {data.top_items.map((item, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: C.muted, minWidth: 16 }}>{i + 1}</span>
              <span style={{ fontSize: 13, color: C.text, flex: 1 }}>{item.item}</span>
              <span style={{ fontSize: 12, color: C.muted }}>{item.total_qty} units</span>
              <div style={{ width: 80, height: 4, background: C.surface, borderRadius: 4, overflow: "hidden" }}>
                <div style={{ width: `${Math.min(100, (item.total_qty / data.top_items[0].total_qty) * 100)}%`, height: "100%", background: "#1D9E75", borderRadius: 4 }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Recent Orders ──────────────────────────────────────────────
function RecentOrders({ refresh }) {
  const [data, setData] = useState(null);
  const [days, setDays] = useState(7);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    setData(null);
    fetch(`${API}/analytics/recent?days=${days}`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  }, [days, refresh]);

  return (
    <div style={card}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
        <p style={{ fontSize: 13, fontWeight: 500, color: C.text, flex: 1 }}>Recent orders</p>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={{ fontSize: 12 }}>
          <option value={3}>Last 3 days</option>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
        </select>
      </div>

      {!data ? <Loader /> : data.orders.length === 0 ? (
        <p style={{ fontSize: 13, color: C.muted, textAlign: "center", padding: "20px 0" }}>No orders in this period</p>
      ) : (
        data.orders.map((order) => (
          <div key={order.order_id} style={{ borderBottom: `0.5px solid ${C.border}`, paddingBottom: 10, marginBottom: 10 }}>
            <div
              style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}
              onClick={() => setExpanded(expanded === order.order_id ? null : order.order_id)}
            >
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: 13, fontWeight: 500, color: C.text }}>{order.shopkeeper_name || "Unknown"}</p>
                <p style={{ fontSize: 11, color: C.muted }}>{order.order_id} · {order.date?.slice(0, 16)}</p>
              </div>
              <Badge type={order.source === "whatsapp" ? "success" : "info"}>{order.source}</Badge>
              <span style={{ fontSize: 13, color: C.text, fontWeight: 500 }}>{fmt(order.order_total)}</span>
              <span style={{ fontSize: 12, color: C.hint }}>{expanded === order.order_id ? "▲" : "▼"}</span>
            </div>
            {expanded === order.order_id && (
              <div style={{ marginTop: 10, background: C.surface, borderRadius: 8, overflow: "hidden" }}>
                <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ borderBottom: `0.5px solid ${C.border}` }}>
                      {["Item", "Qty", "Unit", "Price/unit", "Total"].map((h) => (
                        <th key={h} style={{ padding: "6px 10px", textAlign: "left", color: C.muted, fontWeight: 500 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {order.items.map((item, i) => (
                      <tr key={i} style={{ borderBottom: `0.5px solid ${C.border}` }}>
                        <td style={{ padding: "6px 10px", color: C.text }}>{item.item_name}</td>
                        <td style={{ padding: "6px 10px", color: C.muted }}>{item.quantity}</td>
                        <td style={{ padding: "6px 10px", color: C.muted }}>{item.unit || "—"}</td>
                        <td style={{ padding: "6px 10px", color: C.muted }}>{item.price_per_unit ? `₹${item.price_per_unit}` : "—"}</td>
                        <td style={{ padding: "6px 10px", color: C.text, fontWeight: 500 }}>{item.total_price ? fmt(item.total_price) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

// ── Shopkeepers List ───────────────────────────────────────────
function Shopkeepers({ refresh }) {
  const [data, setData] = useState(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch(`${API}/analytics/shopkeepers`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  }, [refresh]);

  const list = data?.shopkeepers?.filter((s) =>
    s.name.toLowerCase().includes(search.toLowerCase())
  ) ?? [];

  return (
    <div style={card}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <p style={{ fontSize: 13, fontWeight: 500, color: C.text, flex: 1 }}>Shopkeepers</p>
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search…" style={{ fontSize: 12, width: 140 }} />
      </div>
      {!data ? <Loader /> : list.length === 0 ? (
        <p style={{ fontSize: 13, color: C.muted, textAlign: "center", padding: "20px 0" }}>No shopkeepers found</p>
      ) : (
        list.map((s, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: `0.5px solid ${C.border}` }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", background: C.info, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 500, color: C.infoText, flexShrink: 0 }}>
              {s.name.slice(0, 2).toUpperCase()}
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: 13, color: C.text, fontWeight: 500 }}>{s.name}</p>
              <p style={{ fontSize: 11, color: C.muted }}>{s.phone || "no phone"} · {s.total_orders} order(s)</p>
            </div>
            <span style={{ fontSize: 13, fontWeight: 500, color: C.text }}>{fmt(s.total_spent)}</span>
          </div>
        ))
      )}
    </div>
  );
}

// ── Root App ───────────────────────────────────────────────────
const TABS = ["Overview", "Submit order", "Recent orders", "Shopkeepers"];

export default function App() {
  const [tab, setTab] = useState("Overview");
  const [refresh, setRefresh] = useState(0);

  const onSuccess = () => { setRefresh((r) => r + 1); setTab("Recent orders"); };

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "1.5rem 0", fontFamily: "var(--font-sans)" }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, color: C.text, marginBottom: 4 }}>Wholesale Orders</h1>
        <p style={{ fontSize: 13, color: C.muted }}>Order capture · Google Sheets sync · Analytics</p>
      </div>

      <div style={{ display: "flex", gap: 4, marginBottom: 20, flexWrap: "wrap" }}>
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{ fontSize: 13, background: tab === t ? C.surface : "transparent", borderColor: tab === t ? C.borderMd : C.border, color: tab === t ? C.text : C.muted }}
          >
            {t}
          </button>
        ))}
        <button onClick={() => setRefresh((r) => r + 1)} style={{ fontSize: 13, marginLeft: "auto", color: C.muted }}>↻ Refresh</button>
      </div>

      {tab === "Overview"       && <Summary refresh={refresh} />}
      {tab === "Submit order"   && <SubmitOrder onSuccess={onSuccess} />}
      {tab === "Recent orders"  && <RecentOrders refresh={refresh} />}
      {tab === "Shopkeepers"    && <Shopkeepers refresh={refresh} />}
    </div>
  );
}
