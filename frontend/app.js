const fileInput = document.getElementById("resumeFiles");
const dropZone = document.getElementById("dropZone");
const fileList = document.getElementById("fileList");
const evaluateBtn = document.getElementById("evaluateBtn");
const statusEl = document.getElementById("status");
const resultsCard = document.getElementById("resultsCard");
const resultsEl = document.getElementById("results");
const topNInput = document.getElementById("topN");
const jobDescriptionEl = document.getElementById("jobDescription");

// Load the default top-N from the backend.
fetch("/api/default-top-n")
  .then((r) => r.json())
  .then((data) => {
    if (data.top_n) topNInput.value = data.top_n;
  })
  .catch(() => {});

function renderFileList() {
  fileList.innerHTML = "";
  for (const file of fileInput.files) {
    const li = document.createElement("li");
    li.textContent = `• ${file.name}`;
    fileList.appendChild(li);
  }
}

fileInput.addEventListener("change", renderFileList);

["dragenter", "dragover"].forEach((evt) =>
  dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
  })
);
dropZone.addEventListener("drop", (e) => {
  fileInput.files = e.dataTransfer.files;
  renderFileList();
});

function setStatus(message, isError = false) {
  statusEl.hidden = !message;
  statusEl.textContent = message || "";
  statusEl.classList.toggle("error", isError);
}

function chip(text, cls) {
  const span = document.createElement("span");
  span.className = `chip ${cls}`;
  span.textContent = text;
  return span;
}

function renderCandidate(candidate) {
  const details = candidate.details || {};
  const div = document.createElement("div");
  div.className = "candidate";

  const head = document.createElement("div");
  head.className = "head";
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = candidate.name || "Unknown candidate";
  const score = document.createElement("span");
  score.className = "score";
  score.textContent = `${Number(candidate.score).toFixed(1)} / 100`;
  head.append(name, score);

  const bar = document.createElement("div");
  bar.className = "score-bar";
  const fill = document.createElement("span");
  fill.style.width = `${Math.max(0, Math.min(100, candidate.score))}%`;
  bar.appendChild(fill);

  div.append(head, bar);

  if (details.verdict) {
    const verdict = document.createElement("p");
    verdict.className = "verdict";
    verdict.textContent = details.verdict;
    div.appendChild(verdict);
  }

  const chips = document.createElement("div");
  chips.className = "chips";
  (details.matching_skills || []).forEach((s) => chips.appendChild(chip(`✓ ${s}`, "match")));
  (details.missing_important_skills || []).forEach((s) =>
    chips.appendChild(chip(`✗ ${s}`, "missing"))
  );
  if (chips.children.length) div.appendChild(chips);

  return div;
}

async function evaluate() {
  const files = fileInput.files;
  if (!files.length) {
    setStatus("Please select at least one resume.", true);
    return;
  }

  const topN = parseInt(topNInput.value, 10);
  if (!Number.isInteger(topN) || topN < 1) {
    setStatus("Please enter a positive number for N.", true);
    return;
  }

  const form = new FormData();
  for (const file of files) form.append("files", file);
  form.append("top_n", topN);
  if (jobDescriptionEl.value.trim()) form.append("job_description", jobDescriptionEl.value.trim());

  evaluateBtn.disabled = true;
  resultsCard.hidden = true;
  setStatus(`Evaluating ${files.length} resume(s)... this may take a minute.`);

  try {
    const response = await fetch("/api/evaluate", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Evaluation failed");
    }

    resultsEl.innerHTML = "";
    data.top_candidates.forEach((c) => resultsEl.appendChild(renderCandidate(c)));

    if (data.errors && data.errors.length) {
      const err = document.createElement("p");
      err.className = "errors";
      err.textContent = "Failed: " + data.errors.map((e) => e.name).join(", ");
      resultsEl.appendChild(err);
    }

    resultsCard.hidden = false;
    setStatus(`Evaluated ${data.total_evaluated} resume(s).`);
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    evaluateBtn.disabled = false;
  }
}

evaluateBtn.addEventListener("click", evaluate);
