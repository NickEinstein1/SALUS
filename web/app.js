(() => {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];

  const healthStatus = $("#healthStatus");
  const askForm = $("#askForm");
  const questionInput = $("#question");
  const askBtn = $("#askBtn");
  const workspace = $("#workspace");
  const stepLog = $("#stepLog");
  const agentRail = $("#agentRail");
  const answerBox = $("#answerBox");
  const sourcesBox = $("#sourcesBox");
  const checklistBox = $("#checklistBox");
  const metaRow = $("#metaRow");
  const graphFocus = $("#graphFocus");
  const graphName = $("#graphName");
  const hero = $("#hero");
  const panelAct = $("#panelAct");
  const panelRemember = $("#panelRemember");
  const panelExplain = $("#panelExplain");
  const actionToast = $("#actionToast");
  const escalateStatus = $("#escalateStatus");
  const apiKeyInput = $("#apiKeyInput");
  const openaiKeyInput = $("#openaiKeyInput");
  const chatThread = $("#chatThread");
  const chatPanel = $("#chatPanel");
  const chatFollowForm = $("#chatFollowForm");
  const chatFollow = $("#chatFollow");
  const chatFollowBtn = $("#chatFollowBtn");
  const pathFrom = $("#pathFrom");
  const pathTo = $("#pathTo");
  const pathFindBtn = $("#pathFindBtn");
  const pathClearBtn = $("#pathClearBtn");
  const pathBreadcrumb = $("#pathBreadcrumb");

  let cy = null;
  let sessionId = null;
  let lastResult = null;
  let lastGraph = null;
  let lastPath = [];
  let collectedSteps = [];
  let authRequired = true;
  let chatReady = false;

  const API_KEY_STORAGE = "salus_api_key";
  const OPENAI_KEY_STORAGE = "salus_openai_key";
  const DEFAULT_DEV_KEY = "salus-dev-change-me";

  function getApiKey() {
    return (apiKeyInput?.value || localStorage.getItem(API_KEY_STORAGE) || DEFAULT_DEV_KEY).trim();
  }

  function getOpenAIKey() {
    return (openaiKeyInput?.value || localStorage.getItem(OPENAI_KEY_STORAGE) || "").trim();
  }

  function persistApiKey() {
    if (!apiKeyInput) return;
    const v = apiKeyInput.value.trim();
    if (v) localStorage.setItem(API_KEY_STORAGE, v);
  }

  function persistOpenAIKey() {
    if (!openaiKeyInput) return;
    const v = openaiKeyInput.value.trim();
    if (v) localStorage.setItem(OPENAI_KEY_STORAGE, v);
    else localStorage.removeItem(OPENAI_KEY_STORAGE);
  }

  function authHeaders(extra = {}) {
    const headers = { ...extra };
    if (authRequired) headers["X-API-Key"] = getApiKey();
    const oai = getOpenAIKey();
    if (oai) headers["X-OpenAI-Key"] = oai;
    return headers;
  }

  async function apiFetch(url, options = {}) {
    const opts = { ...options };
    opts.headers = authHeaders(opts.headers || {});
    if (opts.body && !opts.headers["Content-Type"]) {
      opts.headers["Content-Type"] = "application/json";
    }
    const res = await fetch(url, opts);
    if (res.status === 401) {
      toast("API key required or invalid — set key in the top bar", true);
    }
    return res;
  }

  const DOMAIN_COLORS = {
    finance: "#0c6b52",
    healthcare: "#1a5cff",
    security: "#8a3d12",
    facilities: "#2f6f7e",
    ops: "#44554c",
  };

  const TRACK_MAP = {
    router: ["02"],
    investigator: ["01", "03"],
    actor: ["01"],
    scribe: ["02"],
  };

  function setHealth(ok, text) {
    healthStatus.textContent = text;
    healthStatus.classList.toggle("ok", ok);
    healthStatus.classList.toggle("bad", !ok);
  }

  function setTrackState(id, state) {
    const el = document.getElementById(`track${id}`);
    if (!el) return;
    el.classList.toggle("is-active", state === "running" || state === "active");
    el.classList.toggle("is-running", state === "running");
    el.classList.toggle("is-done", state === "done");
    const stateEl = el.querySelector("[data-state]");
    if (stateEl) stateEl.textContent = state;
    const panel = document.querySelector(`.track-panel[data-panel="${id}"]`);
    if (panel) panel.classList.toggle("is-lit", state === "running" || state === "done" || state === "active");
  }

  function resetTracks() {
    ["01", "02", "03"].forEach((id) => setTrackState(id, "idle"));
    panelAct.textContent = "Waiting for investigation…";
    panelRemember.textContent = "Session memory will appear here.";
    panelExplain.textContent = "Evidence path and sources will appear here.";
  }

  function activateTracksFromAgent(agent) {
    (TRACK_MAP[agent] || []).forEach((id) => setTrackState(id, "running"));
  }

  function toast(msg, isError = false) {
    actionToast.hidden = false;
    actionToast.textContent = msg;
    actionToast.classList.toggle("is-error", isError);
    clearTimeout(toast._t);
    toast._t = setTimeout(() => {
      actionToast.hidden = true;
    }, 4200);
  }

  /* —— SALUS left chatbot (speaks after other sections) —— */
  function clearChat(keepSystem = true) {
    chatThread.innerHTML = "";
    if (keepSystem) {
      appendChat(
        "system",
        "Sections on the right and center run first. When the path is complete, I will appear here and explain what transpired."
      );
    }
    chatReady = false;
    chatPanel.classList.remove("is-ready");
    if (chatFollowBtn) chatFollowBtn.disabled = true;
  }

  function appendChat(role, text) {
    const div = document.createElement("div");
    div.className = `chat-bubble ${role}`;
    const label =
      role === "salus" ? "SALUS" : role === "user" ? "You" : "Waiting";
    div.innerHTML = `<span class="chat-label">${label}</span>`;
    const body = document.createElement("div");
    body.textContent = text;
    div.appendChild(body);
    chatThread.appendChild(div);
    chatThread.scrollTop = chatThread.scrollHeight;
  }

  function buildSalusNarration(result) {
    const path = result.path || {};
    const radius = path.blast_radius || {};
    const mem = path.memory || {};
    const actions = result.actions || [];
    const hops = lastPath.length ? lastPath.join(" → ") : null;
    const depends = (radius.depends_on || []).slice(0, 5);
    const owners = result.owners || [];
    const episodes = (mem.episodes || []).map((e) => e.summary).slice(0, 2);
    const steps = collectedSteps.slice(0, 6);

    const lines = [
      "I've reviewed what transpired across the path finder and the three tracks.",
      "",
      hops
        ? `Graph path: ${hops}.`
        : result.system
          ? `Focus system: ${result.system}.`
          : "No single dependency path was highlighted.",
      "",
      "01 · Act",
      actions.length
        ? `Actions taken: ${actions.join("; ")}.`
        : "No automated actions were queued.",
      owners.length ? `Owners in scope: ${owners.join(", ")}.` : "",
      depends.length ? `Downstream depends: ${depends.join(", ")}.` : "",
      "",
      "02 · Remember",
      result.session_id ? `Session ${result.session_id}.` : "",
      episodes.length
        ? `Memory recalled: ${episodes.join(" · ")}.`
        : "No prior episodes for this session.",
      "",
      "03 · Explain",
      result.evidence_summary || "Evidence summarized from graph hops and tool traces.",
      result.sources?.length
        ? `Sources: ${result.sources.slice(0, 4).join(" · ")}.`
        : "",
      "",
      `Confidence ${Math.round((result.confidence || 0) * 100)}%.`,
      "",
      (result.answer || "").replace(/\*\*/g, "").slice(0, 900),
    ];

    if (steps.length) {
      lines.splice(2, 0, "", "Agent sequence:", ...steps.map((s) => `· ${s}`), "");
    }

    return lines.filter((l) => l !== undefined && l !== null).join("\n").trim();
  }

  function revealSalusChat(result) {
    chatPanel.classList.add("is-ready");
    chatReady = true;
    if (chatFollowBtn) chatFollowBtn.disabled = false;
    appendChat("salus", buildSalusNarration(result));
  }

  function fillPathSelects(data) {
    if (!pathFrom || !pathTo) return;
    const systems = (data.nodes || [])
      .filter((n) => n.kind === "system")
      .map((n) => n.id)
      .sort();
    const prevFrom = pathFrom.value;
    const prevTo = pathTo.value;
    pathFrom.innerHTML = systems.map((s) => `<option value="${s}">${s}</option>`).join("");
    pathTo.innerHTML = systems.map((s) => `<option value="${s}">${s}</option>`).join("");
    if (systems.includes(prevFrom)) pathFrom.value = prevFrom;
    else if (systems.includes("ehr-core")) pathFrom.value = "ehr-core";
    if (systems.includes(prevTo)) pathTo.value = prevTo;
    else if (systems.includes("building-mgmt")) pathTo.value = "building-mgmt";
    else if (systems.length > 1) pathTo.selectedIndex = Math.min(1, systems.length - 1);
  }

  function renderBreadcrumb(nodes) {
    if (!pathBreadcrumb) return;
    pathBreadcrumb.innerHTML = nodes.map((n) => `<li>${n}</li>`).join("");
  }

  function clearPathHighlight() {
    lastPath = [];
    renderBreadcrumb([]);
    if (!cy) return;
    cy.elements().removeClass("on-path path-endpoint");
  }

  function highlightPath(nodeNames) {
    lastPath = nodeNames || [];
    renderBreadcrumb(lastPath);
    if (!cy || !lastPath.length) return;

    cy.elements().removeClass("on-path path-endpoint");
    lastPath.forEach((name, i) => {
      const node = cy.getElementById(name);
      if (node.nonempty()) {
        node.addClass("on-path");
        if (i === 0 || i === lastPath.length - 1) node.addClass("path-endpoint");
      }
      if (i < lastPath.length - 1) {
        const next = lastPath[i + 1];
        const edge = cy.edges().filter(
          (e) =>
            (e.data("source") === name && e.data("target") === next) ||
            (e.data("source") === next && e.data("target") === name)
        );
        edge.addClass("on-path");
      }
    });

    const pathNodes = cy.nodes(".on-path");
    if (pathNodes.length) {
      cy.animate({
        fit: { eles: pathNodes.union(cy.edges(".on-path")), padding: 48 },
        duration: 500,
      });
    }
  }

  async function tracePath(source, target) {
    if (!source || !target || source === target) {
      toast("Pick two different systems", true);
      return;
    }
    graphFocus.textContent = `Tracing · ${source} → ${target}`;
    setTrackState("03", "running");
    try {
      const res = await apiFetch(
        `/api/path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `path ${res.status}`);
      if (!data.found || !data.path?.length) {
        clearPathHighlight();
        toast(`No DEPENDS_ON path from ${source} to ${target}`, true);
        panelExplain.textContent = `No shortest path between ${source} and ${target}.`;
        setTrackState("03", "done");
        appendChat(
          "salus",
          `I checked the graph after the other sections. No DEPENDS_ON path exists from ${source} to ${target} within hop limits.`
        );
        chatPanel.classList.add("is-ready");
        chatReady = true;
        if (chatFollowBtn) chatFollowBtn.disabled = false;
        return;
      }
      highlightPath(data.path);
      panelExplain.textContent =
        `Shortest path (${data.algorithm}, ${data.hops} hops): ${data.path.join(" → ")}.`;
      setTrackState("03", "done");
      graphFocus.textContent = `Path · ${data.hops} hops`;
      toast(`Path found · ${data.hops} hops`);

      // SALUS chats only after path + explain section filled
      appendChat(
        "salus",
        [
          "Path finder finished. Here's what transpired:",
          "",
          `Route: ${data.path.join(" → ")}`,
          `Algorithm: ${data.algorithm} · ${data.hops} hop(s)`,
          "",
          "Track 03 · Explain is lit with this evidence path. Ask a question above if you want Act + Remember to run next, or send a follow-up here.",
        ].join("\n")
      );
      chatPanel.classList.add("is-ready");
      chatReady = true;
      if (chatFollowBtn) chatFollowBtn.disabled = false;
    } catch (e) {
      toast(String(e.message || e), true);
    }
  }

  async function boot() {
    try {
      const stored = localStorage.getItem(API_KEY_STORAGE) || DEFAULT_DEV_KEY;
      if (apiKeyInput) {
        apiKeyInput.value = stored;
        apiKeyInput.addEventListener("change", persistApiKey);
        apiKeyInput.addEventListener("blur", persistApiKey);
      }
      const oaiStored = localStorage.getItem(OPENAI_KEY_STORAGE) || "";
      if (openaiKeyInput) {
        openaiKeyInput.value = oaiStored;
        openaiKeyInput.addEventListener("change", persistOpenAIKey);
        openaiKeyInput.addEventListener("blur", persistOpenAIKey);
      }

      const cfg = await fetch("/api/auth/config").then((r) => r.json());
      authRequired = !!cfg.auth_required;

      let h = await fetch("/api/health").then((r) => r.json());
      if (h.ok) {
        setHealth(true, `${h.nodes} nodes · live${authRequired ? " · auth" : ""}`);
        graphName.textContent = h.graph || "salus:acme";
      } else {
        setHealth(false, "graph offline");
      }
      await loadGraph();
    } catch (e) {
      setHealth(false, "api offline");
      console.error(e);
    }
  }

  function domainColor(domain) {
    return DOMAIN_COLORS[domain] || "#0c6b52";
  }

  async function loadGraph(focus) {
    const url = focus ? `/api/graph?focus=${encodeURIComponent(focus)}` : "/api/graph";
    const res = await apiFetch(url);
    if (!res.ok) throw new Error(`graph ${res.status}`);
    const data = await res.json();
    lastGraph = data;
    renderGraph(data, focus);
    fillPathSelects(data);
    if (focus) graphFocus.textContent = `Focus · ${focus}`;
    if (lastPath.length) highlightPath(lastPath);
  }

  function renderGraph(data, focus) {
    const elements = [
      ...data.nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.label,
          kind: n.kind,
          domain: n.domain || "",
          focused: n.focused || (focus && n.id === focus),
        },
      })),
      ...data.edges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          kind: e.kind,
        },
      })),
    ];

    if (!cy) {
      cy = cytoscape({
        container: $("#cy"),
        elements,
        style: [
          {
            selector: "node",
            style: {
              label: "data(label)",
              "font-family": "IBM Plex Sans, sans-serif",
              "font-size": 10,
              color: "#13241c",
              "text-valign": "bottom",
              "text-margin-y": 6,
              "background-color": "#0c6b52",
              width: 28,
              height: 28,
              "border-width": 0,
              opacity: 0.55,
            },
          },
          {
            selector: 'node[kind = "person"]',
            style: {
              shape: "round-rectangle",
              "background-color": "#1a5cff",
              width: 24,
              height: 24,
            },
          },
          {
            selector: "node.focused",
            style: {
              width: 40,
              height: 40,
              "border-width": 3,
              "border-color": "#13241c",
              opacity: 1,
            },
          },
          {
            selector: "node.on-path",
            style: {
              width: 36,
              height: 36,
              "border-width": 3,
              "border-color": "#b33a1a",
              opacity: 1,
              "z-index": 10,
            },
          },
          {
            selector: "node.path-endpoint",
            style: {
              width: 44,
              height: 44,
              "border-width": 4,
              "border-color": "#b33a1a",
            },
          },
          {
            selector: "edge",
            style: {
              width: 1.5,
              "line-color": "rgba(19,36,28,0.28)",
              "target-arrow-color": "rgba(19,36,28,0.28)",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              "arrow-scale": 0.7,
              opacity: 0.45,
            },
          },
          {
            selector: 'edge[kind = "OWNS"]',
            style: {
              "line-style": "dashed",
              "line-color": "rgba(26,92,255,0.45)",
              "target-arrow-color": "rgba(26,92,255,0.45)",
            },
          },
          {
            selector: "edge.on-path",
            style: {
              width: 4,
              "line-color": "#b33a1a",
              "target-arrow-color": "#b33a1a",
              opacity: 1,
              "z-index": 9,
            },
          },
        ],
        layout: { name: "cose", animate: true, animationDuration: 650, padding: 28 },
      });
    } else {
      cy.elements().remove();
      cy.add(elements);
      cy.layout({ name: "cose", animate: true, animationDuration: 650, padding: 28 }).run();
    }

    cy.nodes().forEach((node) => {
      if (node.data("kind") === "system") {
        node.style("background-color", domainColor(node.data("domain")));
      }
      if (node.data("focused")) node.addClass("focused");
      else node.removeClass("focused");
    });
  }

  function activateWorkspace() {
    workspace.classList.remove("is-idle");
    workspace.classList.add("is-active");
    if (hero) {
      hero.style.minHeight = "auto";
      hero.style.paddingBottom = "1.25rem";
    }
  }

  function resetRunUI() {
    stepLog.innerHTML = "";
    answerBox.innerHTML = `<p class="muted">Agents running across sections… SALUS will chat when complete.</p>`;
    sourcesBox.innerHTML = "";
    checklistBox.innerHTML = "";
    metaRow.innerHTML = "";
    escalateStatus.textContent = "";
    collectedSteps = [];
    clearChat(true);
    clearPathHighlight();
    resetTracks();
    agentRail.querySelectorAll("li").forEach((li) => {
      li.classList.remove("is-active", "is-done");
    });
  }

  function setActiveAgent(agent) {
    activateTracksFromAgent(agent);
    agentRail.querySelectorAll("li").forEach((li) => {
      const name = li.getAttribute("data-agent");
      if (name === agent) {
        li.classList.add("is-active");
        li.classList.remove("is-done");
      } else if (li.classList.contains("is-active")) {
        li.classList.remove("is-active");
        li.classList.add("is-done");
      }
    });
  }

  function pushStep(agent, action) {
    const li = document.createElement("li");
    li.innerHTML = `<div class="agent">${agent}</div><div>${action}</div>`;
    stepLog.prepend(li);
    collectedSteps.push(`${agent}: ${action}`);
    setActiveAgent(agent);
  }

  function fillTrackPanels(result) {
    const path = result.path || {};
    const radius = path.blast_radius || {};
    const mem = path.memory || {};
    const actions = result.actions || [];

    panelAct.textContent =
      `Actions: ${actions.join("; ") || "none"}. ` +
      `Depends on ${(radius.depends_on || []).join(", ") || "—"}; ` +
      `owners ${(result.owners || []).join(", ") || "—"}.`;

    const episodes = (mem.episodes || []).map((e) => e.summary).slice(0, 2);
    const facts = (mem.facts || []).map((f) => f.statement).slice(0, 1);
    panelRemember.textContent =
      `Session ${result.session_id || "—"}. ` +
      (episodes.length ? `Episodes: ${episodes.join(" · ")}. ` : "No prior episodes. ") +
      (facts.length ? `Fact: ${facts[0]}` : "");

    const pathNodes = extractPathFromResult(result);
    if (pathNodes.length) {
      panelExplain.textContent =
        `Path: ${pathNodes.join(" → ")}. ` +
        `${result.evidence_summary || ""}. ` +
        `Sources: ${(result.sources || []).slice(0, 3).join(" · ") || "graph only"}.`;
    } else {
      panelExplain.textContent =
        `${result.evidence_summary || "No evidence summary"}. ` +
        `Sources: ${(result.sources || []).slice(0, 3).join(" · ") || "graph only"}.`;
    }

    setTrackState("01", "done");
    setTrackState("02", "done");
    setTrackState("03", "done");
  }

  function extractPathFromResult(result) {
    const path = result.path || {};
    const sp = path.shortest_path || path.tool_trace?.find?.(() => false);
    if (Array.isArray(path.path_nodes) && path.path_nodes.length) return path.path_nodes;
    if (path.shortest_path?.path) return path.shortest_path.path;
    const radius = path.blast_radius || {};
    const deps = radius.depends_on || [];
    if (result.system && deps.length) return [result.system, deps[0]];
    if (result.system) return [result.system];
    return [];
  }

  function renderResult(result) {
    lastResult = result;
    const conf = Math.round((result.confidence || 0) * 100);
    metaRow.innerHTML = [
      result.system ? `<span class="chip strong">${result.system}</span>` : "",
      result.domain ? `<span class="chip">${result.domain}</span>` : "",
      `<span class="chip">${conf}% confidence</span>`,
      result.investigation_id ? `<span class="chip">${result.investigation_id}</span>` : "",
    ].join("");

    answerBox.textContent = (result.answer || "").replace(/\*\*/g, "");

    sourcesBox.innerHTML = (result.sources || [])
      .map((s) =>
        String(s).startsWith("http")
          ? `<a href="${s}" target="_blank" rel="noopener">${s}</a>`
          : `<span>${s}</span>`
      )
      .join("");

    checklistBox.innerHTML = Object.entries(result.checklist || {})
      .map(
        ([k, v]) =>
          `<div class="check ${v ? "pass" : "fail"}">${v ? "✓" : "✗"} ${k.replace(/_/g, " ")}</div>`
      )
      .join("");

    fillTrackPanels(result);

    const pathNodes = extractPathFromResult(result);
    if (result.system) {
      loadGraph(result.system).then(() => {
        if (pathNodes.length > 1) highlightPath(pathNodes);
        else if (result.system) highlightPath([result.system]);
      });
    } else if (pathNodes.length) {
      highlightPath(pathNodes);
    }

    if (result.session_id) sessionId = result.session_id;

    agentRail.querySelectorAll("li").forEach((li) => {
      li.classList.remove("is-active");
      li.classList.add("is-done");
    });

    // Chatbot appears last — after graph, tracks, and context panels are filled
    revealSalusChat(result);
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function doExport(format) {
    if (!lastResult && !["graph_json", "graph_csv", "graphml"].includes(format)) {
      toast("Run an investigation first", true);
      return;
    }
    try {
      const res = await apiFetch("/api/export", {
        method: "POST",
        body: JSON.stringify({
          format,
          system: lastResult?.system || null,
          result: lastResult || {},
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const cd = res.headers.get("Content-Disposition") || "";
      const match = /filename=([^;]+)/.exec(cd);
      const filename = (match ? match[1] : `salus-export.${format}`).replace(/"/g, "");
      const blob = await res.blob();
      downloadBlob(blob, filename);
      toast(`Exported ${filename}`);
    } catch (e) {
      toast(String(e.message || e), true);
    }
  }

  function ticketFromResult(result) {
    const sources = result?.sources || [];
    const hit = sources.find((s) => String(s).startsWith("ticket:"));
    if (hit) return String(hit).replace(/^ticket:/, "");
    const pathTicket =
      result?.path?.shared_state?.value?.ticket || result?.path?.shared_state?.ticket;
    return pathTicket || "INC-441";
  }

  async function doEscalate(mode) {
    if (!lastResult?.system && mode !== "severity") {
      toast("Run an investigation first", true);
      return;
    }
    const person = (lastResult?.owners || [])[0] || null;
    const body = {
      mode,
      system_name: lastResult?.system || null,
      person_name: person,
      ticket_key: ticketFromResult(lastResult),
      severity: "SEV-1",
      reason: `UI escalate (${mode}) from SALUS console`,
    };
    if ((mode === "page_owner" || mode === "manager") && !person) {
      toast("No owner on result to escalate to", true);
      return;
    }
    try {
      const res = await apiFetch("/api/escalate", {
        method: "POST",
        body: JSON.stringify(body),
      }).then((r) => r.json());
      if (res.status === "failed" || res.error) {
        toast(res.error || "Escalate failed", true);
        escalateStatus.textContent = JSON.stringify(res);
        return;
      }
      escalateStatus.textContent = `Escalated · ${res.kind} → ${res.person || res.manager || res.severity || res.ticket_key || "ok"}`;
      toast(`Escalation complete: ${res.kind}`);
      setTrackState("01", "done");
      panelAct.textContent =
        `${panelAct.textContent} · Escalation: ${res.kind} (${res.person || res.manager || res.severity || "done"}).`;
      if (chatReady) {
        appendChat(
          "salus",
          `Escalation noted after the other sections: ${res.kind} → ${res.person || res.manager || res.severity || res.ticket_key || "ok"}.`
        );
      }
    } catch (e) {
      toast(String(e.message || e), true);
    }
  }

  async function runAsk(question) {
    activateWorkspace();
    resetRunUI();
    document.body.classList.add("is-running");
    askBtn.disabled = true;
    setTrackState("01", "running");
    setTrackState("02", "running");
    setTrackState("03", "running");

    const params = new URLSearchParams({
      question,
      user_id: "person:sam",
    });
    if (sessionId) params.set("session_id", sessionId);
    if (authRequired) params.set("api_key", getApiKey());
    const oai = getOpenAIKey();
    if (oai) params.set("openai_key", oai);

    try {
      const es = new EventSource(`/api/ask/stream?${params.toString()}`);
      await new Promise((resolve, reject) => {
        es.onmessage = (msg) => {
          const evt = JSON.parse(msg.data);
          if (evt.type === "step") {
            pushStep(evt.agent, evt.action);
          } else if (evt.type === "handoff") {
            pushStep(evt.from, `handoff → ${evt.to}`);
          } else if (evt.type === "system_focus" && evt.system) {
            loadGraph(evt.system);
            graphFocus.textContent = `Focus · ${evt.system}`;
            setTrackState("01", "running");
          } else if (evt.type === "graph_insight" && evt.system) {
            loadGraph(evt.system);
            setTrackState("01", "running");
            setTrackState("03", "running");
          } else if (evt.type === "result") {
            renderResult(evt);
          } else if (evt.type === "error") {
            answerBox.textContent = evt.message || "Run failed";
            es.close();
            reject(new Error(evt.message));
          } else if (evt.type === "done") {
            es.close();
            resolve();
          }
        };
        es.onerror = () => {
          es.close();
          reject(new Error("stream interrupted"));
        };
      });
    } catch (err) {
      try {
        const res = await apiFetch("/api/ask", {
          method: "POST",
          body: JSON.stringify({
            question,
            user_id: "person:sam",
            session_id: sessionId,
            openai_api_key: getOpenAIKey() || null,
          }),
        }).then((r) => r.json());
        (res.steps || []).forEach((s) => pushStep(s.agent, s.action));
        renderResult(res);
      } catch (e2) {
        answerBox.textContent = String(err.message || e2);
      }
    } finally {
      document.body.classList.remove("is-running");
      askBtn.disabled = false;
    }
  }

  askForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = questionInput.value.trim();
    if (!q) return;
    runAsk(q);
  });

  $$("#prompts [data-q]").forEach((btn) => {
    btn.addEventListener("click", () => {
      questionInput.value = btn.getAttribute("data-q");
      runAsk(questionInput.value);
    });
  });

  $$("[data-export]").forEach((btn) => {
    btn.addEventListener("click", () => doExport(btn.getAttribute("data-export")));
  });

  $$("[data-escalate]").forEach((btn) => {
    btn.addEventListener("click", () => doEscalate(btn.getAttribute("data-escalate")));
  });

  $$(".track-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-track");
      const panel = document.querySelector(`.track-panel[data-panel="${id}"]`);
      if (panel) panel.scrollIntoView({ behavior: "smooth", block: "center" });
      $$(".track-item").forEach((t) => t.classList.remove("is-active"));
      btn.classList.add("is-active");
    });
  });

  pathFindBtn?.addEventListener("click", () => {
    tracePath(pathFrom.value, pathTo.value);
  });

  pathClearBtn?.addEventListener("click", () => {
    clearPathHighlight();
    graphFocus.textContent = "Pick systems or run a question to light a path";
  });

  chatFollowForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    if (!chatReady) {
      toast("Wait for the path / investigation to finish first", true);
      return;
    }
    const q = chatFollow.value.trim();
    if (!q) return;
    appendChat("user", q);
    chatFollow.value = "";
    // Follow-ups re-run the full agent path; narration lands after sections again
    runAsk(q);
  });

  boot();
})();
