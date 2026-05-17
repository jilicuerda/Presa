const params = new URLSearchParams(window.location.search);
const teamID = params.get('team') || 'main'; 
const API_URL = `/api/team-history/${teamID}`;

// --- TEAM LINKS DATABASE ---
const GANKSTER_LINKS = {
    "main": "https://valorant.gankster.gg/teams/117773/presa",
    "academy": "https://valorant.gankster.gg/teams/128676/presa-acy"
};

// --- CONTACT DATABASE ---
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
    if (titleEl) {
        titleEl.innerText = teamID === 'main' ? 'PRESA MAIN' : 'PRESA ACADEMY';
    }

    // Set dynamic Gankster link
    const ganksterBtn = document.getElementById('btn-gankster');
    if (ganksterBtn) {
        ganksterBtn.href = GANKSTER_LINKS[teamID] || "#";
    }
});

// --- CONTACT MODAL LOGIC ---
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
                    <span class="material-symbols-outlined text-base">chat</span>
                    DM
                </a>
            </div>
            `;
        });

        modal.classList.remove('hidden');
        setTimeout(() => {
            modal.classList.remove('opacity-0');
            content.classList.remove('scale-95');
        }, 10);
    } else {
        modal.classList.add('opacity-0');
        content.classList.add('scale-95');
        setTimeout(() => {
            modal.classList.add('hidden');
        }, 300);
    }
    isModalOpen = !isModalOpen;
}

window.onclick = function(event) {
    const modal = document.getElementById('contact-modal');
    if (event.target === modal) {
        toggleContactModal();
    }
}

// --- EXISTING ROSTER LOGIC ---
async function fetchTeamData() {
    const container = document.getElementById('roster-grid');
    if (!container) return; 

    try {
        const response = await fetch(API_URL);
        const data = await response.json();
        
        if(data.error) {
            container.innerHTML = `<div class='text-red-500 text-center w-full mt-10'>Error: ${data.error}</div>`;
            return;
        }

        renderCards(data.roster);
    } catch (error) {
        console.error("Error fetching data:", error);
        container.innerHTML = "<div class='text-red-500 text-center w-full mt-10'>Error loading roster data.</div>";
    }
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

function generateCardHTML(player) {
    let agentName = player.main_agent || "Jett";
    let cleanName = agentName.replace("/", ""); 
    let safeAgentName = cleanName.charAt(0).toUpperCase() + cleanName.slice(1).toLowerCase();

    const agentImageFile = `${safeAgentName}_Artwork-large.webp`;
    const roleIcon = getRoleIcon(player.role);
    const profileLink = `/player?name=${encodeURIComponent(player.name)}&tag=${encodeURIComponent(player.tag)}&agent=${encodeURIComponent(safeAgentName)}`;

    return `
    <div class="group relative min-h-[400px] w-full transition-all duration-500 ease-in-out bg-surface-dark border border-[#0348a2]/50 hover:border-accent rounded-lg overflow-hidden flex flex-col">
        <div class="absolute inset-0 z-0">
            <img alt="${agentName}" 
                 class="w-full h-full object-cover opacity-60 group-hover:opacity-40 transition-opacity duration-500 filter grayscale group-hover:grayscale-0" 
                 src="/static/assets/agents/${agentImageFile}"
                 onerror="this.src='/static/assets/agents/Jett_Artwork-large.webp'">
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
                <div class="bg-primary size-10 xl:size-12 rounded flex items-center justify-center text-white shrink-0">
                    <span class="material-symbols-outlined text-2xl xl:text-3xl">${roleIcon}</span>
                </div>
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
                <span class="material-symbols-outlined">bar_chart</span>
                View Stats
            </a>
        </div>
    </div>
    `;
}

function renderCards(players) {
    const container = document.getElementById('roster-grid');
    container.innerHTML = ""; 

    const activeRoster = players.filter(p => p.type === 'player' || !p.type);
    const substitutes = players.filter(p => p.type === 'sub');
    const coaches = players.filter(p => p.type === 'coach');

    if (activeRoster.length > 0) {
        let section = `<div class="w-full">
            <h3 class="text-2xl font-bold uppercase tracking-wider mb-6 flex items-center gap-3 border-b border-[#0348a2]/30 pb-3">
                <span class="material-symbols-outlined text-primary">group</span> Starting Lineup
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">`;
        activeRoster.forEach(p => { section += generateCardHTML(p); });
        section += `</div></div>`;
        container.innerHTML += section;
    }

    if (substitutes.length > 0) {
        let section = `<div class="w-full mt-8">
            <h3 class="text-2xl font-bold uppercase tracking-wider mb-6 flex items-center gap-3 border-b border-[#0348a2]/30 pb-3">
                <span class="material-symbols-outlined text-accent">swap_horiz</span> Substitutes
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">`;
        substitutes.forEach(p => { section += generateCardHTML(p); });
        section += `</div></div>`;
        container.innerHTML += section;
    }

    if (coaches.length > 0) {
        let section = `<div class="w-full mt-8">
            <h3 class="text-2xl font-bold uppercase tracking-wider mb-6 flex items-center gap-3 border-b border-[#0348a2]/30 pb-3">
                <span class="material-symbols-outlined text-white">school</span> Coaching Staff
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">`;
        coaches.forEach(p => { section += generateCardHTML(p); });
        section += `</div></div>`;
        container.innerHTML += section;
    }
}

if(document.getElementById('roster-grid')) {
    fetchTeamData();
}
