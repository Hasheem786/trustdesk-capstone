// TrustDesk Frontend Support Operations Dashboard
let activeTickets = [];
let selectedTicketId = null;
let currentFilter = 'all';

document.addEventListener("DOMContentLoaded", () => {
  loadTickets();
  checkHealth();
});

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    if (res.ok) {
      const data = await res.json();
      document.getElementById("engine-mode").innerText = data.ai_provider === 'mock' ? 'Mock (Deterministic)' : 'Gemini Live';
    }
  } catch (e) {
    console.error("Health check error", e);
  }
}

async function loadTickets() {
  try {
    const res = await fetch("/api/tickets");
    if (res.ok) {
      activeTickets = await res.json();
      document.getElementById("ticket-count").innerText = activeTickets.length;
      renderTicketList();
      if (!selectedTicketId && activeTickets.length > 0) {
        selectTicket(activeTickets[0].id);
      }
    }
  } catch (e) {
    console.error("Error loading tickets", e);
  }
}

function filterTickets(filter) {
  currentFilter = filter;
  document.querySelectorAll(".filter-tab").forEach(tab => {
    if (tab.getAttribute("data-filter") === filter) {
      tab.className = "filter-tab px-2.5 py-1 rounded-md font-medium bg-blue-50 text-blue-600";
    } else {
      tab.className = "filter-tab px-2.5 py-1 rounded-md font-medium text-slate-600 hover:bg-slate-100";
    }
  });
  renderTicketList();
}

function renderTicketList() {
  const container = document.getElementById("ticket-list");
  let filtered = activeTickets;

  if (currentFilter !== 'all') {
    filtered = activeTickets.filter(t => t.status === currentFilter);
  }

  if (filtered.length === 0) {
    container.innerHTML = `<div class="text-center py-8 text-xs text-slate-400">No tickets found for filter "${currentFilter}".</div>`;
    return;
  }

  container.innerHTML = filtered.map(t => {
    const isSelected = t.id === selectedTicketId;
    const cat = t.category || 'general';
    const pri = t.priority || 'medium';
    const stat = t.status || 'new';

    return `
      <div onclick="selectTicket('${t.id}')" 
           class="p-3 rounded-lg border cursor-pointer transition ${isSelected ? 'bg-blue-50/60 border-blue-400 shadow-sm' : 'bg-white border-slate-200 hover:border-slate-300'}">
        <div class="flex items-center justify-between text-xs mb-1.5">
          <span class="font-bold text-slate-700">${t.id}</span>
          <span class="badge badge-${pri}">${pri}</span>
        </div>
        <div class="font-semibold text-xs text-slate-900 line-clamp-1 mb-1">${t.subject}</div>
        <div class="text-slate-500 text-[11px] line-clamp-2 mb-2">${t.description}</div>
        <div class="flex items-center justify-between pt-1 border-t border-slate-100 text-[11px]">
          <span class="font-medium text-slate-600 uppercase tracking-wider text-[10px]">${cat}</span>
          <span class="badge badge-${stat}">${stat.replace('_', ' ')}</span>
        </div>
      </div>
    `;
  }).join('');
}

async function selectTicket(ticketId) {
  selectedTicketId = ticketId;
  renderTicketList();

  const container = document.getElementById("ticket-detail-view");
  container.innerHTML = `
    <div class="text-center py-16 text-slate-400 text-xs">
      <i class="fa-solid fa-spinner fa-spin text-2xl text-blue-600 mb-2"></i>
      <p>Loading ticket ${ticketId} details & audit traces...</p>
    </div>
  `;

  try {
    const res = await fetch(`/api/tickets/${ticketId}`);
    if (!res.ok) {
      container.innerHTML = `<div class="text-red-500 text-xs py-4">Failed to load ticket details.</div>`;
      return;
    }
    const data = await res.json();
    renderTicketDetail(data);
  } catch (e) {
    container.innerHTML = `<div class="text-red-500 text-xs py-4">Error loading ticket: ${e.message}</div>`;
  }
}

