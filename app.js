const API_BASE = "http://localhost:8000";

let candidates = [];
let topCandidates = [];
let executionResults = [];
let currentRunId = null;

async function plan() {
  const url = document.getElementById("targetUrl").value || "http://example.com";
  const res = await fetch(`${API_BASE}/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_url: url, n_candidates: 20 })
  });
  const data = await res.json();
  candidates = data.candidates;
  document.getElementById("planOutput").textContent = JSON.stringify(data, null, 2);
}

async function rank() {
  if (!candidates.length) return alert("Run planning first!");
  const res = await fetch(`${API_BASE}/rank`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidates, top_k: 10 })
  });
  const data = await res.json();
  topCandidates = data.top_candidates;
  document.getElementById("rankOutput").textContent = JSON.stringify(data, null, 2);
}

async function execute() {
  if (!topCandidates.length) return alert("Run ranking first!");
  const res = await fetch(`${API_BASE}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tests: topCandidates, parallelism: 3 })
  });
  const data = await res.json();
  executionResults = data.results;
  currentRunId = data.run_id;
  document.getElementById("executeOutput").textContent = JSON.stringify(data, null, 2);
}

async function analyze() {
  if (!executionResults.length || !currentRunId) return alert("Run execution first!");
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: currentRunId, results: executionResults })
  });
  const data = await res.json();
  document.getElementById("analyzeOutput").textContent = JSON.stringify(data, null, 2);
}

async function fetchReport() {
  if (!currentRunId) return alert("No run ID yet! Execute tests first.");
  const res = await fetch(`${API_BASE}/report/${currentRunId}`);
  if (res.status !== 200) {
    alert("Report not found!");
    return;
  }
  const data = await res.json();
  document.getElementById("reportOutput").textContent = JSON.stringify(data, null, 2);
}
