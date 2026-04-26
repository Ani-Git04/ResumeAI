const $ = (id) => document.getElementById(id);

const state = {
  resumePdfBase64: "",
  resumeText: "",
  jobDescription: "",
  resumeSkills: [],
  jdSkills: [],
  missingSkills: [],
  interviewSkills: [],
  questionsBySkill: {},
  activeSkillIdx: 0,
  activeQIdx: 0,
  qaBySkill: {}, // { skill: [{q,a}] }
  conversation: [], // chat transcript
  results: null,
  roadmapMarkdown: "",
  radar: null,
};

function setLoader(on, text = "Working…") {
  const box = $("globalLoader");
  const t = $("globalLoaderText");
  if (!box || !t) return;
  t.textContent = text;
  box.classList.toggle("hidden", !on);
  box.classList.toggle("flex", on);
}

function setStep(stepNum) {
  document.querySelectorAll(".step").forEach((el) => {
    const s = Number(el.dataset.step);
    el.classList.toggle("active", s === stepNum);
  });

  $("panelUpload").classList.toggle("hidden", stepNum !== 1);
  $("panelInterview").classList.toggle("hidden", stepNum !== 2);
  $("panelResults").classList.toggle("hidden", stepNum !== 3);
}

async function apiPost(path, payload) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data?.error || `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

function toast(targetId, text, tone = "info") {
  const el = $(targetId);
  if (!el) return;
  const color =
    tone === "error"
      ? "text-red-300"
      : tone === "success"
        ? "text-emerald-300"
        : "text-white/70";
  el.className = `text-xs ${color}`;
  el.textContent = text;
}

function bytesToHuman(bytes) {
  const units = ["B", "KB", "MB", "GB"];
  let n = bytes;
  let u = 0;
  while (n >= 1024 && u < units.length - 1) {
    n /= 1024;
    u++;
  }
  return `${n.toFixed(u ? 1 : 0)} ${units[u]}`;
}

function addBubble(role, content) {
  const wrap = document.createElement("div");
  wrap.className = "w-full flex";
  const b = document.createElement("div");
  b.className = `bubble ${role === "user" ? "user" : "assistant"}`;
  b.textContent = content;
  wrap.appendChild(b);
  $("chatLog").appendChild(wrap);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
}

function setTyping(on) {
  $("typingDot").classList.toggle("hidden", !on);
  $("typingText").classList.toggle("hidden", !on);
}

function currentSkill() {
  return state.interviewSkills[state.activeSkillIdx] || "";
}

function currentQuestion() {
  const sk = currentSkill();
  const qs = state.questionsBySkill[sk] || [];
  return qs[state.activeQIdx] || "";
}

function updateInterviewSidebar() {
  const totalSkills = state.interviewSkills.length;
  $("pillSkillCount").textContent = `${totalSkills} skills`;
  $("activeSkill").textContent = currentSkill() || "—";

  const totalQuestions = totalSkills * 3;
  const doneQuestions = state.activeSkillIdx * 3 + state.activeQIdx;
  const pct = totalQuestions ? Math.round((doneQuestions / totalQuestions) * 100) : 0;
  $("progressBar").style.width = `${pct}%`;
  $("progressText").textContent = `${doneQuestions}/${totalQuestions} questions`;

  const ms = $("missingSkillsList");
  ms.innerHTML = "";
  (state.missingSkills || []).slice(0, 18).forEach((s) => {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = s;
    ms.appendChild(tag);
  });
}

function nextQuestion() {
  const sk = currentSkill();
  if (!sk) return null;

  const q = currentQuestion();
  if (!q) return null;

  addBubble(
    "assistant",
    `(${sk}) ${q}`
  );
  state.conversation.push({ role: "assistant", content: `(${sk}) ${q}` });
  updateInterviewSidebar();
  return q;
}

function advancePointer() {
  state.activeQIdx += 1;
  if (state.activeQIdx >= 3) {
    state.activeQIdx = 0;
    state.activeSkillIdx += 1;
  }
}

function recordAnswer(skill, question, answer) {
  if (!state.qaBySkill[skill]) state.qaBySkill[skill] = [];
  state.qaBySkill[skill].push({ q: question, a: answer });
}

async function interviewerReply(skill, question) {
  setTyping(true);
  try {
    const data = await apiPost("/api/chat", {
      conversation: state.conversation,
      active_skill: skill,
      current_question: question,
    });
    const msg = (data.assistant_message || "").trim();
    if (msg) {
      addBubble("assistant", msg);
      state.conversation.push({ role: "assistant", content: msg });
    }
  } finally {
    setTyping(false);
  }
}

async function startInterview() {
  setStep(2);
  state.conversation = [];
  state.qaBySkill = {};
  state.activeSkillIdx = 0;
  state.activeQIdx = 0;

  $("chatLog").innerHTML = "";

  addBubble(
    "assistant",
    "Welcome. I’ll run a short, high-signal interview. One question at a time. Answer with real examples when possible."
  );
  state.conversation.push({
    role: "assistant",
    content:
      "Welcome. I’ll run a short, high-signal interview. One question at a time. Answer with real examples when possible.",
  });

  updateInterviewSidebar();
  nextQuestion();
}

function pickInterviewSkills() {
  // Interview: prioritize missing skills + top JD skills, cap for UX.
  const set = new Map();
  (state.missingSkills || []).forEach((s) => set.set(s.toLowerCase(), s));
  (state.jdSkills || []).forEach((s) => set.set(s.toLowerCase(), s));
  const merged = Array.from(set.values());
  state.interviewSkills = merged.slice(0, 8); // premium feel: focused interview
}

async function runAssessmentPipeline() {
  state.jobDescription = ($("jobDescription").value || "").trim();
  if (!state.resumePdfBase64) {
    toast("uploadHint", "Please upload a PDF resume first.", "error");
    return;
  }
  if (!state.jobDescription || state.jobDescription.length < 40) {
    toast("uploadHint", "Please paste a more complete job description (at least ~40 characters).", "error");
    return;
  }

  try {
    setLoader(true, "Parsing resume…");
    toast("uploadHint", "Parsing resume…", "info");
    const parsed = await apiPost("/api/parse_resume", {
      resume_pdf_base64: state.resumePdfBase64,
    });
    state.resumeText = parsed.resume_text || "";

    setLoader(true, "Extracting skills…");
    toast("uploadHint", "Extracting skills with Groq…", "info");
    const skills = await apiPost("/api/extract_skills", {
      resume_text: state.resumeText,
      job_description: state.jobDescription,
    });
    state.resumeSkills = skills.resume_skills || [];
    state.jdSkills = skills.jd_skills || [];
    state.missingSkills = skills.missing_skills || [];

    pickInterviewSkills();

    setLoader(true, "Generating interview questions…");
    toast("uploadHint", "Generating interview questions…", "info");
    const qs = await apiPost("/api/generate_questions", {
      skills: state.interviewSkills,
    });
    state.questionsBySkill = qs.questions_by_skill || {};

    toast("uploadHint", "Ready. Starting interview…", "success");
    setLoader(false);
    await startInterview();
  } catch (e) {
    setLoader(false);
    toast("uploadHint", e.message || "Something went wrong.", "error");
  }
}

async function finishAndGenerateResults() {
  try {
    setLoader(true, "Scoring your answers…");
    const evalRes = await apiPost("/api/evaluate_answers", {
      job_description: state.jobDescription,
      qa_by_skill: state.qaBySkill,
    });
    const scoredSkills = evalRes.skills || [];

    setLoader(true, "Building your learning roadmap…");
    const planRes = await apiPost("/api/learning_plan", {
      job_description: state.jobDescription,
      missing_skills: state.missingSkills,
      scored_skills: scoredSkills,
    });

    state.results = scoredSkills;
    state.roadmapMarkdown = planRes.learning_plan_markdown || "";
    setLoader(false);
    renderResults();
  } catch (e) {
    setLoader(false);
    addBubble("assistant", `I hit an error while generating results: ${e.message || e}`);
  }
}

function renderGapTable() {
  const wrap = $("gapTable");
  const missing = state.missingSkills || [];
  if (!missing.length) {
    wrap.innerHTML = `<div class="text-sm text-white/60">No clear gaps detected from JD vs resume.</div>`;
    return;
  }

  wrap.innerHTML = `
    <div class="overflow-hidden rounded-xl border border-white/10">
      <table class="w-full text-sm">
        <thead class="bg-white/5 text-white/70">
          <tr>
            <th class="text-left px-4 py-3">Missing skill</th>
            <th class="text-left px-4 py-3">Priority</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-white/10">
          ${missing
            .slice(0, 16)
            .map((s, i) => {
              const p = i < 4 ? "High" : i < 10 ? "Medium" : "Nice-to-have";
              const badge =
                p === "High"
                  ? "bg-emerald-500/15 text-emerald-200 border-emerald-400/25"
                  : p === "Medium"
                    ? "bg-indigo-500/15 text-indigo-200 border-indigo-400/25"
                    : "bg-white/5 text-white/70 border-white/10";
              return `
                <tr>
                  <td class="px-4 py-3">${s}</td>
                  <td class="px-4 py-3">
                    <span class="inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${badge}">
                      ${p}
                    </span>
                  </td>
                </tr>
              `;
            })
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderScoreCards() {
  const wrap = $("scoreCards");
  wrap.innerHTML = "";
  const skills = (state.results || []).slice(0, 12);
  skills.forEach((x) => {
    const card = document.createElement("div");
    card.className = "rounded-2xl border border-white/10 bg-white/5 p-4";
    const score = Number(x.score ?? 0);
    const pct = Math.max(0, Math.min(100, Math.round((score / 10) * 100)));
    card.innerHTML = `
      <div class="flex items-start justify-between gap-3">
        <div>
          <div class="font-semibold">${x.skill || "Skill"}</div>
          <div class="text-xs text-white/60">${x.level || "—"} • ${score}/10</div>
        </div>
        <div class="h-10 w-10 rounded-2xl border border-white/10 bg-white/5 flex items-center justify-center text-sm font-semibold">
          ${score}
        </div>
      </div>
      <div class="mt-3 h-2 w-full rounded-full bg-white/10 overflow-hidden">
        <div class="h-2 rounded-full bg-primary" style="width:${pct}%"></div>
      </div>
      <div class="mt-3 text-xs text-white/60">${(x.rationale || "").slice(0, 160)}</div>
    `;
    wrap.appendChild(card);
  });
}

function renderRadar() {
  const skills = (state.results || []).slice(0, 8);
  const labels = skills.map((s) => s.skill || "");
  const values = skills.map((s) => Number(s.score ?? 0));

  const ctx = $("radarChart");
  if (!ctx) return;

  if (state.radar) state.radar.destroy();

  state.radar = new Chart(ctx, {
    type: "radar",
    data: {
      labels,
      datasets: [
        {
          label: "Proficiency",
          data: values,
          borderColor: "rgba(99,102,241,0.9)",
          backgroundColor: "rgba(99,102,241,0.22)",
          pointBackgroundColor: "rgba(34,197,94,0.85)",
          pointBorderColor: "rgba(255,255,255,0.4)",
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        r: {
          suggestedMin: 0,
          suggestedMax: 10,
          ticks: { display: false },
          grid: { color: "rgba(255,255,255,0.08)" },
          angleLines: { color: "rgba(255,255,255,0.08)" },
          pointLabels: { color: "rgba(255,255,255,0.75)", font: { size: 11 } },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.raw}/10`,
          },
        },
      },
    },
  });
}

function renderRoadmap() {
  const md = state.roadmapMarkdown || "";
  const html = marked.parse(md);
  $("roadmap").innerHTML = html || `<div class="text-sm text-white/60">No roadmap generated.</div>`;
}

function renderResults() {
  setStep(3);
  renderScoreCards();
  renderRadar();
  renderGapTable();
  renderRoadmap();
}

function bindUploadUI() {
  const dz = $("dropzone");
  const fileInput = $("resumeFile");

  const openPicker = () => fileInput.click();
  dz.addEventListener("click", openPicker);

  const onFile = async (file) => {
    if (!file) return;
    if (file.type !== "application/pdf") {
      toast("uploadHint", "Please upload a PDF file.", "error");
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      toast("uploadHint", "Please use a PDF smaller than 8MB for best reliability.", "error");
      return;
    }

    $("fileMeta").textContent = `${file.name} • ${bytesToHuman(file.size)}`;
    toast("uploadHint", "Reading PDF…", "info");

    const buf = await file.arrayBuffer();
    const bytes = new Uint8Array(buf);
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
    }
    state.resumePdfBase64 = btoa(binary);
    toast("uploadHint", "Resume loaded. Paste JD and continue.", "success");
  };

  fileInput.addEventListener("change", (e) => onFile(e.target.files?.[0]));

  dz.addEventListener("dragover", (e) => {
    e.preventDefault();
    dz.classList.add("dragover");
  });
  dz.addEventListener("dragleave", () => dz.classList.remove("dragover"));
  dz.addEventListener("drop", (e) => {
    e.preventDefault();
    dz.classList.remove("dragover");
    onFile(e.dataTransfer.files?.[0]);
  });
}

function bindChatUI() {
  const input = $("chatInput");
  const send = $("btnSend");

  const doSend = async () => {
    const txt = (input.value || "").trim();
    if (!txt) return;

    const sk = currentSkill();
    const q = currentQuestion();
    if (!sk || !q) {
      input.value = "";
      await finishAndGenerateResults();
      return;
    }

    addBubble("user", txt);
    state.conversation.push({ role: "user", content: txt });
    recordAnswer(sk, q, txt);
    input.value = "";

    // Short interviewer response (ack + follow-up if needed)
    try {
      await interviewerReply(sk, q);
    } catch {
      // fallback silently; the interview can still proceed
    }

    advancePointer();
    const next = currentQuestion();
    if (!next) {
      await finishAndGenerateResults();
      return;
    }
    nextQuestion();
  };

  send.addEventListener("click", doSend);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doSend();
  });

  $("btnFinishEarly").addEventListener("click", finishAndGenerateResults);
}

function bindNav() {
  $("ctaStart").addEventListener("click", () => {
    window.scrollTo({ top: $("panelUpload").offsetTop - 10, behavior: "smooth" });
    setStep(1);
  });
  $("btnExtract").addEventListener("click", runAssessmentPipeline);
  $("btnRestart").addEventListener("click", () => window.location.reload());
}

function init() {
  setStep(1);
  bindUploadUI();
  bindChatUI();
  bindNav();
}

init();