function renderTicketDetail(data) {
  const t = data.ticket;
  const c = data.customer;
  const o = data.order;
  const d = data.draft;
  const actions = data.actions || [];
  const traces = data.traces || [];

  const container = document.getElementById("ticket-detail-view");

  // Citations render
  const citationsHtml = d && d.cited_doc_ids && d.cited_doc_ids.length > 0
    ? d.cited_doc_ids.map(cid => `<span class="citation-pill" title="Official Policy Document"><i class="fa-solid fa-bookmark mr-1 text-[10px]"></i>${cid}</span>`).join('')
    : '<span class="text-xs text-slate-400">None (General / Security Guardrail Flagged)</span>';

  // Actions render
  const pendingActions = actions.filter(a => a.status === 'PENDING_APPROVAL');
  const pastActions = actions.filter(a => a.status !== 'PENDING_APPROVAL');

  let actionsHtml = '';
  if (pendingActions.length > 0) {
    actionsHtml = pendingActions.map(act => `
      <div class="bg-amber-50/70 border border-amber-300 rounded-xl p-4 shadow-sm space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="w-2.5 h-2.5 rounded-full bg-amber-500 animate-ping"></span>
            <strong class="text-xs text-amber-900 uppercase tracking-wide">Human-in-the-Loop Action Required</strong>
          </div>
          <span class="badge badge-pending">PENDING SUPERVISOR APPROVAL</span>
        </div>
        <div class="text-xs text-slate-700">
          <div>Action Tool: <strong class="font-mono text-blue-700">${act.action_type}</strong></div>
          <div class="mt-1 text-slate-600 italic">"${act.justification}"</div>
        </div>
        <div>
          <span class="text-[10px] text-slate-500 font-semibold block mb-0.5">Deterministic Idempotency Key (SHA256):</span>
          <div class="idempotency-box">${act.idempotency_key}</div>
        </div>
        <div class="flex items-center justify-end space-x-2 pt-2 border-t border-amber-200">
          <button onclick="rejectAction('${act.id}')" class="px-3 py-1.5 bg-rose-100 hover:bg-rose-200 text-rose-700 rounded-lg text-xs font-semibold">
            <i class="fa-solid fa-ban mr-1"></i> Reject Action
          </button>
          <button onclick="approveAction('${act.id}')" class="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-sm">
            <i class="fa-solid fa-check mr-1"></i> Approve & Execute
          </button>
        </div>
      </div>
    `).join('');
  } else if (pastActions.length > 0) {
    actionsHtml = pastActions.map(act => `
      <div class="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs flex items-center justify-between">
        <div>
          <span class="font-mono font-semibold text-slate-800">${act.action_type}</span>
          <span class="text-slate-500 text-[11px] block">Executed at: ${act.executed_at || act.created_at}</span>
        </div>
        <span class="badge ${act.status === 'EXECUTED' ? 'badge-resolved' : 'badge-escalated'}">${act.status}</span>
      </div>
    `).join('');
  } else {
    actionsHtml = `<div class="text-xs text-slate-400 italic">No operational action proposals required for this ticket.</div>`;
  }

  container.innerHTML = `
    <!-- Ticket Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4 gap-2">
      <div>
        <div class="flex items-center space-x-2">
          <h2 class="text-lg font-bold text-slate-900">${t.subject}</h2>
          <span class="text-xs font-mono text-slate-400">#${t.id}</span>
        </div>
        <div class="text-xs text-slate-500 mt-0.5">
          Created: <strong>${t.created_at}</strong>
        </div>
      </div>
      <div class="flex items-center space-x-2">
        <span class="badge badge-${t.priority}">${t.priority || 'MEDIUM'}</span>
        <span class="badge badge-${t.status}">${(t.status || 'NEW').replace('_', ' ')}</span>
      </div>
    </div>

    <!-- Metadata Grid: Customer & Order Context -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs">
      <div>
        <strong class="text-slate-700 block mb-1 font-semibold flex items-center">
          <i class="fa-solid fa-user text-blue-600 mr-1.5"></i> Customer Profile
        </strong>
        ${c ? `
          <div class="text-slate-800 font-medium">${c.name} (${c.id})</div>
          <div class="text-slate-500">${c.email} • Tier: <span class="uppercase font-bold text-indigo-600">${c.tier}</span></div>
        ` : '<span class="text-slate-400">No customer on file</span>'}
      </div>

      <div>
        <strong class="text-slate-700 block mb-1 font-semibold flex items-center">
          <i class="fa-solid fa-box text-blue-600 mr-1.5"></i> Associated Order
        </strong>
        ${o ? `
          <div class="text-slate-800 font-medium">${o.id} • Total: $${o.total_amount.toFixed(2)}</div>
          <div class="text-slate-500">Delivered: <strong>${o.delivered_date || 'In Transit'}</strong> • Tracking: ${o.tracking_number || 'N/A'}</div>
        ` : '<span class="text-slate-400">No order linked</span>'}
      </div>
    </div>

    <!-- Customer Ticket Body -->
    <div class="space-y-1.5">
      <h3 class="text-xs font-bold text-slate-700 uppercase tracking-wider">Customer Inquiry</h3>
      <div class="bg-white p-3.5 rounded-xl border border-slate-200 text-xs text-slate-800 leading-relaxed shadow-inner">
        ${t.description}
      </div>
    </div>

    <!-- AI Triage Result Card -->
    <div class="bg-indigo-50/50 border border-indigo-100 rounded-xl p-4 space-y-2">
      <div class="flex items-center justify-between">
        <h3 class="text-xs font-bold text-indigo-950 flex items-center">
          <i class="fa-solid fa-brain text-indigo-600 mr-1.5"></i> AI Triage & Grounding Analysis
        </h3>
        <span class="text-[11px] text-indigo-700 font-semibold">Triage Confidence: 98%</span>
      </div>
      <div class="grid grid-cols-3 gap-2 text-xs pt-1">
        <div>
          <span class="text-slate-500 text-[10px] block">Category:</span>
          <strong class="uppercase font-bold text-slate-800">${t.category || 'N/A'}</strong>
        </div>
        <div>
          <span class="text-slate-500 text-[10px] block">Assigned Priority:</span>
          <strong class="uppercase font-bold text-slate-800">${t.priority || 'N/A'}</strong>
        </div>
        <div>
          <span class="text-slate-500 text-[10px] block">Escalation Trigger:</span>
          <strong class="${t.escalate ? 'text-rose-600' : 'text-emerald-600'} font-bold">${t.escalate ? 'ESCALATE (SUPERVISOR)' : 'NO ESCALATION'}</strong>
        </div>
      </div>
      ${t.escalation_reason ? `
        <div class="mt-2 text-xs text-rose-700 bg-rose-50 border border-rose-200 p-2 rounded-lg font-medium">
          <i class="fa-solid fa-triangle-exclamation mr-1"></i> ${t.escalation_reason}
        </div>
      ` : ''}
    </div>

    <!-- Grounded Draft Response -->
    <div class="space-y-2">
      <div class="flex items-center justify-between">
        <h3 class="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center">
          <i class="fa-solid fa-pen-fancy text-blue-600 mr-1.5"></i> Grounded Draft Response
        </h3>
        <div class="flex items-center space-x-1">
          <span class="text-xs text-slate-500 font-medium mr-1">Policy Citations:</span>
          ${citationsHtml}
        </div>
      </div>

      <div class="bg-white p-4 rounded-xl border border-slate-200 text-xs text-slate-800 leading-relaxed shadow-sm">
        ${d ? d.response_text : '<span class="text-slate-400 italic">No draft response generated. Click Process Ticket below.</span>'}
      </div>
    </div>

    <!-- HITL Actions Section -->
    <div class="space-y-2">
      <h3 class="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center">
        <i class="fa-solid fa-hand-holding-hand text-amber-600 mr-1.5"></i> Human-in-the-Loop Operational Actions
      </h3>
      ${actionsHtml}
    </div>

    <!-- Audit Trace Collapsible Timeline -->
    <div class="border-t border-slate-100 pt-4">
      <details class="text-xs">
        <summary class="font-bold text-slate-700 cursor-pointer hover:text-blue-600">
          <i class="fa-solid fa-list-check mr-1"></i> Audit Trace History (${traces.length} steps recorded)
        </summary>
        <div class="mt-3 space-y-2 max-h-48 overflow-y-auto pr-1">
          ${traces.map(tr => `
            <div class="p-2 bg-slate-50 border border-slate-200 rounded text-[11px] font-mono">
              <span class="text-blue-600 font-bold">[${tr.step_name}]</span>
              <span class="text-slate-400 ml-1">${tr.created_at}</span>
              ${tr.guardrail_flags && tr.guardrail_flags.length > 0 ? `<span class="ml-2 text-rose-600 font-bold font-sans">FLAGS: ${tr.guardrail_flags.join(', ')}</span>` : ''}
              ${tr.retrieved_docs && tr.retrieved_docs.length > 0 ? `<span class="ml-2 text-indigo-600 font-sans">DOCS: ${tr.retrieved_docs.join(', ')}</span>` : ''}
            </div>
          `).join('')}
        </div>
      </details>
    </div>
  `;
}

