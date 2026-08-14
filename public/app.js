/**
 * Adobe University Hackathon 2026 - Leaderboard Result & Query Portal
 */

let state = {
  activeTab: "search",
  query: "",
  filterBy: "all",
  // Multi-field filters
  mfName: "",
  mfTeam: "",
  mfCollege: "",
  mfProfile: "",
  // View & Pagination
  view: "cards", // "cards" or "flat"
  currentPage: 1,
  totalPages: 1,
  limit: 24,
  isLoading: false,
  debounceTimer: null,
  // Current active SQL query
  lastSqlQuery: ""
};

// DOM Elements
const modeTabs = document.getElementById("modeTabs");
const searchInput = document.getElementById("searchInput");
const clearSearchBtn = document.getElementById("clearSearchBtn");
const filterPills = document.getElementById("filterPills");
const quickTags = document.getElementById("quickTags");

const multiFilterForm = document.getElementById("multiFilterForm");
const mfName = document.getElementById("mfName");
const mfTeam = document.getElementById("mfTeam");
const mfCollege = document.getElementById("mfCollege");
const mfProfile = document.getElementById("mfProfile");
const mfResetBtn = document.getElementById("mfResetBtn");

const sqlInput = document.getElementById("sqlInput");
const runSqlBtn = document.getElementById("runSqlBtn");
const sqlResultsContainer = document.getElementById("sqlResultsContainer");
const sqlExecutionStatus = document.getElementById("sqlExecutionStatus");
const sqlTableHead = document.getElementById("sqlTableHead");
const sqlTableBody = document.getElementById("sqlTableBody");
const exportSqlCsvBtn = document.getElementById("exportSqlCsvBtn");

const topCollegesGrid = document.getElementById("topCollegesGrid");

const resultsMainSection = document.getElementById("resultsMainSection");
const resultsGrid = document.getElementById("resultsGrid");
const tableViewContainer = document.getElementById("tableViewContainer");
const flatTableBody = document.getElementById("flatTableBody");
const resultsCountText = document.getElementById("resultsCountText");
const pageInfoText = document.getElementById("pageInfoText");
const loadingSpinner = document.getElementById("loadingSpinner");
const emptyState = document.getElementById("emptyState");
const paginationContainer = document.getElementById("paginationContainer");
const prevPageBtn = document.getElementById("prevPageBtn");
const nextPageBtn = document.getElementById("nextPageBtn");
const pageNumbers = document.getElementById("pageNumbers");

const viewSwitcher = document.getElementById("viewSwitcher");
const exportCsvBtn = document.getElementById("exportCsvBtn");
const exportJsonBtn = document.getElementById("exportJsonBtn");

const statTeams = document.getElementById("statTeams");
const statPlayers = document.getElementById("statPlayers");
const statPages = document.getElementById("statPages");
const statColleges = document.getElementById("statColleges");

// Initialize application
document.addEventListener("DOMContentLoaded", () => {
  loadStats();
  performSearch(1);
  setupEventListeners();
});

