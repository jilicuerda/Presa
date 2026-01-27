const API_URL = "/api/team-history";

async function fetchTeamData() {
    const container = document.getElementById('roster-grid');
    
    try {
        const response = await fetch(API_URL);
        const data = await response.json();
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
    return "sports_esports";
}

function renderCards(players) {
    const container = document.getElementById('roster-grid');
    container.innerHTML = ""; 

    players.forEach(player => {
        // Use the Fixed Agent from Python, or fallback to Jett
        let agentName = player.main_agent || "Jett";
        
        // Ensure proper capitalization (e.g. "Kayo" -> "Kayo")
        let cleanName = agentName.replace("/", ""); 
        let safeAgentName = cleanName.charAt(0).toUpperCase() + cleanName.slice(1).toLowerCase();

        const agentImageFile = `${safeAgentName}_Artwork-large.webp`;
        const roleIcon = getRoleIcon(player.role);

        // GENERATE LINK TO PLAYER DETAIL PAGE
        // We encode the URI components to handle spaces and hash tags safely
        const profileLink = `/player?name=${encodeURIComponent(player.name)}&tag=${encodeURIComponent(player.tag)}&agent=${encodeURIComponent(safeAgentName)}`;

        const cardHTML = `
        <div class="group relative flex-1 min-h-[400px] lg:min-h-0 lg:hover:flex-[2.5] transition-all duration-500 ease-in-out bg-surface-dark border border-[#482325] hover:border-primary rounded-lg overflow-hidden flex flex-col">
            <div class="absolute inset-0 z-0">
                <img alt="${agentName}" 
                     class="w-full h-full object-cover opacity-60 group-hover:opacity-40 transition-opacity duration-500 filter grayscale group-hover:grayscale-0" 
                     src="/static/assets/agents/${agentImageFile}"
                     onerror="this.src='/static/assets/agents/Jett_Artwork-large.webp'">
                <div class="absolute inset-0 bg-gradient-to-t from-background-dark via-background-dark/50 to-transparent"></div>
            </div>

            <div class="absolute bottom-0 left-0 w-full p-6 z-10 transition-all duration-500 lg:group-hover:opacity-0 lg:group-hover:translate-y-4">
                <div class="flex items-center gap-2 text-primary mb-1">
                    <span class="material-symbols-outlined text-lg">${roleIcon}</span>
                    <span class="text-xs font-bold tracking-widest uppercase">${player.role}</span>
                </div>
                <h2 class="text-4xl font-bold text-white uppercase tracking-tighter">${player.name}</h2>
            </div>

            <div class="relative z-20 flex flex-col h-full opacity-0 lg:group-hover:opacity-100 transition-opacity duration-500 delay-100 pointer-events-none lg:group-hover:pointer-events-auto p-6 lg:p-8">
                <div class="flex justify-between items-start mb-auto">
                    <div class="flex flex-col">
                        <h2 class="text-5xl font-bold text-white uppercase tracking-tighter mb-1">${player.name}</h2>
                        <span class="text-primary font-mono text-sm tracking-widest uppercase">${player.tag}</span>
                    </div>
                    <div class="bg-primary size-12 rounded flex items-center justify-center text-white">
                        <span class="material-symbols-outlined text-3xl">${roleIcon}</span>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-3 mb-6">
                    <div class="bg-background-dark/80 backdrop-blur border border-[#482325] p-3 rounded">
                        <p class="text-gray-400 text-xs font-medium uppercase mb-1">Current Rank</p>
                        <p class="text-white text-xl font-bold font-mono">${player.rank}</p>
                    </div>
                    <div class="bg-background-dark/80 backdrop-blur border border-[#482325] p-3 rounded">
                        <p class="text-gray-400 text-xs font-medium uppercase mb-1">Main Agent</p>
                        <p class="text-white text-xl font-bold font-mono text-primary">${safeAgentName}</p>
                    </div>
                </div>
                
                 <div class="bg-background-dark/80 backdrop-blur border border-[#482325] p-4 rounded mb-4">
                    <div class="flex items-center gap-3 text-sm text-gray-300">
                        <span class="material-symbols-outlined text-primary" style="font-size: 20px;">flag</span>
                        <span>Region: <strong class="text-white uppercase">EU</strong></span>
                    </div>
                </div>

                <a href="${profileLink}" class="w-full mt-auto bg-white hover:bg-gray-200 text-black font-bold py-3 px-4 rounded flex items-center justify-center gap-2 uppercase text-sm tracking-wide transition-colors">
                    <span class="material-symbols-outlined">bar_chart</span>
                    View Details
                </a>
            </div>
        </div>
        `;
        container.innerHTML += cardHTML;
    });
}
fetchTeamData();