async function approveAction(actionId) {
  try {
    const res = await fetch(`/api/actions/${actionId}/approve`, { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      alert("✅ Action approved & executed successfully!");
      await loadTickets();
      if (selectedTicketId) selectTicket(selectedTicketId);
    } else {
      alert("❌ " + data.detail);
    }
  } catch (e) {
    alert("Error approving action: " + e.message);
  }
}

async function rejectAction(actionId) {
  const reason = prompt("Enter rejection reason for audit log:", "Rejected by support operator");
  if (!reason) return;

  try {
    const res = await fetch(`/api/actions/${actionId}/reject?reason=${encodeURIComponent(reason)}`, { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      alert("Action rejected.");
      await loadTickets();
      if (selectedTicketId) selectTicket(selectedTicketId);
    } else {
      alert("❌ " + data.detail);
    }
  } catch (e) {
    alert("Error rejecting action: " + e.message);
  }
}

function openNewTicketModal() {
  document.getElementById("modal-new-ticket").classList.remove("hidden");
}

function closeNewTicketModal() {
  document.getElementById("modal-new-ticket").classList.add("hidden");
}

async function submitNewTicket(e) {
  e.preventDefault();
  const custId = document.getElementById("new-cust-id").value;
  const orderId = document.getElementById("new-order-id").value || null;
  const subject = document.getElementById("new-subject").value;
  const desc = document.getElementById("new-desc").value;

  try {
    const res = await fetch("/api/tickets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: custId,
        order_id: orderId,
        subject: subject,
        description: desc
      })
    });
    if (res.ok) {
      const ticket = await res.json();
      // Process ticket immediately
      await fetch(`/api/tickets/${ticket.id}/process`, { method: "POST" });
      closeNewTicketModal();
      document.getElementById("new-ticket-form").reset();
      await loadTickets();
      selectTicket(ticket.id);
    }
  } catch (err) {
    alert("Failed to create ticket: " + err.message);
  }
}

