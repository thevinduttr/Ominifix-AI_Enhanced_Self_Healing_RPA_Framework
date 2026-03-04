import React, { useEffect, useMemo, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.trim() || "http://127.0.0.1:8001";
const HISTORY_KEY = "locator_dashboard_history";

// Fixed metrics from your latest training run
const MODEL_METRICS = {
  accuracy: 0.8488,
  rocAuc: 0.8945,
};

// Simple color palette for charts
const COLORS = ["#6366F1", "#F97316", "#22C55E", "#EAB308", "#EC4899"];

// DOM scenarios (already in your dashboard)
const PREDEFINED_SCENARIOS = [
  {
    id: "id_changed",
    label: "ID changed (Login button)",
    description: "Same text, ID changed from login_old to login_new",
    page_url: "https://dummy.local/login",
    expected_text: "Login",
    old_locator_type: "xpath",
    old_locator: "//button[@id='login_old']",
    page_html:
      '<!doctype html><html><body><form><h1>Welcome</h1><button id="login_new" class="btn primary">Login</button></form></body></html>',
  },
  {
    id: "button_to_anchor",
    label: "Button → Anchor migration",
    description: "Button replaced by anchor link with same label",
    page_url: "https://dummy.local/details",
    expected_text: "View details",
    old_locator_type: "xpath",
    old_locator: "//button[@id='view_details']",
    page_html:
      '<!doctype html><html><body><div class="card"><a id="view_details_link" class="btn primary">View details</a></div></body></html>',
  },
  {
    id: "text_changed",
    label: "Text changed (Login → Sign in)",
    description: "Label text changed but role still the same",
    page_url: "https://dummy.local/login",
    expected_text: "Sign in",
    old_locator_type: "xpath",
    old_locator: "//button[@id='login_btn']",
    page_html:
      '<!doctype html><html><body><form><button id="login_btn" class="btn primary">Sign in</button></form></body></html>',
  },
  {
    id: "moved_inside_div",
    label: "Moved inside container DIV",
    description: "Element wrapped in new container, structure changed",
    page_url: "https://dummy.local/profile",
    expected_text: "Save",
    old_locator_type: "xpath",
    old_locator: "//button[@id='save_btn']",
    page_html:
      '<!doctype html><html><body><div class="layout"><div class="panel"><button id="save_btn" class="btn primary">Save</button></div></div></body></html>',
  },
];

// Vision scenarios (based on your folders)
const VISION_SCENARIOS = [
  {
    id: "vision_login_v1",
    label: "Vision: Login button (v1)",
    description: "Template match login button inside login_v1.png",
    page_url: "https://dummy.local/login",
    expected_text: "Login",
    screenshot_path: "data/raw/screenshots/full/login_v1.png",
    template_path: "data/raw/screenshots/templates/login_button.png",
  },
  {
    id: "vision_login_style_changed",
    label: "Vision: Login button (style changed)",
    description: "Template match login button in style-changed screenshot",
    page_url: "https://dummy.local/login",
    expected_text: "Sign In",
    screenshot_path: "data/raw/screenshots/full/login_v2_style_changed.png",
    template_path: "data/raw/screenshots/templates/login_button.png",
  },
  {
    id: "vision_dropdown",
    label: "Vision: Dropdown select",
    description: "Template match dropdown in dropdown_v1.png",
    page_url: "https://dummy.local/dropdown",
    expected_text: "Please select an option",
    screenshot_path: "data/raw/screenshots/full/dropdown_v1.png",
    template_path: "data/raw/screenshots/templates/dropdown_select.png",
  },
];

function App() {
  // DOM inputs
  const [pageUrl, setPageUrl] = useState("https://dummy.local/login");
  const [expectedText, setExpectedText] = useState("Login");
  const [oldLocator, setOldLocator] = useState("//button[@id='login_old']");
  const [oldLocatorType, setOldLocatorType] = useState("xpath");
  const [rawHtml, setRawHtml] = useState(
    '<!doctype html><html><body><form><h1>Welcome</h1><button id="login_new" class="btn primary">Login</button></form></body></html>'
  );

  // Vision inputs
  const [screenshotPath, setScreenshotPath] = useState("");
  const [templatePath, setTemplatePath] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [currentReport, setCurrentReport] = useState(null);
  const [history, setHistory] = useState([]);

  // ========== History persistence (localStorage) ==========

  // Load from localStorage on first mount
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(HISTORY_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          setHistory(parsed);
        }
      }
    } catch {
      // ignore
    }
  }, []);

  // Save history whenever it changes
  useEffect(() => {
    try {
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    } catch {
      // ignore
    }
  }, [history]);

  // ========== Core: call backend ==========

  async function runTest() {
    setLoading(true);
    setError("");
    setCurrentReport(null);

    const payload = {
      page_url: pageUrl,
      failure_type: "ELEMENT_NOT_FOUND",
      failed_action: "click",
      element_role: "primary_action",
      expected_text: expectedText,
      old_locator: oldLocator,
      old_locator_type: oldLocatorType,
      error_message: "Manual test via dashboard",
      page_html: rawHtml.trim() || null,

      // Vision fields (backend must support these)
      screenshot_path: screenshotPath.trim() || null,
      template_path: templatePath.trim() || null,

      metadata: {
        bot_id: "DASHBOARD-BOT",
        workflow_step: "demo_step",
      },
    };

    try {
      const res = await fetch(`${API_BASE}/element-locator/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }

      const json = await res.json();
      setCurrentReport(json);

      setHistory((prev) => {
        const next = [
          {
            id: `${Date.now()}`,
            input: payload,
            output: json,
          },
          ...prev,
        ];
        return next.slice(0, 25); // keep latest 25
      });
    } catch (err) {
      console.error(err);
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const candidate = currentReport?.element_candidate;
  const score = candidate?.score ?? null;
  const extra = candidate?.extra ?? {};

  // ========== Predefined scenarios ==========

  // DOM scenario apply
  function applyScenario(scenario) {
    setPageUrl(scenario.page_url);
    setExpectedText(scenario.expected_text);
    setOldLocatorType(scenario.old_locator_type);
    setOldLocator(scenario.old_locator);
    setRawHtml(scenario.page_html);

    // clear vision fields
    setScreenshotPath("");
    setTemplatePath("");
  }

    // Vision scenario apply
  function applyVisionScenario(scenario) {
    setPageUrl(scenario.page_url);
    setExpectedText(scenario.expected_text);

    // Keep old locator fields as-is (optional), but you can also set dummy values
    // setOldLocatorType("xpath");
    // setOldLocator("//button[@id='old_locator']");

    // Vision fields
    setScreenshotPath(scenario.screenshot_path);
    setTemplatePath(scenario.template_path);

    // For vision-only testing, you can leave rawHtml empty OR keep current rawHtml
    // If your backend uses DOM after vision to build XPath/CSS, keep HTML present.
    // We keep current rawHtml to avoid breaking DOM stage.
  }

  // ========== Chart data building ==========
  const { strategyData, scoreData } = useMemo(() => {
    const strategyCounts = history.reduce((acc, h) => {
      const st = h.output.element_candidate?.strategy || "none";
      acc[st] = (acc[st] || 0) + 1;
      return acc;
    }, {});
    const sData = Object.entries(strategyCounts).map(([name, value]) => ({
      name,
      value,
    }));

    const cData = history
      .map((h, idx) => {
        const s = h?.output?.element_candidate?.score;
        if (s == null) return null;
        return {
          index: history.length - idx,
          score: Number(s.toFixed(3)),
        };
      })
      .filter(Boolean);
    
    return { strategyData: sData, scoreData: cData };

  }, [history]);

  // ========== Render ==========

  return (
    <div className="page">
      <header className="header">
        <h1>AI Element Locator – Dashboard</h1>
        <p className="subtitle">
          AI-Powered Element Locator Engine
        </p>
      </header>

      {/* MODEL METRICS */}
      <section className="card card-metrics">
        <h2>Reliability Model Metrics</h2>
        <div className="metrics-row">
          <div className="metric-box">
            <div className="metric-label">Accuracy</div>
            <div className="metric-value">
              {(MODEL_METRICS.accuracy * 100).toFixed(2)}%
            </div>
          </div>
          <div className="metric-box">
            <div className="metric-label">ROC-AUC</div>
            <div className="metric-value">
              {(MODEL_METRICS.rocAuc * 100).toFixed(2)}%
            </div>
          </div>
          <div className="metric-note">
            RANDOMFOREST CLASSIFIER
          </div>
        </div>
      </section>

      <main className="main">
        {/* Left: Test form + scenarios */}
        <section className="card card-form">
          <h2>Test Case Input</h2>

          <div className="scenario-row">
            <span className="label">Predefined DOM Scenarios:</span>
            <div className="scenario-buttons">
              {PREDEFINED_SCENARIOS.map((s) => (
                <button
                  key={s.id}
                  className="btn-scenario"
                  onClick={() => applyScenario(s)}
                  title={s.description}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <div className="scenario-row">
            <span className="label">Predefined Vision Scenarios:</span>
            <div className="scenario-buttons">
              {VISION_SCENARIOS.map((s) => (
                <button
                  key={s.id}
                  className="btn-scenario btn-scenario-vision"
                  onClick={() => applyVisionScenario(s)}
                  title={s.description}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Page URL</label>
            <input
              value={pageUrl}
              onChange={(e) => setPageUrl(e.target.value)}
              placeholder="https://example.com"
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Expected Text</label>
              <input
                value={expectedText}
                onChange={(e) => setExpectedText(e.target.value)}
                placeholder="Login"
              />
            </div>
            <div className="form-group">
              <label>Old Locator Type</label>
              <select
                value={oldLocatorType}
                onChange={(e) => setOldLocatorType(e.target.value)}
              >
                <option value="xpath">XPath</option>
                <option value="css">CSS</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Old Locator</label>
            <input
              value={oldLocator}
              onChange={(e) => setOldLocator(e.target.value)}
              placeholder='//button[@id="login_old"]'
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Screenshot Path (Vision)</label>
              <input
                value={screenshotPath}
                onChange={(e) => setScreenshotPath(e.target.value)}
                placeholder="data/raw/screenshots/full/login_v1.png"
              />
              <small>
                Use local paths inside your project. Backend reads this file.
              </small>
            </div>
            <div className="form-group">
              <label>Template Path (Vision)</label>
              <input
                value={templatePath}
                onChange={(e) => setTemplatePath(e.target.value)}
                placeholder="data/raw/screenshots/templates/login_button.png"
              />
              <small>Cropped element image used for template matching.</small>
            </div>
          </div>

          <div className="form-group">
            <label>Page HTML Snapshot (optional)</label>
            <textarea
              value={rawHtml}
              onChange={(e) => setRawHtml(e.target.value)}
              rows={6}
            />
            <small>
              If empty, the backend will try to fetch HTML from the URL
              directly.
            </small>
          </div>

          <button className="btn-primary" onClick={runTest} disabled={loading}>
            {loading ? "Running..." : "Run Locator Engine"}
          </button>

          {error && <div className="error">Error: {error}</div>}
        </section>

        {/* Right: Current result + charts */}
        <section className="card card-result">
          <h2>Current Result</h2>

          {!currentReport && <p>No test executed yet.</p>}

          {currentReport && (
            <>
              <div className="score-row">
                <div>
                  <span className="label">Strategy:</span>{" "}
                  <strong>{candidate?.strategy ?? "None"}</strong>
                </div>
                <div>
                  <span className="label">Score:</span>{" "}
                  <strong>
                    {score !== null ? score.toFixed(3) : "N/A"}
                  </strong>
                </div>
              </div>

              <div className="grid-two">
                <div>
                  <h3>Locator Details</h3>
                  <pre className="code">
{`XPath: ${candidate?.xpath ?? "N/A"}
CSS:   ${candidate?.css ?? "N/A"}`}
                  </pre>

                  <h3>Vision Signals (if used)</h3>
                  <pre className="code small">
                    {`vision_match_score: ${extra?.vision_match_score != null ? Number(extra.vision_match_score).toFixed(4) : "N/A"}
vision_threshold  : ${extra?.vision_threshold != null ? Number(extra.vision_threshold).toFixed(2) : "N/A"}
vision_template   : ${extra?.vision_template ?? "N/A"}
vision_screenshot : ${extra?.vision_screenshot ?? "N/A"}`}
                  </pre>
                </div>
                <div>
                  <h3>Element HTML</h3>
                  <pre className="code small">
                    {currentReport.dom_context?.new_element_html ?? "N/A"}
                  </pre>
                </div>
              </div>

              <details style={{ marginTop: 10 }}>
                <summary
                  style={{ cursor: "pointer", fontWeight: 700, opacity: 0.9 }}
                >
                  Raw JSON Report
                </summary>
                <pre className="code small">
                  {JSON.stringify(currentReport, null, 2)}
                </pre>
              </details>
            </>
          )}

          {/* Charts section */}
          <div className="charts-container">
            <div className="chart-card">
              <h3>Strategy Usage</h3>
              {strategyData.length === 0 ? (
                <p className="chart-placeholder">
                  Run some tests to see chart.
                </p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={strategyData}
                      dataKey="value"
                      nameKey="name"
                      outerRadius={80}
                      label
                    >
                      {strategyData.map((entry, index) => (
                        <Cell
                          key={`cell-${entry.name}`}
                          fill={COLORS[index % COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Legend />
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="chart-card">
              <h3>Confidence Scores (Recent Runs)</h3>
              {scoreData.length === 0 ? (
                <p className="chart-placeholder">
                  Run some tests to see chart.
                </p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={scoreData}>
                    <XAxis dataKey="index" />
                    <YAxis domain={[0, 1]} />
                    <Tooltip />
                    <Bar dataKey="score" fill="#22C55E" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </section>
      </main>

      {/* History */}
      <section className="card card-history">
        <h2>Recent Test Runs</h2>
        {history.length === 0 && <p>No history yet.</p>}
        {history.length > 0 && (
          <table className="history-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Expected Text</th>
                <th>Old Locator</th>
                <th>Strategy</th>
                <th>Score</th>
                <th>Vision</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h, idx) => {
                const c = h.output.element_candidate;
                const ex = c?.extra ?? {};
                const visionShown =
                  ex?.vision_match_score != null
                    ? `${Number(ex.vision_match_score).toFixed(3)} / thr ${ex?.vision_threshold != null ? Number(ex.vision_threshold).toFixed(2) : "?"}`
                    : "-";

                return (
                  <tr key={h.id}>
                    <td>{history.length - idx}</td>
                    <td>{h.input.expected_text}</td>
                    <td className="mono">{h?.input?.old_locator ?? "-"}</td>
                    <td>{c?.strategy ?? "-"}</td>
                    <td>
                      {c?.score != null ? Number(c.score).toFixed(3) : "-"}
                    </td>
                    <td className="mono">{visionShown}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default App;