function setupEventListeners() {
  // Tab navigation
  modeTabs.addEventListener("click", (e) => {
    const tabBtn = e.target.closest(".mode-tab");
    if (!tabBtn) return;

    const tabName = tabBtn.dataset.tab;
    state.activeTab = tabName;

    modeTabs.querySelectorAll(".mode-tab").forEach(t => t.classList.remove("active"));
    tabBtn.classList.add("active");

    document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
    const activePane = document.getElementById(`pane${capitalize(tabName)}`);
    if (activePane) activePane.classList.add("active");

    // Hide or show main results grid depending on tab
    if (tabName === "sql" || tabName === "analytics") {
      resultsMainSection.style.display = "none";
    } else {
      resultsMainSection.style.display = "block";
      performSearch(1);
    }
  });

  // Tab 1: Smart Search input debouncing
  searchInput.addEventListener("input", (e) => {
    state.query = e.target.value.trim();
    clearSearchBtn.classList.toggle("hidden", state.query.length === 0);

    clearTimeout(state.debounceTimer);
    state.debounceTimer = setTimeout(() => {
      performSearch(1);
    }, 280);
  });

  clearSearchBtn.addEventListener("click", () => {
    searchInput.value = "";
    state.query = "";
    clearSearchBtn.classList.add("hidden");
    searchInput.focus();
    performSearch(1);
  });

  // Filter pills
  filterPills.addEventListener("click", (e) => {
    const btn = e.target.closest(".filter-pill");
    if (!btn) return;

    filterPills.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    state.filterBy = btn.dataset.filter;
    performSearch(1);
  });

  // Quick tags
  quickTags.addEventListener("click", (e) => {
    const btn = e.target.closest(".tag-btn");
    if (!btn) return;

    const queryTag = btn.dataset.query;
    searchInput.value = queryTag;
    state.query = queryTag;
    state.filterBy = "college";
    
    filterPills.querySelectorAll(".filter-pill").forEach(p => {
      p.classList.toggle("active", p.dataset.filter === "college");
    });

    clearSearchBtn.classList.remove("hidden");
    performSearch(1);
  });

  // Tab 2: Multi-Field Form submission
  multiFilterForm.addEventListener("submit", (e) => {
    e.preventDefault();
    state.mfName = mfName.value.trim();
    state.mfTeam = mfTeam.value.trim();
    state.mfCollege = mfCollege.value.trim();
    state.mfProfile = mfProfile.value.trim();
    performSearch(1);
  });

  mfResetBtn.addEventListener("click", () => {
    mfName.value = "";
    mfTeam.value = "";
    mfCollege.value = "";
    mfProfile.value = "";
    state.mfName = "";
    state.mfTeam = "";
    state.mfCollege = "";
    state.mfProfile = "";
    performSearch(1);
  });

  // Tab 3: SQL Console Run & Presets
  runSqlBtn.addEventListener("click", () => {
    executeSqlFromInput();
  });

  document.querySelectorAll(".sql-preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const query = btn.dataset.sql;
      sqlInput.value = query;
      executeSqlFromInput();
    });
  });

  exportSqlCsvBtn.addEventListener("click", () => {
    if (state.lastSqlQuery) {
      window.location.href = `/api/export?format=csv&sql_query=${encodeURIComponent(state.lastSqlQuery)}`;
    }
  });

  // View Switcher (Cards vs Flat Table)
  viewSwitcher.addEventListener("click", (e) => {
    const btn = e.target.closest(".view-btn");
    if (!btn) return;

    viewSwitcher.querySelectorAll(".view-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    state.view = btn.dataset.view;
    performSearch(state.currentPage);
  });

  // Export Buttons
  exportCsvBtn.addEventListener("click", () => triggerExport("csv"));
  exportJsonBtn.addEventListener("click", () => triggerExport("json"));

  // Pagination Next / Prev
  prevPageBtn.addEventListener("click", () => {
    if (state.currentPage > 1) {
      performSearch(state.currentPage - 1);
      scrollToResults();
    }
  });

  nextPageBtn.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
      performSearch(state.currentPage + 1);
      scrollToResults();
    }
  });

  // Keyboard shortcut (Ctrl+K or /) to focus search
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey && e.key === "k") || (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA")) {
      e.preventDefault();
      if (state.activeTab !== "search") {
        document.querySelector('.mode-tab[data-tab="search"]').click();
      }
      searchInput.focus();
      searchInput.select();
    }
  });
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// Fetch overview statistics
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) return;
    const data = await res.json();
    
    if (data.total_teams) statTeams.textContent = data.total_teams.toLocaleString();
    if (data.total_players) statPlayers.textContent = data.total_players.toLocaleString();
    if (data.total_pages) statPages.textContent = data.total_pages.toLocaleString();
    if (data.total_colleges) statColleges.textContent = data.total_colleges.toLocaleString();

    // Populate top colleges in Analytics tab
    if (data.top_colleges && topCollegesGrid) {
      topCollegesGrid.innerHTML = data.top_colleges.map((c, i) => `
        <div class="college-rank-card" data-college="${escapeHTML(c.name)}">
          <span class="college-rank-num">#${i + 1}</span>
          <div class="college-info">
            <div class="college-name" title="${escapeHTML(c.name)}">${escapeHTML(c.name)}</div>
            <div class="college-count-badge">${c.count.toLocaleString()} participants</div>
          </div>
        </div>
      `).join("");

      topCollegesGrid.querySelectorAll(".college-rank-card").forEach(card => {
        card.addEventListener("click", () => {
          const colName = card.dataset.college;
          document.querySelector('.mode-tab[data-tab="search"]').click();
          searchInput.value = colName;
          state.query = colName;
          state.filterBy = "college";
          filterPills.querySelectorAll(".filter-pill").forEach(p => {
            p.classList.toggle("active", p.dataset.filter === "college");
          });
          clearSearchBtn.classList.remove("hidden");
          performSearch(1);
        });
      });
    }
  } catch (err) {
    console.error("Could not load stats:", err);
  }
}

