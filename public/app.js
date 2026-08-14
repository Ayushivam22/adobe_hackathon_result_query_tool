/**
 * Adobe University Hackathon 2026 - Leaderboard Result Finder Frontend
 */

let state = {
  query: "",
  filterBy: "all",
  currentPage: 1,
  totalPages: 1,
  limit: 24,
  isLoading: false,
  debounceTimer: null,
};

// DOM Elements
const searchInput = document.getElementById("searchInput");
const clearSearchBtn = document.getElementById("clearSearchBtn");
const filterPills = document.getElementById("filterPills");
const quickTags = document.getElementById("quickTags");
const resultsGrid = document.getElementById("resultsGrid");
const resultsCountText = document.getElementById("resultsCountText");
const pageInfoText = document.getElementById("pageInfoText");
const loadingSpinner = document.getElementById("loadingSpinner");
const emptyState = document.getElementById("emptyState");
const paginationContainer = document.getElementById("paginationContainer");
const prevPageBtn = document.getElementById("prevPageBtn");
const nextPageBtn = document.getElementById("nextPageBtn");
const pageNumbers = document.getElementById("pageNumbers");

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
  // Search input debouncing
  searchInput.addEventListener("input", (e) => {
    state.query = e.target.value.trim();
    clearSearchBtn.classList.toggle("hidden", state.query.length === 0);

    clearTimeout(state.debounceTimer);
    state.debounceTimer = setTimeout(() => {
      performSearch(1);
    }, 280);
  });

  // Clear button
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

  // Quick suggestions
  quickTags.addEventListener("click", (e) => {
    const btn = e.target.closest(".tag-btn");
    if (!btn) return;

    const queryTag = btn.dataset.query;
    searchInput.value = queryTag;
    state.query = queryTag;
    state.filterBy = "college";
    
    // Update active filter pill
    filterPills.querySelectorAll(".filter-pill").forEach(p => {
      p.classList.toggle("active", p.dataset.filter === "college");
    });

    clearSearchBtn.classList.remove("hidden");
    performSearch(1);
  });

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
    if ((e.ctrlKey && e.key === "k") || (e.key === "/" && document.activeElement !== searchInput)) {
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
    }
  });
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
      filter_by: state.filterBy,
    });

    if (state.query) {
      params.append("q", state.query);
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
  document.querySelector(".search-section").scrollIntoView({ behavior: "smooth" });
}

// Render team cards & pagination
function renderResults(data) {
  const { results, total_matches, total_pages, page } = data;
  state.totalPages = total_pages || 1;
  state.currentPage = page || 1;

  // Update header counts
  if (state.query) {
    resultsCountText.textContent = `Found ${total_matches.toLocaleString()} teams matching "${state.query}"`;
  } else {
    resultsCountText.textContent = `Showing all teams (${total_matches.toLocaleString()} total)`;
  }
  
  pageInfoText.textContent = `Page ${state.currentPage} of ${state.totalPages}`;

  if (!results || results.length === 0) {
    resultsGrid.innerHTML = "";
    emptyState.classList.remove("hidden");
    paginationContainer.classList.add("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  paginationContainer.classList.remove("hidden");

  // Render cards
  resultsGrid.innerHTML = results.map(team => createTeamCardHTML(team)).join("");

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
