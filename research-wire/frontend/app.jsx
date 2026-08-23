const { useState, useRef, useCallback } = React;

// Streaming endpoint. On Vercel this is a single-origin path (same host as
// the page, no scheme/host juggling needed like the old WebSocket setup).
// If you split frontend/backend across hosts, make this absolute instead,
// e.g. "https://your-backend.example.com/api/research/stream".
const STREAM_ENDPOINT = "/api/research/stream";

const STAGES = [
  { key: "search", label: "Search Agent", role: "Scans the web for sources" },
  { key: "reader", label: "Reader Agent", role: "Scrapes the best source" },
  { key: "writer", label: "Writer", role: "Drafts the report" },
  { key: "critic", label: "Critic", role: "Reviews the draft" },
];

// Helper function to convert URLs in text to clickable links
function renderTextWithLinks(text) {
  if (!text) return text;
  
  // Regex to match URLs
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const parts = text.split(urlRegex);
  
  return parts.map((part, index) => {
    if (urlRegex.test(part)) {
      return React.createElement("a", {
        key: index,
        href: part,
        target: "_blank",
        rel: "noopener noreferrer",
        style: { color: "#00d9ff", textDecoration: "underline", cursor: "pointer" }
      }, part);
    }
    return part;
  });
}

// Helper function to download report
function downloadReport(report, topic) {
  const filename = `research-report-${topic.replace(/\s+/g, "-").toLowerCase()}.txt`;
  const element = document.createElement("a");
  element.setAttribute("href", "data:text/plain;charset=utf-8," + encodeURIComponent(report));
  element.setAttribute("download", filename);
  element.style.display = "none";
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
}

function StageStatusText({ status }) {
  if (status === "active") return "transmitting…";
  if (status === "done") return "received";
  if (status === "error") return "failed";
  return "standing by";
}