// Search and fetch results
async function performSearch(page = 1) {
  state.currentPage = page;
  setLoading(true);

  try {
    const params = new URLSearchParams({
      page: state.currentPage,
      limit: state.limit,
      view: state.view
    });

    if (state.activeTab === "multifilter") {
      if (state.mfName) params.append("name", state.mfName);
      if (state.mfTeam) params.append("team", state.mfTeam);
      if (state.mfCollege) params.append("college", state.mfCollege);
      if (state.mfProfile) params.append("profile", state.mfProfile);
    } else {
      params.append("filter_by", state.filterBy);
      if (state.query) params.append("q", state.query);
    }

    const res = await fetch(`/api/search?${params.toString()}`);
    if (!res.ok) throw new Error("Search request failed");
    
    const data = await res.json();
    renderResults(data);
  } catch (err) {
    console.error("Search error:", err);
    resultsGrid.innerHTML = "";
    emptyState.classList.remove("hidden");
    resultsCountText.textContent = "Error fetching results. Please try again.";
  } finally {
    setLoading(false);
  }
}

function setLoading(isLoading) {
  state.isLoading = isLoading;
  loadingSpinner.classList.toggle("hidden", !isLoading);
}

function scrollToResults() {
  document.querySelector(".mode-tabs-container").scrollIntoView({ behavior: "smooth" });
}

// Render Results based on view (Cards or Table)
function renderResults(data) {
  const { results, total_matches, total_pages, page, view } = data;
  state.totalPages = total_pages || 1;
  state.currentPage = page || 1;

  // Update header text
  if (state.activeTab === "multifilter") {
    resultsCountText.textContent = `Found ${total_matches.toLocaleString()} matches with multi-filter`;
  } else if (state.query) {
    resultsCountText.textContent = `Found ${total_matches.toLocaleString()} matches for "${state.query}"`;
  } else {
    resultsCountText.textContent = `Showing all teams (${total_matches.toLocaleString()} total)`;
  }
  
  pageInfoText.textContent = `Page ${state.currentPage} of ${state.totalPages}`;

  if (!results || results.length === 0) {
    resultsGrid.innerHTML = "";
    tableViewContainer.classList.add("hidden");
    resultsGrid.classList.add("hidden");
    emptyState.classList.remove("hidden");
    paginationContainer.classList.add("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  paginationContainer.classList.remove("hidden");

  if (view === "flat") {
    // Render Flat Table View
    resultsGrid.classList.add("hidden");
    tableViewContainer.classList.remove("hidden");

    flatTableBody.innerHTML = results.map(r => `
      <tr>
        <td><code>Page ${r.page}</code></td>
        <td><strong>${escapeHTML(r.name)}</strong></td>
        <td><span class="role-pill ${r.role === 'Leader' ? 'role-leader' : 'role-member'}">${escapeHTML(r.role)}</span></td>
        <td>${escapeHTML(r.organisation || '-')}</td>
        <td>${escapeHTML(r.team_name)}</td>
        <td><span class="badge-evaluated">${escapeHTML(r.evaluated || 'Manual')}</span></td>
        <td>
          ${r.profile_url ? `<a href="https://unstop.com${r.profile_url}" target="_blank" rel="noopener noreferrer" class="unstop-page-link">View Profile ↗</a>` : '-'}
        </td>
      </tr>
    `).join("");
  } else {
    // Render Cards View
    tableViewContainer.classList.add("hidden");
    resultsGrid.classList.remove("hidden");
    resultsGrid.innerHTML = results.map(team => createTeamCardHTML(team)).join("");
  }

  renderPagination();
}

function escapeHTML(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getInitials(name) {
  if (!name) return "?";
  const parts = name.trim().split(" ");
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.substring(0, 2).toUpperCase();
}

function createTeamCardHTML(team) {
  const teamName = escapeHTML(team.team_name || "Unnamed Team");
  const pageNum = team.page;
  const evaluatedStatus = team.evaluated ? escapeHTML(team.evaluated) : "Manual";

  const membersHTML = (team.players || []).map(p => {
    const name = escapeHTML(p.name || "Unknown");
    const org = escapeHTML(p.organisation || "College not listed");
    const isLeader = p.role === "Leader" || p.player_type === 1;
    const roleClass = isLeader ? "role-leader" : "role-member";
    const roleText = isLeader ? "Leader" : "Member";
    const initials = getInitials(p.name);
    const profileUrl = p.profile_url;

    const avatarHTML = p.avatar 
      ? `<img src="${escapeHTML(p.avatar)}" alt="${name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
         <span style="display:none;">${initials}</span>`
      : `<span>${initials}</span>`;

    const linkHTML = profileUrl
      ? `<a href="${escapeHTML(profileUrl)}" target="_blank" rel="noopener noreferrer" class="member-link-btn" title="View ${name}'s Unstop Profile">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
        </a>`
      : "";

    return `
      <div class="member-item">
        <div class="member-avatar">
          ${avatarHTML}
        </div>
        <div class="member-details">
          <div class="member-name-row">
            <span class="member-name" title="${name}">${name}</span>
            <span class="role-pill ${roleClass}">${roleText}</span>
          </div>
          <div class="member-org" title="${org}">${org}</div>
        </div>
        ${linkHTML}
      </div>
    `;
  }).join("");

  return `
    <article class="team-card">
      <div>
        <div class="team-card-header">
          <h2 class="team-name-title">${teamName}</h2>
          <div class="team-badges">
            <span class="badge-page" title="Leaderboard Page">Page ${pageNum}</span>
            <span class="badge-evaluated">${evaluatedStatus}</span>
          </div>
        </div>

        <div class="members-list">
          ${membersHTML}
        </div>
      </div>

      <div class="team-card-footer">
        <span class="members-count-badge">${team.players ? team.players.length : 0} Members</span>
        <a href="${team.unstop_url}" target="_blank" rel="noopener noreferrer" class="unstop-page-link">
          <span>View Page ${pageNum} on Unstop</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </a>
      </div>
    </article>
  `;
}

function renderPagination() {
  const current = state.currentPage;
  const total = state.totalPages;

  prevPageBtn.disabled = current <= 1;
  nextPageBtn.disabled = current >= total;

  let pages = [];
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i);
  } else {
    pages.push(1);
    if (current > 3) pages.push("...");
    
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    
    if (current < total - 2) pages.push("...");
    pages.push(total);
  }

  pageNumbers.innerHTML = pages.map(p => {
    if (p === "...") {
      return `<span class="page-ellipsis">...</span>`;
    }
    const isActive = p === current ? "active" : "";
    return `<button class="page-btn ${isActive}" data-page="${p}">${p}</button>`;
  }).join("");

  pageNumbers.querySelectorAll(".page-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const targetPage = parseInt(btn.dataset.page, 10);
      if (targetPage !== state.currentPage) {
        performSearch(targetPage);
        scrollToResults();
      }
    });
  });
}

