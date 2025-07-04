// frontend/js/cases.js

document.addEventListener('DOMContentLoaded', async () => {
    feather.replace(); // Ensure icons are rendered

    let caseList; // To hold the List.js instance
    let allCasesData = []; // Store the full fetched data for filtering

    async function fetchCases() {
        try {
            const response = await fetch('/api/cases');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            // Process data for display and List.js
            return data.map(c => ({
                ...c, // Spread all properties from the backend Case schema
                last_updated_display: new Date(c.last_updated).toLocaleString(), // Format date for display
                created_at_display: new Date(c.created_at).toLocaleString(), // Format date for display
                // Note: structured_intake and follow_up_notes are already objects/arrays if parsed correctly by FastAPI
            }));
        } catch (error) {
            console.error("Error fetching cases:", error);
            document.getElementById('cases-list-body').innerHTML = `<tr><td colspan="6" class="text-secondary" style="text-align: center;">Error loading cases.</td></tr>`;
            return [];
        }
    }

    allCasesData = await fetchCases(); // Fetch data once

    var options = {
        valueNames: [
            'case_name',
            'client_name',
            'type',
            { name: 'status', attr: 'data-status' }, // Use data-status for filtering if needed
            'assigned_to',
            'last_updated_display'
        ],
        item: `<tr>
                    <td class="case_name"></td>
                    <td class="client_name"></td>
                    <td class="type"></td>
                    <td><span class="status-badge status"></span></td>
                    <td class="assigned_to"></td>
                    <td class="last_updated_display"></td>
               </tr>`
    };

    caseList = new List('cases-section', options, allCasesData); // Target the cases-section ID

    // Apply status-badge classes after List.js renders
    caseList.on('updated', function (list) {
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
    caseList.update();

    // Search functionality for List.js
    document.getElementById('search-cases').addEventListener('keyup', function() {
        caseList.search(this.value);
    });

    // Handle filter buttons
    document.getElementById('case-filters').addEventListener('click', function(event) {
        const button = event.target.closest('button');
        if (button && button.dataset.filter) {
            document.querySelectorAll('#case-filters .button').forEach(btn => btn.classList.remove('active-tab'));
            button.classList.add('active-tab');

            const filterType = button.dataset.filter;
            caseList.filter(function(item) {
                const values = item.values();
                if (filterType === 'all') {
                    return true;
                } else if (filterType === 'my') {
                    // Assuming 'Alex' is the current user for 'My Cases'
                    // In a real app, this would come from user session/authentication
                    return values.assigned_to === 'Alex';
                } else if (filterType === 'unassigned') {
                    return !values.assigned_to || values.assigned_to === 'Unassigned';
                }
                return false;
            });
            caseList.update(); // Re-apply sorting/filtering
        }
    });

    // Case Details Display Logic
    document.getElementById('cases-list-body').addEventListener('click', (event) => {
        const row = event.target.closest('tr');
        if (row) {
            // Find the original data item for the clicked row
            // We'll use the unique 'case_id' to find the full data object
            const caseIdInRow = row.querySelector('.case_name').textContent.replace('...', ''); // Assuming first part matches case_id
            const fullCase = allCasesData.find(c => c.case_id.startsWith(caseIdInRow)); // Use startsWith to match partial name

            if (fullCase) {
                document.getElementById('details-case-id').textContent = fullCase.case_id;
                
                const statusBadge = document.getElementById('details-status');
                statusBadge.textContent = fullCase.status;
                // Ensure the class name is consistent with CSS: status-badge-<status-value-lowercase-hyphenated>
                statusBadge.className = `status-badge status-badge-${fullCase.status.toLowerCase().replace(' ', '-')}`;
                
                document.getElementById('details-assigned-to').textContent = fullCase.assigned_to || 'Unassigned';
                document.getElementById('details-client-name').textContent = fullCase.client_name;
                document.getElementById('details-phone').textContent = fullCase.caller_phone_number || 'N/A';
                document.getElementById('details-case-type').textContent = fullCase.type;
                document.getElementById('details-created').textContent = fullCase.created_at_display;
                document.getElementById('details-last-updated').textContent = fullCase.last_updated_display;
                document.getElementById('details-vapi-call-id').textContent = fullCase.vapi_call_id || 'N/A';

                document.getElementById('details-summary').textContent = fullCase.call_summary || 'No summary available.';
                document.getElementById('details-structured-intake').textContent = JSON.stringify(fullCase.structured_intake, null, 2);
                document.getElementById('details-full-transcript').textContent = fullCase.full_transcript || 'No full transcript available.';

                const notesList = document.getElementById('details-follow-up-notes');
                notesList.innerHTML = ''; // Clear previous notes
                if (fullCase.follow_up_notes && fullCase.follow_up_notes.length > 0) {
                    fullCase.follow_up_notes.forEach(note => {
                        const li = document.createElement('li');
                        li.className = 'py-2 border-b border-border-color'; // Add some styling
                        const noteTimestamp = new Date(note.timestamp).toLocaleString();
                        li.innerHTML = `<strong>${noteTimestamp}:</strong> ${note.summary}`;
                        notesList.appendChild(li);
                    });
                } else {
                    notesList.innerHTML = `<li class="text-secondary">No follow-up notes.</li>`;
                }

                document.getElementById('case-details-display').style.display = 'block';
                feather.replace(); // Re-render icons in details section
            }
        }
    });

    // Initial load and display
    caseList.update();
});