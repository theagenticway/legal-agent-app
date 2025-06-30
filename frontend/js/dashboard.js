// frontend/js/dashboard.js

document.addEventListener('DOMContentLoaded', () => {
    // Dashboard Table Functionality (List.js)
    const caseListOptions = {
        valueNames: ['case_id', 'status', 'caller_phone_number', 'created_at'],
        item: '<tr class="case-item"><td class="case_id"></td><td class="status"></td><td class="caller_phone_number"></td><td class="created_at"></td><td><button class="summarize-btn button secondary-button" style="margin-right: 8px;">Summarize</button><button class="view-details-btn button secondary-button">View Details</button></td></tr>'
    };

    let caseList = null; // Will hold the List.js instance
    let allCasesData = []; // Store full case data for details view

    const caseDetailsDisplay = document.getElementById('case-details-display');
    const detailsCaseId = document.getElementById('details-case-id');
    const detailsStatus = document.getElementById('details-status');
    const detailsPhone = document.getElementById('details-phone');
    const detailsCreated = document.getElementById('details-created');
    const detailsSummary = document.getElementById('details-summary');
    const detailsStructuredIntake = document.getElementById('details-structured-intake');
    const detailsFullTranscript = document.getElementById('details-full-transcript');
    const detailsFollowUpNotes = document.getElementById('details-follow-up-notes');

    async function fetchCases() {
        try {
            const response = await fetch('/api/cases');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            allCasesData = await response.json(); // Store full data
            console.log('Fetched cases:', allCasesData);

            // Format dates for display in the table
            const formattedCases = allCasesData.map(c => ({
                ...c,
                created_at: new Date(c.created_at).toLocaleDateString('en-US', {
                    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                })
            }));

            if (!caseList) {
                caseList = new List('cases-dashboard', caseListOptions, formattedCases);
                console.log('List.js initialized with cases.');
            } else {
                caseList.clear();
                caseList.add(formattedCases);
                console.log('List.js updated with new cases.');
            }

            // Add event listeners to summarize and view buttons
            document.querySelectorAll('.summarize-btn').forEach(button => {
                button.onclick = async (event) => {
                    const row = event.target.closest('tr');
                    const caseId = row.querySelector('.case_id').textContent;
                    const originalCase = allCasesData.find(c => c.case_id === caseId);

                    if (originalCase && originalCase.full_transcript) {
                        const transcriptToSummarize = originalCase.full_transcript;
                        const phone = originalCase.caller_phone_number;
                        const summaryQuery = `Please summarize the call transcript for case ID ${caseId} from phone number ${phone}:\n\n${transcriptToSummarize}`;
                        // Redirect to agent chat and send the query
                        sessionStorage.setItem('agentChatInitialQuery', summaryQuery);
                        window.location.href = 'agent.html';

                    } else {
                        alert('Full transcript not available for this case.');
                    }
                };
            });

            document.querySelectorAll('.view-details-btn').forEach(button => {
                button.onclick = (event) => {
                    const row = event.target.closest('tr');
                    const caseId = row.querySelector('.case_id').textContent;
                    const caseToDisplay = allCasesData.find(c => c.case_id === caseId);
                    displayCaseDetails(caseToDisplay);
                };
            });

        } catch (error) {
            console.error('Error fetching cases:', error);
            const dashboardTableBody = document.querySelector('#cases-dashboard .list');
            if (dashboardTableBody) {
                dashboardTableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-secondary);">Error loading cases: ${error.message}</td></tr>`;
            }
        }
    }

    function displayCaseDetails(caseData) {
        if (!caseData) {
            caseDetailsDisplay.style.display = 'none';
            return;
        }

        detailsCaseId.textContent = caseData.case_id || 'N/A';
        detailsStatus.textContent = caseData.status || 'N/A';
        detailsPhone.textContent = caseData.caller_phone_number || 'N/A';
        detailsCreated.textContent = new Date(caseData.created_at).toLocaleString() || 'N/A';
        detailsSummary.textContent = caseData.call_summary || 'N/A';

        try {
            detailsStructuredIntake.textContent = JSON.stringify(caseData.structured_intake, null, 2) || 'No structured intake data.';
        } catch (e) {
            detailsStructuredIntake.textContent = caseData.structured_intake || 'Malformed structured intake data.';
        }

        detailsFullTranscript.textContent = caseData.full_transcript || 'No full transcript available.';

        detailsFollowUpNotes.innerHTML = '';
        if (caseData.follow_up_notes && caseData.follow_up_notes.length > 0) {
            caseData.follow_up_notes.forEach(note => {
                const li = document.createElement('li');
                li.style.marginBottom = '10px';
                li.innerHTML = `<strong>${new Date(note.timestamp).toLocaleString()}:</strong> ${note.summary}<br><small>${note.transcript.substring(0, 150)}...</small>`;
                detailsFollowUpNotes.appendChild(li);
            });
        } else {
            detailsFollowUpNotes.innerHTML = '<li>No follow-up notes.</li>';
        }

        caseDetailsDisplay.style.display = 'block';
        caseDetailsDisplay.scrollIntoView({ behavior: 'smooth' }); // Scroll to details
    }


    fetchCases();
    setInterval(fetchCases, 30000);
});