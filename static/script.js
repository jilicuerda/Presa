const params = new URLSearchParams(window.location.search);
const teamID = params.get('team') || 'main'; 
const API_URL = `/api/team-history/${teamID}`;
const TOURNEY_URL = `/api/tournaments/${teamID}`;

const GANKSTER_LINKS = {
    "main": "https://valorant.gankster.gg/teams/117773/presa",
    "academy": "https://valorant.gankster.gg/teams/128676/presa-acy"
};

const STAFF_CONTACTS = {
    "main": [
        { role: "General Manager", name: "Team Manager", discordId: "286632547285467137" }
    ],
    "academy": [
        { role: "General Manager", name: "Team Manager", discordId: "286632547285467137" },
        { role: "Academy Coach", name: "zaka", discordId: "371369284351557662" }
    ]
};

document.addEventListener("DOMContentLoaded", () => {
    const titleEl = document.getElementById('team-title');
    if (titleEl) titleEl.innerText = teamID === 'main' ? 'PRESA MAIN' : 'PRESA ACADEMY';
    const ganksterBtn = document.getElementById('btn-gankster');
    if (ganksterBtn) ganksterBtn.href = GANKSTER_LINKS[teamID] || "#";
});

// --- CONTACT MODAL ---
let isModalOpen = false;
function toggleContactModal() {
    const modal = document.getElementById('contact-modal');
    const content = document.getElementById('contact-modal-content');
    const body = document.getElementById('contact-modal-body');
    
    if (!isModalOpen) {
        const staff = STAFF_CONTACTS[teamID];
        body.innerHTML = "";
        staff.forEach(person => {
            body.innerHTML += `
            <div class="bg-[#0f2747] p-4 rounded-lg border border-white/5 flex justify-between items-center group hover:border-[#0348a2]/50 transition-colors">
                <div>
                    <p class="text-[10px] text-gray-400 uppercase tracking-widest font-bold mb-1">${person.role}</p>
                    <p class="text-white font-bold text-lg leading-none">${person.name}</p>
                </div>
                <a href="https://discord.com/users/${person.discordId}" target="_blank" rel="noopener noreferrer" class="bg-[#5865F2] hover:bg-[#4752C4] text-white px-4 py-2 rounded text-sm font-bold uppercase tracking-wider flex items-center gap-2 transition-colors">
                    <span class="material-symbols-outlined text-base">chat</span> DM
                </a>
            </div>`;
        });
        modal.classList.remove('hidden');
        setTimeout(() => { modal.classList.remove('opacity-0'); content.classList.remove('scale-95'); }, 10);
    } else {
        modal.classList.add('opacity-0'); content.classList.add('scale-95');
        setTimeout(() => { modal.classList.add('hidden'); }, 300);
    }
    isModalOpen = !isModalOpen;
}
window.onclick = function(event) { if (event.target === document.getElementById('contact-modal')) toggleContactModal(); }

// --- FETCH & RENDER DATA ---
async function fetchData() {
    const rosterContainer = document.getElementById('roster-grid');
    if (!rosterContainer) return; 

    // Fetch both endpoints at the same time
    try {
        const [rosterRes, tourneyRes] = await Promise.all([
            fetch(API_URL),
            fetch(TOURNEY_URL)
        ]);

        const rosterData = await rosterRes.json();
        const tourneyData = await tourneyRes.json();
        
        if(rosterData.error) {
            rosterContainer.innerHTML = `<div class='text-red-500 text-center w-full mt-10'>Error: ${rosterData.error}</div>`;
            return;
        }

        renderTournaments(tourneyData);
        renderCards(rosterData.roster);
    } catch (error) {
        console.error("Error fetching data:", error);
        rosterContainer.innerHTML = "<div class='text-red-500 text-center w-full mt-10'>Error loading roster data.</div>";
    }
}