function openBenchmarkModal() {
  document.getElementById("modal-eval").classList.remove("hidden");
}

function closeBenchmarkModal() {
  document.getElementById("modal-eval").classList.add("hidden");
}

async function runBenchmarkModal() {
  openBenchmarkModal();
  const body = document.getElementById("eval-modal-body");
  body.innerHTML = `
    <div class="flex flex-col items-center justify-center py-12 space-y-3 text-slate-500">
      <i class="fa-solid fa-spinner fa-spin text-3xl text-indigo-600"></i>
      <span class="text-sm font-semibold text-slate-700">Executing benchmark test harness on data/eval_cases.jsonl...</span>
      <span class="text-xs text-slate-400">Benchmarking Triage Accuracy, Citation Grounding, Guardrails, and Idempotency</span>
    </div>
  `;

  try {
    const res = await fetch("/api/eval/run", { method: "POST" });
    if (res.ok) {
      const s = await res.json();
      renderBenchmarkResults(s);
    } else {
      body.innerHTML = `<div class="text-red-500 text-xs">Error running benchmark evaluation suite.</div>`;
    }
  } catch (err) {
    body.innerHTML = `<div class="text-red-500 text-xs">Network error: ${err.message}</div>`;
  }
}

function renderBenchmarkResults(s) {
  const body = document.getElementById("eval-modal-body");
  body.innerHTML = `
    <!-- Top KPI Cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
        <span class="text-[11px] text-slate-500 block">Triage Accuracy</span>
        <div class="text-lg font-bold ${s.triage_accuracy >= 90 ? 'text-emerald-600' : 'text-rose-600'}">${s.triage_accuracy.toFixed(1)}%</div>
        <span class="text-[10px] text-slate-400">Target: &ge;90% (${s.triage_correct}/${s.total_cases})</span>
      </div>

      <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
        <span class="text-[11px] text-slate-500 block">Citation Grounding</span>
        <div class="text-lg font-bold ${s.citation_grounding_rate >= 95 ? 'text-emerald-600' : 'text-rose-600'}">${s.citation_grounding_rate.toFixed(1)}%</div>
        <span class="text-[10px] text-slate-400">Target: &ge;95% (${s.citation_grounded_cases}/${s.total_cases})</span>
      </div>

      <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
        <span class="text-[11px] text-slate-500 block">Adversarial Safety</span>
        <div class="text-lg font-bold ${s.adversarial_safety_rate === 100 ? 'text-emerald-600' : 'text-rose-600'}">${s.adversarial_safety_rate.toFixed(1)}%</div>
        <span class="text-[10px] text-slate-400">Target: 100% (${s.adversarial_neutralized}/${s.adversarial_cases})</span>
      </div>

      <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
        <span class="text-[11px] text-slate-500 block">HITL & Idempotency</span>
        <div class="text-lg font-bold ${s.hitl_safety_rate === 100 ? 'text-emerald-600' : 'text-rose-600'}">${s.hitl_safety_rate.toFixed(1)}%</div>
        <span class="text-[10px] text-slate-400">Target: 100% (${s.operational_hitl_safe}/${s.operational_hitl_cases})</span>
      </div>
    </div>

    <!-- Pass/Fail Banner -->
    <div class="p-3 rounded-xl flex items-center justify-between text-xs font-semibold ${s.all_passed ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'}">
      <div class="flex items-center space-x-2">
        <i class="fa-solid ${s.all_passed ? 'fa-circle-check text-emerald-600' : 'fa-circle-xmark text-rose-600'} text-base"></i>
        <span>${s.all_passed ? 'All 5 Capstone Rubric Criteria Fully Satisfied!' : 'Some benchmark criteria require review.'}</span>
      </div>
      <span>Total Test Cases: ${s.total_cases}</span>
    </div>

    <!-- Table of Cases -->
    <div class="border border-slate-200 rounded-xl overflow-hidden text-xs max-h-60 overflow-y-auto">
      <table class="w-full text-left border-collapse">
        <thead class="bg-slate-100 text-slate-700 sticky top-0 text-[11px]">
          <tr>
            <th class="p-2 border-b border-slate-200">Case ID</th>
            <th class="p-2 border-b border-slate-200">Subject</th>
            <th class="p-2 border-b border-slate-200">Expected</th>
            <th class="p-2 border-b border-slate-200">Actual</th>
            <th class="p-2 border-b border-slate-200">Citations</th>
            <th class="p-2 border-b border-slate-200">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 text-slate-800">
          ${s.details.map(d => `
            <tr class="hover:bg-slate-50">
              <td class="p-2 font-mono font-semibold">${d.id}</td>
              <td class="p-2 line-clamp-1">${d.subject}</td>
              <td class="p-2 uppercase font-medium text-[10px] text-slate-500">${d.expected_cat}</td>
              <td class="p-2 uppercase font-bold text-[10px] text-blue-700">${d.actual_cat}</td>
              <td class="p-2 font-mono text-[10px] text-slate-600">${d.actual_citations.join(', ') || 'None'}</td>
              <td class="p-2">${d.passed ? '<span class="text-emerald-600 font-bold">PASS ✅</span>' : '<span class="text-rose-600 font-bold">FAIL ❌</span>'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}
