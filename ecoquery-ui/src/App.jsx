// ecoquery-ui/src/App.jsx

import { useState, useEffect, useCallback } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

const PROVINCE_YEARS = [2024, 2025];
const DEFAULT_YEAR = 2025;

function co2Color(g) {
  if (g < 100) return "#22c55e";
  if (g < 300) return "#eab308";
  if (g < 600) return "#f97316";
  return "#ef4444";
}

function waterColor(ml) {
  if (ml < 2) return "#22c55e";
  if (ml < 4) return "#eab308";
  if (ml < 7) return "#f97316";
  return "#ef4444";
}

export default function App() {
  const [tab, setTab]             = useState("province");
  const [location, setLocation]   = useState("");
  const [year, setYear]           = useState(DEFAULT_YEAR);
  const [result, setResult]       = useState(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);
  const [provinces, setProvinces] = useState([]);
  const [countries, setCountries] = useState([]);
  const [listLoading, setListLoading] = useState(false);

  useEffect(() => {
    setResult(null);
    setError(null);
    setLocation("");
    setListLoading(true);

    const url =
      tab === "province"
        ? `${API_BASE}/provinces?year=${year}`
        : `${API_BASE}/countries`;

    fetch(url)
      .then(r => r.json())
      .then(data => {
        if (tab === "province") setProvinces(data.provinces || []);
        else setCountries(data.countries || []);
      })
      .catch(() => setError("Could not load data from server."))
      .finally(() => setListLoading(false));
  }, [tab, year]);

  const query = useCallback(
    (loc = location) => {
      if (!loc) return;
      setLoading(true);
      setError(null);
      setResult(null);

      const yearParam = tab === "province" ? `&year=${year}` : "";
      fetch(`${API_BASE}/footprint?location=${encodeURIComponent(loc)}${yearParam}`)
        .then(r => {
          if (!r.ok) return r.json().then(d => { throw new Error(d.error || r.statusText); });
          return r.json();
        })
        .then(setResult)
        .catch(e => setError(e.message))
        .finally(() => setLoading(false));
    },
    [location, tab, year]
  );

  const listItems = tab === "province" ? provinces : countries;

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>🌿 EcoQuery</h1>
        <p style={styles.subtitle}>CO₂ and water footprint per AI inference query</p>
      </header>

      <div style={styles.tabs}>
        {["province", "country"].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{ ...styles.tabBtn, ...(tab === t ? styles.tabBtnActive : {}) }}
          >
            {t === "province" ? "🇨🇳 Chinese Provinces" : "🌍 World Countries"}
          </button>
        ))}
      </div>

      {tab === "province" && (
        <div style={styles.yearRow}>
          <label style={styles.yearLabel}>Year:</label>
          {PROVINCE_YEARS.map(y => (
            <button
              key={y}
              onClick={() => setYear(y)}
              style={{ ...styles.yearBtn, ...(year === y ? styles.yearBtnActive : {}) }}
            >
              {y}
            </button>
          ))}
          <span style={styles.yearNote}>NBS data · Jan-Feb excluded, scaled x12/10</span>
        </div>
      )}

      <div style={styles.searchRow}>
        <input
          type="text"
          value={location}
          onChange={e => setLocation(e.target.value)}
          onKeyDown={e => e.key === "Enter" && query()}
          placeholder={tab === "province" ? "e.g. Beijing, Sichuan" : "e.g. China, Germany"}
          style={styles.input}
        />
        <button onClick={() => query()} disabled={!location || loading} style={styles.btn}>
          {loading ? "..." : "Estimate"}
        </button>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {result && (
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>
            {result.location}
            <span style={styles.cardYear}> · {result.year}</span>
          </h2>
          <div style={styles.metrics}>
            <Metric label="CO₂ per query"   value={`${result.co2_g} g`}         color={co2Color(result.co2_g)} />
            <Metric label="Water per query"  value={`${result.water_ml} mL`}     color={waterColor(result.water_ml)} />
            <Metric label="Grid intensity"   value={`${result.intensity} gCO₂/kWh`} color="#6366f1" />
          </div>
          <p style={styles.cardNote}>
            Energy: {result.energy_kwh * 1000} Wh/query (Patterson et al. 2021).
            Water: Ren et al. 2025 WUE method (PUE 1.4).
          </p>
        </div>
      )}

      <div style={styles.tableWrap}>
        <h3 style={styles.tableTitle}>
          {tab === "province" ? `All 31 provinces - ${year}` : "All countries (most recent year)"}
        </h3>
        {listLoading ? (
          <p style={styles.loading}>Loading...</p>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>#</th>
                <th style={styles.th}>Location</th>
                <th style={styles.th}>Intensity (gCO₂/kWh)</th>
                <th style={styles.th}>CO₂ / query (g)</th>
              </tr>
            </thead>
            <tbody>
              {listItems.map((item, i) => (
                <tr
                  key={item.name}
                  style={styles.tr(i)}
                  onClick={() => { setLocation(item.name); query(item.name); }}
                  title="Click to estimate"
                >
                  <td style={styles.td}>{i + 1}</td>
                  <td style={{ ...styles.td, fontWeight: 600 }}>{item.name}</td>
                  <td style={styles.td}>{item.intensity}</td>
                  <td style={{ ...styles.td, color: co2Color(item.co2_g) }}>{item.co2_g}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <footer style={styles.footer}>
        GreenInfer + EcoQuery · Data: Ember, NBS, IPCC AR5, Ren et al. 2025 · Open source
      </footer>
    </div>
  );
}

function Metric({ label, value, color }) {
  return (
    <div style={styles.metric}>
      <div style={{ ...styles.metricValue, color }}>{value}</div>
      <div style={styles.metricLabel}>{label}</div>
    </div>
  );
}

const styles = {
  page: {
    fontFamily: "'Inter', system-ui, sans-serif",
    maxWidth: 900,
    margin: "0 auto",
    padding: "24px 16px 48px",
    color: "#1e293b",
    background: "#f8fafc",
    minHeight: "100vh",
  },
  header:   { textAlign: "center", marginBottom: 28 },
  title:    { fontSize: 32, fontWeight: 800, margin: 0, color: "#166534" },
  subtitle: { color: "#64748b", marginTop: 6, fontSize: 15 },

  tabs:        { display: "flex", gap: 8, justifyContent: "center", marginBottom: 20 },
  tabBtn:      { padding: "8px 20px", borderRadius: 8, border: "1.5px solid #cbd5e1", background: "#fff", cursor: "pointer", fontWeight: 500, fontSize: 14, color: "#475569" },
  tabBtnActive:{ background: "#166534", color: "#fff", border: "1.5px solid #166534" },

  yearRow:      { display: "flex", alignItems: "center", gap: 8, justifyContent: "center", marginBottom: 16, flexWrap: "wrap" },
  yearLabel:    { fontWeight: 600, fontSize: 14, color: "#374151" },
  yearBtn:      { padding: "5px 16px", borderRadius: 6, border: "1.5px solid #cbd5e1", background: "#fff", cursor: "pointer", fontWeight: 500, fontSize: 14, color: "#475569" },
  yearBtnActive:{ background: "#0f766e", color: "#fff", border: "1.5px solid #0f766e" },
  yearNote:     { fontSize: 12, color: "#94a3b8" },

  searchRow: { display: "flex", gap: 8, justifyContent: "center", marginBottom: 16 },
  input: { padding: "10px 14px", borderRadius: 8, border: "1.5px solid #cbd5e1", fontSize: 15, width: 280, outline: "none" },
  btn:   { padding: "10px 22px", borderRadius: 8, background: "#166534", color: "#fff", border: "none", fontWeight: 600, fontSize: 15, cursor: "pointer" },

  error: { background: "#fef2f2", border: "1px solid #fecaca", color: "#dc2626", padding: "10px 16px", borderRadius: 8, marginBottom: 16, maxWidth: 560, margin: "0 auto 16px" },

  card:      { background: "#fff", border: "1.5px solid #d1fae5", borderRadius: 12, padding: "20px 24px", maxWidth: 560, margin: "0 auto 28px", boxShadow: "0 2px 8px rgba(0,0,0,.06)" },
  cardTitle: { fontSize: 22, fontWeight: 700, margin: "0 0 16px", color: "#0f172a" },
  cardYear:  { fontWeight: 400, color: "#94a3b8", fontSize: 16 },
  metrics:   { display: "flex", gap: 16, marginBottom: 14, flexWrap: "wrap" },
  metric:    { flex: "1 1 140px", background: "#f8fafc", borderRadius: 8, padding: "12px 16px", textAlign: "center" },
  metricValue: { fontSize: 24, fontWeight: 700 },
  metricLabel: { fontSize: 12, color: "#64748b", marginTop: 4 },
  cardNote:    { fontSize: 12, color: "#94a3b8", margin: 0 },

  tableWrap:  { marginTop: 8 },
  tableTitle: { fontSize: 16, fontWeight: 600, color: "#374151", marginBottom: 10 },
  loading:    { color: "#94a3b8" },
  table:      { width: "100%", borderCollapse: "collapse", fontSize: 14 },
  th:         { textAlign: "left", padding: "8px 12px", borderBottom: "2px solid #e2e8f0", color: "#475569", fontWeight: 600 },
  tr:  i => ({ background: i % 2 === 0 ? "#fff" : "#f8fafc", cursor: "pointer" }),
  td:         { padding: "7px 12px", borderBottom: "1px solid #f1f5f9" },

  footer: { textAlign: "center", color: "#94a3b8", fontSize: 12, marginTop: 40 },
};
