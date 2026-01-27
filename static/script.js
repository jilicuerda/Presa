const API_URL = "/api/team-history";

async function fetchTeamData() {
    const container = document.getElementById('roster-container');
    container.innerHTML = "<p class='loading-text'>Loading Team Data...</p>";

    try {
        const response = await fetch(API_URL);
        const data = await response.json();
        
        // The Python backend now sends "roster" with the stats already calculated!
        renderCards(data.roster);

    } catch (error) {
        console.error("Error fetching data:", error);
        container.innerHTML = "<p>Error loading data. Check console for details.</p>";
    }
}

function renderCards(players) {
    const container = document.getElementById('roster-container');
    container.innerHTML = ""; // Clear loading text

    players.forEach(player => {
        // Use the calculated stats from Python
        // Ensure we capitalize the first letter for the file name (e.g. "jett" -> "Jett")
        let agentName = player.main_agent || "Unknown";
        
        // Fix capitalization for image file (Jett_Artwork...)
        if (agentName !== "Unknown") {
            agentName = agentName.charAt(0).toUpperCase() + agentName.slice(1);
        } else {
            // Fallback if API failed
            agentName = "Jett"; 
        }

        const agentImageFile = `${agentName}_Artwork-large.webp`;

        const cardHTML = `
            <div class="card">
                <div class="card-image">
                    <img src="/static/assets/agents/${agentImageFile}" 
                         alt="${agentName}"
                         onerror="this.onerror=null; this.src='/static/assets/agents/Jett_Artwork-large.webp';"> 
                </div>
                <div class="card-info">
                    <h2>${player.name}</h2>
                    <span class="role">${player.role}</span>
                    <div class="stats">
                        <span class="rank">${player.rank}</span>
                        <span class="agent-name">Main: ${agentName}</span>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML += cardHTML;
    });
}

fetchTeamData();