function renderTournaments(tournaments) {
    const cabinet = document.getElementById('trophy-cabinet');
    if (!cabinet || !tournaments || tournaments.length === 0) return;

    let html = `
        <h3 class="text-2xl font-bold uppercase tracking-wider mb-6 flex items-center gap-3 border-b border-accent/30 pb-3 text-accent animate-fade-in-up">
            <span class="material-symbols-outlined">emoji_events</span> Trophy Cabinet
        </h3>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
    `;

    tournaments.forEach((t, index) => {
        const delay = index * 100;
        
        let p = (t.placement || "").toLowerCase();
        let iconColor = "text-gray-400"; 
        if(p.includes("1st") || p.includes("champion")) iconColor = "text-[#FFD700]"; 
        else if(p.includes("2nd") || p.includes("runner")) iconColor = "text-[#C0C0C0]"; 
        else if(p.includes("3rd")) iconColor = "text-[#CD7F32]"; 
        else if(p.includes("playoff")) iconColor = "text-primary"; 

        // Check if there is a custom logo
        let iconHtml = `<span class="material-symbols-outlined text-4xl mb-3 ${iconColor}">workspace_premium</span>`;
        if (t.logo_url && t.logo_url.trim() !== "") {
            iconHtml = `<img src="${t.logo_url}" alt="${t.name} Logo" class="h-12 w-12 object-contain mb-3 drop-shadow-[0_0_10px_rgba(255,255,255,0.1)] rounded">`;
        }

        html += `
        <div class="bg-surface-dark border border-[#0348a2]/30 rounded-lg p-5 flex flex-col items-center text-center hover:border-accent transition-colors opacity-0 animate-fade-in-up" style="animation-delay: ${delay}ms;">
            ${iconHtml}
            <h4 class="text-white font-bold text-sm uppercase tracking-wider leading-tight mb-1">${t.name}</h4>
            <span class="text-xs text-gray-400 font-mono uppercase">${t.placement || 'Participant'}</span>
        </div>`;
    });

    html += `</div>`;
    cabinet.innerHTML = html;
    cabinet.classList.remove('hidden');
}
function getRoleIcon(role) {
    const r = role ? role.toLowerCase() : "";
    if (r.includes("duelist")) return "swords";
    if (r.includes("sentinel")) return "security";
    if (r.includes("controller") || r.includes("smoker")) return "smoke_free";
    if (r.includes("initiator")) return "radar";
    if (r.includes("igl")) return "psychology";
    if (r.includes("coach")) return "school";
    return "sports_esports";
}

function generateCardHTML(player, delayIndex) {
    let agentName = player.main_agent || "Jett";
    let cleanName = agentName.replace("/", ""); 
    let safeAgentName = cleanName.charAt(0).toUpperCase() + cleanName.slice(1).toLowerCase();
    const agentImageFile = `${safeAgentName}_Artwork-large.webp`;
    const roleIcon = getRoleIcon(player.role);
    const profileLink = `/player?name=${encodeURIComponent(player.name)}&tag=${encodeURIComponent(player.tag)}&agent=${encodeURIComponent(safeAgentName)}`;
    const delay = delayIndex * 100;

    return `
    <div class="group relative min-h-[400px] w-full transition-all duration-500 ease-in-out bg-surface-dark border border-[#0348a2]/50 hover:border-accent rounded-lg overflow-hidden flex flex-col opacity-0 animate-fade-in-up" style="animation-delay: ${delay}ms;">
        <div class="absolute inset-0 z-0">
            <img alt="${agentName}" class="w-full h-full object-cover opacity-60 group-hover:opacity-40 transition-opacity duration-500 filter grayscale group-hover:grayscale-0" src="/static/assets/agents/${agentImageFile}" onerror="this.src='/static/assets/agents/Jett_Artwork-large.webp'">
            <div class="absolute inset-0 bg-gradient-to-t from-background-dark via-background-dark/50 to-transparent"></div>
        </div>
        <div class="absolute bottom-0 left-0 w-full p-6 z-10 transition-all duration-500 lg:group-hover:opacity-0 lg:group-hover:translate-y-4">
            <div class="flex items-center gap-2 text-accent mb-1">
                <span class="material-symbols-outlined text-lg">${roleIcon}</span>
                <span class="text-xs font-bold tracking-widest uppercase">${player.role}</span>
            </div>
            <h2 class="text-3xl xl:text-4xl font-bold text-white uppercase tracking-tighter break-words">${player.name}</h2>
        </div>
        <div class="relative z-20 flex flex-col h-full opacity-0 lg:group-hover:opacity-100 transition-opacity duration-500 delay-100 pointer-events-none lg:group-hover:pointer-events-auto p-6">
            <div class="flex justify-between items-start mb-auto">
                <div class="flex flex-col">
                    <h2 class="text-3xl xl:text-4xl font-bold text-white uppercase tracking-tighter mb-1 break-words">${player.name}</h2>
                    <span class="text-accent font-mono text-sm tracking-widest uppercase">${player.tag}</span>
                </div>
                <div class="bg-primary size-10 xl:size-12 rounded flex items-center justify-center text-white shrink-0"><span class="material-symbols-outlined text-2xl xl:text-3xl">${roleIcon}</span></div>
            </div>
            <div class="grid grid-cols-2 gap-2 xl:gap-3 mb-4 xl:mb-6 mt-4">
                <div class="bg-background-dark/80 backdrop-blur border border-[#0348a2]/30 p-2 xl:p-3 rounded">
                    <p class="text-gray-400 text-[10px] xl:text-xs font-medium uppercase mb-1">Current Rank</p>
                    <p class="text-white text-base xl:text-xl font-bold font-mono truncate">${player.rank}</p>
                </div>
                <div class="bg-background-dark/80 backdrop-blur border border-[#0348a2]/30 p-2 xl:p-3 rounded">
                    <p class="text-gray-400 text-[10px] xl:text-xs font-medium uppercase mb-1">Main Agent</p>
                    <p class="text-accent text-base xl:text-xl font-bold font-mono truncate">${safeAgentName}</p>
                </div>
            </div>
            <a href="${profileLink}" class="w-full mt-auto bg-white hover:bg-gray-200 text-black font-bold py-3 px-4 rounded flex items-center justify-center gap-2 uppercase text-sm tracking-wide transition-colors">
                <span class="material-symbols-outlined">bar_chart</span> View Stats
            </a>
        </div>
    </div>`;
}