function Timeline({ stageState }) {
  return (
    <div className="timeline-panel">
      <h2>Agent Pipeline</h2>
      <div className="wire">
        {STAGES.map((s) => {
          const status = stageState[s.key] || "idle";
          return (
            <div key={s.key} className={`stage ${status}`}>
              <div className="stage-node" />
              <div className="stage-label">{s.label}</div>
              <div className="stage-role">{s.role}</div>
              <div className="stage-status">
                <StageStatusText status={status} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ReportTab({ report, topic }) {
  if (!report) {
    return (
      <div className="empty-state">
        <div className="glyph">§</div>
        <p>The final report will appear here once the Writer has finished drafting.</p>
      </div>
    );
  }
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div className="section-label">Final Report</div>
        <button 
          onClick={() => downloadReport(report, topic)}
          style={{
            padding: "8px 16px",
            backgroundColor: "#00d9ff",
            color: "#0a0e27",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontWeight: "600",
            fontSize: "12px",
            transition: "all 0.2s"
          }}
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = "#00b8cc";
            e.target.style.transform = "scale(1.05)";
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = "#00d9ff";
            e.target.style.transform = "scale(1)";
          }}
        >
          ⬇ Download Report
        </button>
      </div>
      <div className="report-view">{renderTextWithLinks(report)}</div>
    </div>
  );
}

function SourcesTab({ searchResult, scrapedResult }) {
  if (!searchResult && !scrapedResult) {
    return (
      <div className="empty-state">
        <div className="glyph">⌕</div>
        <p>Raw search results and scraped source content will show up here as agents finish.</p>
      </div>
    );
  }
  return (
    <div>
      {searchResult && (
        <>
          <div className="section-label">Search Results</div>
          <div className="raw-view" style={{ marginBottom: 28 }}>{renderTextWithLinks(searchResult)}</div>
        </>
      )}
      {scrapedResult && (
        <>
          <div className="section-label">Scraped Source</div>
          <div className="raw-view">{renderTextWithLinks(scrapedResult)}</div>
        </>
      )}
    </div>
  );
}

function CritiqueTab({ feedback }) {
  if (!feedback) {
    return (
      <div className="empty-state">
        <div className="glyph">✎</div>
        <p>The critic's feedback on the draft report will land here last.</p>
      </div>
    );
  }
  return (
    <div>
      <div className="section-label">Critic Feedback</div>
      <div className="critique-view">{renderTextWithLinks(feedback)}</div>
    </div>
  );
}

function App() {
  const [topic, setTopic] = useState("");
  const [running, setRunning] = useState(false);
  const [connLive, setConnLive] = useState(null); // null | true | false
  const [stageState, setStageState] = useState({});
  const [result, setResult] = useState({ search_result: "", scraped_result: "", report: "", feedback: "" });
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("report");
  const esRef = useRef(null);

  const resetRun = () => {
    setStageState({});
    setResult({ search_result: "", scraped_result: "", report: "", feedback: "" });
    setError("");
    setActiveTab("report");
  };

  const startResearch = useCallback(() => {
    const trimmed = topic.trim();
    if (!trimmed || running) return;

    resetRun();
    setRunning(true);

    const url = `${STREAM_ENDPOINT}?topic=${encodeURIComponent(trimmed)}`;
    const es = new EventSource(url);
    esRef.current = es;
    setConnLive(true);

    es.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);

      if (msg.type === "stage") {
        setStageState((prev) => ({ ...prev, [msg.stage]: msg.status }));
        if (msg.status === "done" && msg.data) {
          if (msg.stage === "search") {
            setResult((r) => ({ ...r, search_result: msg.data }));
          } else if (msg.stage === "reader") {
            setResult((r) => ({ ...r, scraped_result: msg.data }));
          }
        }
      } else if (msg.type === "complete") {
        setResult({
          search_result: msg.data.search_result || "",
          scraped_result: msg.data.scraped_result || "",
          report: msg.data.report || "",
          feedback: msg.data.feedback || "",
        });
        setRunning(false);
        es.close();
        setConnLive(false);
      } else if (msg.type === "error") {
        setError(msg.message || "The pipeline hit an error.");
        setRunning(false);
        es.close();
        setConnLive(false);
      }
    };

    es.onerror = () => {
      // EventSource fires this on connection drop as well as on completion
      // after we've already called es.close() above — only surface it as a
      // real error if we're still expecting more events.
      if (running) {
        setError((prev) => prev || "Connection to the research stream was lost.");
        setRunning(false);
      }
      setConnLive(false);
      es.close();
    };
  }, [topic, running]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter") startResearch();
  };

  const hasAnyContent = result.report || result.feedback || result.search_result || result.scraped_result;

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead-title">
          <span className="eyebrow">Multi-Agent Research System</span>
          <h1>Research Wire</h1>
          <div className="sub">Search → Read → Draft → Critique, live over the wire.</div>
        </div>
        <div className="conn-status">
          <span className={`dot ${connLive === true ? "live" : connLive === false ? "down" : ""}`} />
          {connLive === true ? "Connected" : connLive === false ? "Disconnected" : "Idle"}
        </div>
      </header>

      <div className="query-bar">
        <input
          type="text"
          placeholder="Enter a research topic — e.g. “state of solid-state batteries in 2026”"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={running}
        />
        <button className="transmit-btn" onClick={startResearch} disabled={running || !topic.trim()}>
          {running ? "Transmitting…" : "Run Research"}
        </button>
      </div>

      <div className="console-grid">
        <Timeline stageState={stageState} />

        <div className="content-panel">
          <div className="tabs">
            <div
              className={`tab ${activeTab === "report" ? "selected" : ""}`}
              onClick={() => setActiveTab("report")}
            >
              Report
            </div>
            <div
              className={`tab ${activeTab === "sources" ? "selected" : ""}`}
              onClick={() => setActiveTab("sources")}
            >
              Sources
            </div>
            <div
              className={`tab ${activeTab === "critique" ? "selected" : ""}`}
              onClick={() => setActiveTab("critique")}
            >
              Critique
            </div>
          </div>

          <div className="tab-body">
            {error && <div className="error-banner">⚠ {error}</div>}
            {!error && activeTab === "report" && <ReportTab report={result.report} topic={topic} />}
            {!error && activeTab === "sources" && (
              <SourcesTab searchResult={result.search_result} scrapedResult={result.scraped_result} />
            )}
            {!error && activeTab === "critique" && <CritiqueTab feedback={result.feedback} />}
            {!error && !hasAnyContent && !running && activeTab === "report" && null}
          </div>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
