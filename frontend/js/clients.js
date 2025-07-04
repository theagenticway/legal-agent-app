// frontend/js/clients.js

document.addEventListener('DOMContentLoaded', async () => {
    feather.replace(); // Ensure icons are rendered

    let clientList; // To hold the List.js instance

    async function fetchClients() {
        try {
            const response = await fetch('/api/clients');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const clientsData = await response.json();
            return clientsData.map(client => ({
                ...client, // Spread existing properties
                last_activity_at_display: new Date(client.last_activity_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }),
                // Add any other display-specific formatting here
            }));
        } catch (error) {
            console.error("Error fetching clients:", error);
            document.getElementById('clients-list-body').innerHTML = `<tr><td colspan="5" class="text-secondary" style="text-align: center;">Error loading clients.</td></tr>`;
            return [];
        }
    }

    const clientsData = await fetchClients();

    var options = {
        valueNames: ['name', 'contact_email', 'num_cases', 'last_activity_at_display', 'status'],
        item: `<tr>
                    <td class="name"></td>
                    <td class="contact_email"></td>
                    <td class="num_cases"></td>
                    <td class="last_activity_at_display"></td>
                    <td><span class="status-badge status"></span></td>
               </tr>`
    };

    clientList = new List('clients-dashboard', options, clientsData);

    // Apply status-badge classes after List.js renders
    clientList.on('updated', function (list) {
        list.items.forEach(item => {
            const statusElement = item.elm.querySelector('.status-badge');
            if (statusElement) {
                const statusValue = statusElement.textContent.toLowerCase().replace(' ', '-');
                statusElement.className = `status-badge status-badge-${statusValue}`;
            }
        });
        feather.replace(); // Re-render feather icons in dynamically added content
    });

    // Initial apply for already rendered items
    clientList.update();

    // Search functionality for List.js
    document.getElementById('search-clients').addEventListener('keyup', function() {
        clientList.search(this.value);
    });

    // Handle "New Client" button click (placeholder for now)
    document.querySelector('.button.primary-button').addEventListener('click', () => {
        alert('New Client functionality coming soon!');
        // In a real app, this would open a modal or navigate to a new form
    });
});