function renderCards(players) {
    const container = document.getElementById('roster-grid');
    container.innerHTML = ""; 

    const activeRoster = players.filter(p => p.type === 'player' || !p.type);
    const substitutes = players.filter(p => p.type === 'sub');
    const coaches = players.filter(p => p.type === 'coach');
    let delayCounter = 0; 

    if (activeRoster.length > 0) {
        let section = `<div class="w-full"><h3 class="text-2xl font-bold uppercase tracking-wider mb-6 flex items-center gap-3 border-b border-[#0348a2]/30 pb-3 opacity-0 animate-fade-in-up" style="animation-delay: ${delayCounter * 100}ms;"><span class="material-symbols-outlined text-primary">group</span> Starting Lineup</h3><div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">`;
        delayCounter++; 
        activeRoster.forEach(p => { section += generateCardHTML(p, delayCounter); delayCounter++; });
        section += `</div></div>`;
        container.innerHTML += section;
    }

    if (substitutes.length > 0) {
        let section = `<div class="w-full mt-8"><h3 class="text-2xl font-bold uppercase tracking-wider mb-6 flex items-center gap-3 border-b border-[#0348a2]/30 pb-3 opacity-0 animate-fade-in-up" style="animation-delay: ${delayCounter * 100}ms;"><span class="material-symbols-outlined text-accent">swap_horiz</span> Substitutes</h3><div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">`;
        delayCounter++; 
        substitutes.forEach(p => { section += generateCardHTML(p, delayCounter); delayCounter++; });
        section += `</div></div>`;
        container.innerHTML += section;
    }

    if (coaches.length > 0) {
        let section = `<div class="w-full mt-8"><h3 class="text-2xl font-bold uppercase tracking-wider mb-6 flex items-center gap-3 border-b border-[#0348a2]/30 pb-3 opacity-0 animate-fade-in-up" style="animation-delay: ${delayCounter * 100}ms;"><span class="material-symbols-outlined text-white">school</span> Coaching Staff</h3><div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">`;
        delayCounter++;
        coaches.forEach(p => { section += generateCardHTML(p, delayCounter); delayCounter++; });
        section += `</div></div>`;
        container.innerHTML += section;
    }
}

if(document.getElementById('roster-grid')) {
    fetchData();
}
