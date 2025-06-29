document.addEventListener('DOMContentLoaded', () => {
    // --- Get all our HTML elements ---
    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const submitButton = document.getElementById('submit-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    const responseContainer = document.getElementById('response-container'); // We'll use this as our chat log
    
    const audioUploadInput = document.getElementById('audio-upload-input');
    const transcribeButton = document.getElementById('transcribe-button');
    const transcribeLoadingIndicator = document.getElementById('transcribe-loading-indicator');
// In script.js, at the top of the 'DOMContentLoaded' event listener

// --- VIEW SWITCHING LOGIC ---
const navLinks = document.querySelectorAll('.nav-link');
const views = document.querySelectorAll('.view');

navLinks.forEach(link => {
    link.addEventListener('click', (event) => {
        event.preventDefault();

        // Manage active state for links
        navLinks.forEach(l => l.classList.remove('active'));
        link.classList.add('active');

        // Manage active state for views
        const targetViewId = link.getAttribute('data-view');
        views.forEach(view => {
            if (view.id === targetViewId) {
                view.classList.add('active-view');
            } else {
                view.classList.remove('active-view');
            }
        });
    });
});
    // --- THE NEW MEMORY STORE ---
    // This array will hold our conversation history.
    let chatHistory = [];

    // --- Function to display messages in the chat log ---
    function addMessageToLog(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-message', `${sender}-message`);
        
        const senderElement = document.createElement('strong');
        senderElement.textContent = sender === 'human' ? 'You' : 'Agent';
        
        const messageText = document.createElement('p');
        messageText.textContent = message;

        messageElement.appendChild(senderElement);
        messageElement.appendChild(messageText);
        responseContainer.appendChild(messageElement);
        
        // Scroll to the bottom
        responseContainer.scrollTop = responseContainer.scrollHeight;
    }


    // --- MAIN AGENT QUERY FORM ---
    queryForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const userQuery = queryInput.value.trim();
        if (!userQuery) return;

        // Add user's message to UI and history
        addMessageToLog('human', userQuery);
        chatHistory.push({ role: 'human', content: userQuery });

        // --- UI Loading State ---
        submitButton.disabled = true;
        loadingIndicator.style.display = 'block';
        queryInput.value = ''; // Clear input after sending

        try {
            // --- Make the API call, now sending the history ---
            const response = await fetch('/agent-query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // Send the query AND the history
                body: JSON.stringify({ 
                    text: userQuery,
                    history: chatHistory.slice(0, -1) // Send history *before* the current message
                }),
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            
            // Add agent's response to UI and history
            addMessageToLog('agent', data.answer);
            chatHistory.push({ role: 'ai', content: data.answer });

        } catch (error) {
            console.error('Error fetching response:', error);
            addMessageToLog('agent', 'An error occurred. Please check the console.');
        } finally {
            // --- Reset UI ---
            submitButton.disabled = false;
            loadingIndicator.style.display = 'none';
        }
    });


    // --- AUDIO TRANSCRIPTION LISTENER (unchanged logic) ---
    transcribeButton.addEventListener('click', async () => {
        const file = audioUploadInput.files[0];
        if (!file) {
            alert('Please select an audio file first.');
            return;
        }
        transcribeButton.disabled = true;
        transcribeLoadingIndicator.style.display = 'block';
        const formData = new FormData();
        formData.append('audio_file', file);
        try {
            const response = await fetch('/transcribe-audio', {
                method: 'POST',
                body: formData,
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Transcription failed.');
            }
            const data = await response.json();
            const fullAgentInput = `Based on the following interview transcript, please create a new case file:\n\n---\n\n${data.text}`;
            queryInput.value = fullAgentInput;
            queryInput.focus();
            queryInput.style.height = '200px';
        } catch (error) {
            console.error('Error during transcription:', error);
            alert(`Transcription Error: ${error.message}`);
        } finally {
            transcribeButton.disabled = false;
            transcribeLoadingIndicator.style.display = 'none';
        }
    });
// In script.js, inside the 'DOMContentLoaded' event listener

// --- CASE DASHBOARD LOGIC ---

// 1. Define options for List.js
const dashboardOptions = {
    valueNames: [
        'case_id',
        'status',
        'caller_phone_number',
        // Format the date before displaying
        { name: 'created_at', attr: 'data-timestamp' } 
    ],
    // This tells List.js how to create each new row from the data
    item: `<tr>
               <td class="case_id"></td>
               <td class="status"></td>
               <td class="caller_phone_number"></td>
               <td class="created_at" data-timestamp=""></td>
               <td><button class="summarize-btn">Summarize</button></td>
           </tr>`
};

// 2. Initialize List.js
const caseList = new List('cases-dashboard', dashboardOptions);

// 3. Function to fetch data and populate the table
async function loadCases() {
    try {
        const response = await fetch('/api/cases');
        if (!response.ok) throw new Error('Failed to fetch cases');
        
        let cases = await response.json();
        
        // Format the data before adding it to the list
        cases = cases.map(caseItem => {
            return {
                ...caseItem,
                // Format the date for display, but keep timestamp for sorting
                created_at: new Date(caseItem.created_at).toLocaleString()
            };
        });

        if (cases.length > 0) {
            caseList.clear(); // Clear the "Loading..." row
            caseList.add(cases); // Add all the new data
        } else {
            caseList.clear();
            // Handle case where there are no records
            const tbody = document.querySelector('#cases-dashboard .list');
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No cases found in the database.</td></tr>';
        }

    } catch (error) {
        console.error('Error loading cases:', error);
    }
}

// 4. Logic for the "Summarize" button
// We use event delegation to handle clicks on buttons that are added dynamically
document.querySelector('#cases-dashboard .list').addEventListener('click', (event) => {
    if (event.target.classList.contains('summarize-btn')) {
        // Find the parent row of the button that was clicked
        const row = event.target.closest('tr');
        // Get the case ID from that row
        const caseId = row.querySelector('.case_id').textContent;
        
        // Find the full case data from our list
        const caseItem = caseList.get('case_id', caseId)[0].values();
        
        // Construct a detailed prompt for the agent
        const summaryPrompt = `Please provide a concise summary of the following case, including the initial intake and any follow-up notes.
        
        Case ID: ${caseItem.case_id}
        Status: ${caseItem.status}
        Initial Transcript:
        ---
        ${caseItem.full_transcript}
        ---
        
        Follow-up Notes:
        ---
        ${JSON.stringify(caseItem.follow_up_notes, null, 2)}
        ---
        
        Provide your summary now:`;
        
        // Put the prompt in the main chat box and add it to the chat UI
        addMessageToLog('human', summaryPrompt);
        chatHistory.push({ role: 'human', content: summaryPrompt });

        // Set the value for submission
        queryInput.value = summaryPrompt;
        queryForm.requestSubmit(); // Automatically submit the form

        // Scroll to the top to see the chat
        window.scrollTo(0, 0);
    }
});

// 5. Load the cases when the page loads
loadCases();
// --- END OF CASE DASHBOARD LOGIC ---

});