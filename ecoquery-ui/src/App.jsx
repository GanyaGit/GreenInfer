// ecoquery-ui/src/App.jsx

import { useState, useEffect, useCallback, useRef } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

const PROVINCE_YEARS = [2024, 2025];
const DEFAULT_PROVINCE_YEAR = 2025;
const COUNTRY_YEAR_MIN = 2000;
let COUNTRY_YEAR_MAX_INIT = 2025;

function co2Color(g) {
  if (g < 0.1) return "#22c55e";
  if (g < 0.3) return "#eab308";
  if (g < 0.6) return "#f97316";
  return "#ef4444";
}

function waterColor(ml) {
  if (ml < 2) return "#22c55e";
  if (ml < 4) return "#eab308";
  if (ml < 7) return "#f97316";
  return "#ef4444";
}

export default function App() {
  const [tab, setTab]               = useState("province");
  const [location, setLocation]     = useState("");
  const [year, setYear]             = useState(DEFAULT_PROVINCE_YEAR);
  const [countryYear, setCountryYear] = useState(COUNTRY_YEAR_MAX_INIT);
  const [countryMaxYear, setCountryMaxYear] = useState(COUNTRY_YEAR_MAX_INIT);
  const [result, setResult]         = useState(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);
  const [provinces, setProvinces]       = useState([]);
  const [countries, setCountries]       = useState([]);
  const [allCountryNames, setAllCountryNames] = useState([]); // full name list for autocomplete
  const [listLoading, setListLoading]   = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlighted, setHighlighted]  = useState(null);
  const highlightRef = useRef(null);

  // Fetch true max year + full country name list on mount
  useEffect(() => {
    fetch(`${API_BASE}/countries/max_year`)
      .then(r => r.json())
      .then(data => {
        if (data.max_year) {
          setCountryMaxYear(data.max_year);
          setCountryYear(data.max_year);
        }
      })
      .catch(() => {});

    // Load all country names from 2023 (best coverage: 209 countries)
    // This is used only for autocomplete - independent of the selected year
    fetch(`${API_BASE}/countries?year=2023`)
      .then(r => r.json())
      .then(data => setAllCountryNames((data.countries || []).map(c => c.name)))
      .catch(() => {});
  }, []);

  // Scroll highlighted row into view
  useEffect(() => {
    if (highlighted && highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlighted]);

  // Load table data when tab / year changes
  useEffect(() => {
    setResult(null);
    setError(null);
    setLocation("");
    setShowDropdown(false);
    setHighlighted(null);
    setListLoading(true);

    const url =
      tab === "province"
        ? `${API_BASE}/provinces?year=${year}`
        : `${API_BASE}/countries?year=${countryYear}`;

    fetch(url)
      .then(r => r.json())
      .then(data => {
        if (tab === "province") setProvinces(data.provinces || []);
        else setCountries(data.countries || []);
      })
      .catch(() => setError("Could not load data from server."))
      .finally(() => setListLoading(false));
  }, [tab, year, countryYear]);

  const listItems = tab === "province" ? provinces : countries;

  // Autocomplete uses allCountryNames for countries (all 209, year-independent)
  // so typing "Sri Lanka" always works even if 2025 has no Sri Lanka data
  const suggestions = location.length > 0
    ? tab === "province"
      ? listItems.filter(item =>
          item.name.toLowerCase().includes(location.toLowerCase())
        ).slice(0, 8)
      : allCountryNames
          .filter(name => name.toLowerCase().includes(location.toLowerCase()))
          .slice(0, 8)
          .map(name => ({ name, intensity: null }))
    : [];

  const query = useCallback(
    (loc = location) => {
      if (!loc) return;
      setLoading(true);
      setError(null);
      setResult(null);
      setShowDropdown(false);

      const typeParam = `&type=${tab === "province" ? "province" : "country"}`;
      // For countries: omit year - backend uses that country's own latest available year
      // For provinces: always send the selected year
      const yearParam = tab === "province" ? `&year=${year}` : "";

      fetch(`${API_BASE}/footprint?location=${encodeURIComponent(loc)}${yearParam}${typeParam}`)
        .then(r => {
          if (!r.ok) return r.json().then(d => { throw new Error(d.error || r.statusText); });
          return r.json();
        })
        .then(data => {
          setResult(data);
          setHighlighted(data.location);
        })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false));
    },
    [location, tab, year]
  );

  const selectItem = (name) => {
    setLocation(name);
    setShowDropdown(false);
    setHighlighted(name);
    query(name);
  };

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

      {/* Year selector row */}
      {tab === "province" ? (
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
      ) : (
        <div style={styles.yearRow}>
          <label style={styles.yearLabel}>Year:</label>
          <select
            value={countryYear}
            onChange={e => setCountryYear(parseInt(e.target.value))}
            style={styles.yearSelect}
          >
            {Array.from(
              { length: countryMaxYear - COUNTRY_YEAR_MIN + 1 },
              (_, i) => countryMaxYear - i          // newest first
            ).map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          <span style={styles.yearNote}>
            Ember data · 2000–{countryMaxYear} · latest year varies by country
          </span>
        </div>
      )}

      <div style={styles.searchRow}>
        <div style={styles.inputWrap}>
          <input
            type="text"
            value={location}
            onChange={e => { setLocation(e.target.value); setShowDropdown(true); }}
            onKeyDown={e => {
              if (e.key === "Enter") query();
              if (e.key === "Escape") setShowDropdown(false);
            }}
            onFocus={() => location && setShowDropdown(true)}
            placeholder={tab === "province" ? "Select or type a province..." : "Select or type a country..."}
            style={styles.input}
            autoComplete="off"
          />
          {showDropdown && suggestions.length > 0 && (
            <div style={styles.dropdown}>
              {suggestions.map(item => (
                <div
                  key={item.name}
                  style={styles.dropdownItem}
                  onMouseDown={() => selectItem(item.name)}
                >
                  <span style={styles.dropdownName}>{item.name}</span>
                  {item.intensity !== null && (
                    <span style={styles.dropdownHint}>{item.intensity} gCO₂/kWh</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
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
            <span style={styles.cardType}> {result.type === "province" ? "· Province" : "· Country"}</span>
          </h2>
          {result.type === "country" && result.latest_year && (
            <p style={styles.latestYearNote}>
              ℹ Latest Ember data for {result.location}: <strong>{result.latest_year}</strong>
              {result.latest_year === result.year ? " (most recent)" : ` - showing ${result.year} data`}
            </p>
          )}
          <div style={styles.metrics}>
            <Metric label="CO₂ per query"  value={`${result.co2_g} g`}            color={co2Color(result.co2_g)} />
            <Metric label="Water per query" value={`${result.water_ml} mL`}        color={waterColor(result.water_ml)} />
            <Metric label="Grid intensity"  value={`${result.intensity} gCO₂/kWh`} color="#6366f1" />
          </div>
          <p style={styles.cardNote}>
            Energy: {result.energy_kwh * 1000} Wh/query (Patterson et al. 2021).
            Water: global median per Ren et al. 2025 WUE method (PUE 1.4) - same for all regions.
          </p>
        </div>
      )}

      <div style={styles.tableWrap}>
        <h3 style={styles.tableTitle}>
          {tab === "province"
            ? `All 31 provinces · ${year}`
            : `All countries · ${countryYear} (Ember)`}
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
                  ref={item.name === highlighted ? highlightRef : null}
                  style={item.name === highlighted ? styles.trHighlight : styles.tr(i)}
                  onClick={() => selectItem(item.name)}
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
  yearInput:    { padding: "5px 10px", borderRadius: 6, border: "1.5px solid #cbd5e1", fontSize: 14, width: 72, textAlign: "center" },
  yearSelect:   { padding: "5px 10px", borderRadius: 6, border: "1.5px solid #cbd5e1", fontSize: 14, cursor: "pointer", background: "#fff", color: "#1e293b" },
  yearNote:     { fontSize: 12, color: "#94a3b8" },

  searchRow: { display: "flex", gap: 8, justifyContent: "center", marginBottom: 16, position: "relative" },
  inputWrap: { position: "relative", width: 280 },
  input: { padding: "10px 14px", borderRadius: 8, border: "1.5px solid #cbd5e1", fontSize: 15, width: "100%", outline: "none", boxSizing: "border-box" },
  btn:   { padding: "10px 22px", borderRadius: 8, background: "#166534", color: "#fff", border: "none", fontWeight: 600, fontSize: 15, cursor: "pointer" },

  dropdown: {
    position: "absolute",
    top: "100%",
    left: 0,
    right: 0,
    background: "#fff",
    border: "1.5px solid #cbd5e1",
    borderRadius: 8,
    boxShadow: "0 4px 16px rgba(0,0,0,.12)",
    zIndex: 100,
    maxHeight: 280,
    overflowY: "auto",
  },
  dropdownItem: {
    display: "flex",
    justifyContent: "space-between",
    padding: "9px 14px",
    cursor: "pointer",
    borderBottom: "1px solid #f1f5f9",
    fontSize: 14,
  },
  dropdownName: { fontWeight: 500, color: "#1e293b" },
  dropdownHint: { color: "#94a3b8", fontSize: 12 },

  error: { background: "#fef2f2", border: "1px solid #fecaca", color: "#dc2626", padding: "10px 16px", borderRadius: 8, marginBottom: 16, maxWidth: 560, margin: "0 auto 16px" },

  card:      { background: "#fff", border: "1.5px solid #d1fae5", borderRadius: 12, padding: "20px 24px", maxWidth: 560, margin: "0 auto 28px", boxShadow: "0 2px 8px rgba(0,0,0,.06)" },
  cardTitle: { fontSize: 22, fontWeight: 700, margin: "0 0 16px", color: "#0f172a" },
  cardYear:  { fontWeight: 400, color: "#94a3b8", fontSize: 16 },
  cardType:  { fontWeight: 400, color: "#94a3b8", fontSize: 13 },
  metrics:   { display: "flex", gap: 16, marginBottom: 14, flexWrap: "wrap" },
  metric:    { flex: "1 1 140px", background: "#f8fafc", borderRadius: 8, padding: "12px 16px", textAlign: "center" },
  metricValue: { fontSize: 24, fontWeight: 700 },
  metricLabel: { fontSize: 12, color: "#64748b", marginTop: 4 },
  cardNote:        { fontSize: 12, color: "#94a3b8", margin: 0 },
  latestYearNote:  { fontSize: 12, color: "#b45309", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 6, padding: "6px 10px", margin: "8px 0 0" },

  tableWrap:  { marginTop: 8 },
  tableTitle: { fontSize: 16, fontWeight: 600, color: "#374151", marginBottom: 10 },
  loading:    { color: "#94a3b8" },
  table:      { width: "100%", borderCollapse: "collapse", fontSize: 14 },
  th:         { textAlign: "left", padding: "8px 12px", borderBottom: "2px solid #e2e8f0", color: "#475569", fontWeight: 600 },
  tr:  i => ({ background: i % 2 === 0 ? "#fff" : "#f8fafc", cursor: "pointer" }),
  trHighlight: { background: "#dcfce7", cursor: "pointer", outline: "2px solid #16a34a", outlineOffset: "-2px" },
  td:         { padding: "7px 12px", borderBottom: "1px solid #f1f5f9" },

  footer: { textAlign: "center", color: "#94a3b8", fontSize: 12, marginTop: 40 },
};
