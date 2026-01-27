// 1. UPDATED API URL
// We use a relative path now. This works automatically on localhost AND Render.
const API_URL = "/api/team-history";

async function fetchTeamData() {
    try {
        const response = await fetch(API_URL);
        const data = await response.json();
        
        // 1. Get the Roster and Matches from backend
        const roster = data.roster;
        const matches = data.matches;

        // 2. Calculate stats for each player
        const processedRoster = roster.map(player => {
            const playerStats = calculatePlayerStats(player, matches);
            return { ...player, ...playerStats };
        });

        // 3. Render the cards
        renderCards(processedRoster);

    } catch (error) {
        console.error("Error fetching data:", error);
        document.getElementById('roster-container').innerHTML = "<p>Error loading data.</p>";
    }
}

function calculatePlayerStats(player, matches) {
    let agentCounts = {};
    let currentRank = "Unranked";
    
    // Loop through every match to find this player's stats
    matches.forEach(match => {
        // Find the player in this specific match
        const pData = match.players.all_players.find(
            p => p.name.toLowerCase() === player.name.toLowerCase() && 
                 p.tag === player.tag
        );

        if (pData) {
            // Count the Agent
            const agentName = pData.character;
            agentCounts[agentName] = (agentCounts[agentName] || 0) + 1;

            // Grab their most recent Rank (Tier)
            currentRank = pData.currenttier_patched; 
        }
    });

    // Find the agent with the highest count
    let mostPlayedAgent = "Unknown";
    let maxCount = 0;
    
    for (const [agent, count] of Object.entries(agentCounts)) {
        if (count > maxCount) {
            maxCount = count;
            mostPlayedAgent = agent;
        }
    }

    // Fallbacks if they haven't played any games recently
    if (mostPlayedAgent === "Unknown") {
        if (player.role === "Duelist") mostPlayedAgent = "Jett";
        else if (player.role === "Initiator") mostPlayedAgent = "Sova";
        else if (player.role === "Smoker") mostPlayedAgent = "Omen";
        else if (player.role === "Sentinel") mostPlayedAgent = "Killjoy";
        else mostPlayedAgent = "Jett"; // Default fallback
    }

    return { mostPlayedAgent, currentRank };
}

function renderCards(players) {
    const container = document.getElementById('roster-container');
    container.innerHTML = ""; // Clear loading text

    players.forEach(player => {
        // 2. UPDATED IMAGE PATH
        // We now point to the /static/ folder where Flask serves files
        const agentImageFile = `${player.mostPlayedAgent}_Artwork-large.webp`;
        
        const cardHTML = `
            <div class="card">
                <div class="card-image">
                    <img src="/static/assets/agents/${agentImageFile}" alt="${player.mostPlayedAgent}">
                </div>
                <div class="card-info">
                    <h2>${player.name}</h2>
                    <span class="role">${player.role}</span>
                    <div class="stats">
                        <span class="rank">${player.currentRank || "Unranked"}</span>
                        <span class="agent-name">Main: ${player.mostPlayedAgent}</span>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML += cardHTML;
    });
}

// Run the function when page loads
fetchTeamData();