// SQL Execution
async function executeSqlFromInput() {
  const query = sqlInput.value.trim();
  if (!query) return;

  state.lastSqlQuery = query;
  runSqlBtn.disabled = true;
  runSqlBtn.innerHTML = "<span>Executing...</span>";

  try {
    const res = await fetch("/api/sql", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query })
    });

    const data = await res.json();

    if (!res.ok) {
      alert(`SQL Error: ${data.detail || data.error || 'Failed to execute query'}`);
      return;
    }

    renderSqlResults(data);
  } catch (err) {
    alert(`SQL Error: ${err.message}`);
  } finally {
    runSqlBtn.disabled = false;
    runSqlBtn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
      <span>Run Query</span>
    `;
  }
}

function renderSqlResults(data) {
  const { headers, rows, total_rows, execution_time_ms, is_truncated } = data;
  sqlResultsContainer.classList.remove("hidden");

  let statusMsg = `Returned ${total_rows} rows in ${execution_time_ms}ms`;
  if (is_truncated) statusMsg += ` (capped at 500 rows for display)`;
  sqlExecutionStatus.textContent = statusMsg;

  // Render Table Head
  sqlTableHead.innerHTML = `<tr>${headers.map(h => `<th>${escapeHTML(h)}</th>`).join("")}</tr>`;

  // Render Table Body
  if (rows.length === 0) {
    sqlTableBody.innerHTML = `<tr><td colspan="${headers.length || 1}" style="text-align:center; padding: 24px;">No records returned.</td></tr>`;
  } else {
    sqlTableBody.innerHTML = rows.map(r => `
      <tr>${r.map(val => `<td>${escapeHTML(val !== null ? val : 'NULL')}</td>`).join("")}</tr>
    `).join("");
  }
}

// Trigger CSV / JSON download
function triggerExport(format) {
  const params = new URLSearchParams({ format });

  if (state.activeTab === "multifilter") {
    if (state.mfName) params.append("name", state.mfName);
    if (state.mfTeam) params.append("team", state.mfTeam);
    if (state.mfCollege) params.append("college", state.mfCollege);
  } else {
    params.append("filter_by", state.filterBy);
    if (state.query) params.append("q", state.query);
  }

  window.location.href = `/api/export?${params.toString()}`;
}
