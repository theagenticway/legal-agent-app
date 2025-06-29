document.addEventListener('DOMContentLoaded', () => {
    feather.replace(); // Initialize Feather icons

    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const responseContainer = document.getElementById('response-container');
    const loadingIndicator = document.getElementById('loading-indicator');

    // Use querySelector for transcribeButton to be slightly more robust,
    // and explicitly define other elements by ID.
    const transcribeButton = document.querySelector('button#transcribe-button');
    const audioUploadInput = document.getElementById('audio-upload-input');
    const fileUploadZone = document.getElementById('file-upload-zone');

    // --- IMPORTANT: Null check for transcribeButton ---
    // If transcribeButton is null, something is wrong with the HTML ID or element's existence.
    // Log an error and prevent further script execution related to the button.
    if (!transcribeButton) {
        console.error("Error: 'transcribe-button' element not found in the DOM. File upload functionality will be unavailable.");
        // Optionally, disable related UI elements or show a user-friendly message
        if (fileUploadZone) fileUploadZone.style.pointerEvents = 'none';
        if (audioUploadInput) audioUploadInput.disabled = true;
        return; // Exit if a critical element is missing
    }
    // --- End Null check ---

    let chatHistory = []; // Stores the conversation history for the agent

    // --- Chat Functionality ---
    queryInput.addEventListener('input', () => {
        // Auto-resize textarea based on content, up to a max height
        queryInput.style.height = 'auto';
        queryInput.style.height = queryInput.scrollHeight + 'px';
        const maxHeight = 150; // Max height in pixels
        if (queryInput.scrollHeight > maxHeight) {
            queryInput.style.overflowY = 'auto';
            queryInput.style.height = maxHeight + 'px';
        } else {
            queryInput.style.overflowY = 'hidden';
        }
    });

    queryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (!query) return;

        addMessage(query, 'human'); // Display human message
        queryInput.value = ''; // Clear input
        queryInput.style.height = 'auto'; // Reset textarea height
        loadingIndicator.style.display = 'flex'; // Show loading

        try {
            const response = await fetch('/agent-query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: query,
                    history: chatHistory // Send current history
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            addMessage(data.answer, 'agent'); // Display agent response
            chatHistory.push({ role: 'human', content: query });
            chatHistory.push({ role: 'ai', content: data.answer });

        } catch (error) {
            console.error('Error sending query to agent:', error);
            addMessage(`Sorry, I'm having trouble connecting to the agent right now. Please try again later. (Error: ${error.message})`, 'agent');
        } finally {
            loadingIndicator.style.display = 'none'; // Hide loading
            responseContainer.scrollTop = responseContainer.scrollHeight; // Scroll to bottom
        }
    });

    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message');
        messageDiv.classList.add(sender === 'human' ? 'human-message' : 'agent-message');

        const avatar = document.createElement('img');
        avatar.classList.add('avatar');
        avatar.src = sender === 'human' ? 'https://i.pravatar.cc/32?u=legal-human' : 'https://i.pravatar.cc/32?u=legal-agent';
        avatar.alt = sender === 'human' ? 'Human Avatar' : 'Agent Avatar';

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');

        const senderName = document.createElement('div');
        senderName.classList.add('sender-name');
        senderName.textContent = sender === 'human' ? 'You' : 'Agent';

        const messageBubble = document.createElement('div');
        messageBubble.classList.add('message-bubble');
        messageBubble.innerHTML = text.replace(/\n/g, '<br>'); // Support newlines, and basic markdown if needed
        messageBubble.innerHTML = messageBubble.innerHTML.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); // Basic bolding

        contentDiv.appendChild(senderName);
        contentDiv.appendChild(messageBubble);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);

        responseContainer.appendChild(messageDiv);
        responseContainer.scrollTop = responseContainer.scrollHeight; // Auto-scroll to latest message
    }

    // Initial welcome message from the agent
    addMessage("Hello! How can I assist you with your legal queries today? I can look up case information, process new client intakes, or answer questions about our internal documents.", 'agent');


    // --- Dashboard Table Functionality (List.js) ---
    const caseListOptions = {
        valueNames: ['case_id', 'status', 'caller_phone_number', 'created_at'],
        item: '<tr class="case-item"><td class="case_id"></td><td class="status"></td><td class="caller_phone_number"></td><td class="created_at"></td><td><button class="summarize-btn">Summarize Call</button></td></tr>'
    };

    let caseList = null; // Will hold the List.js instance

    async function fetchCases() {
        try {
            const response = await fetch('/api/cases');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const cases = await response.json();
            console.log('Fetched cases:', cases);

            // Format dates for display
            const formattedCases = cases.map(c => ({
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

            // Add event listeners to summarize buttons
            document.querySelectorAll('.summarize-btn').forEach(button => {
                button.onclick = async (event) => {
                    const row = event.target.closest('tr');
                    const caseId = row.querySelector('.case_id').textContent;
                    // Find the original case data to get the full transcript
                    const originalCase = cases.find(c => c.case_id === caseId);

                    if (originalCase && originalCase.full_transcript) {
                        const transcriptToSummarize = originalCase.full_transcript;
                        const phone = originalCase.caller_phone_number;
                        // Ask the agent to summarize the transcript
                        const summaryQuery = `Please summarize the call transcript for case ID ${caseId} from phone number ${phone}:\n\n${transcriptToSummarize}`;
                        addMessage(summaryQuery, 'human'); // Show this request in chat
                        queryInput.value = summaryQuery; // Pre-fill input for consistency
                        queryForm.dispatchEvent(new Event('submit')); // Trigger form submission

                    } else {
                        alert('Full transcript not available for this case.');
                    }
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

    // Fetch cases on load
    fetchCases();
    // Refresh cases every 30 seconds
    setInterval(fetchCases, 30000);


    // --- File Upload & Transcription ---
    // Ensure fileUploadZone and audioUploadInput are not null before adding listeners
    if (fileUploadZone && audioUploadInput) {
        fileUploadZone.addEventListener('click', () => {
            audioUploadInput.click();
        });

        audioUploadInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                console.log('Selected file:', file.name);
                // Optionally, update UI to show file selected
                const bElement = fileUploadZone.querySelector('b');
                const smallTextElement = fileUploadZone.querySelector('.small-text');
                if (bElement) bElement.textContent = file.name;
                if (smallTextElement) smallTextElement.textContent = 'Click to change file';
            }
        });

        // Drag and Drop functionality
        fileUploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            fileUploadZone.classList.add('drag-over');
        });

        fileUploadZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            fileUploadZone.classList.remove('drag-over');
        });

        fileUploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            fileUploadZone.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                audioUploadInput.files = files; // Assign dropped files to input
                const event = new Event('change');
                audioUploadInput.dispatchEvent(event); // Trigger change event
            }
        });
    }


    // transcribeButton is already checked for null at the top
    transcribeButton.addEventListener('click', async () => {
        const file = audioUploadInput.files[0];
        if (!file) {
            alert('Please select an audio file first.');
            return;
        }

        const formData = new FormData();
        formData.append('audio_file', file);

        transcribeButton.textContent = 'Transcribing...';
        transcribeButton.disabled = true;

        try {
            const response = await fetch('/transcribe-audio', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const transcribedText = data.text;
            console.log('Transcribed Text:', transcribedText);

            // Now, send the transcribed text to the /case-intake endpoint
            addMessage(`I've transcribed the audio. Now, processing it for case intake...`, 'agent');
// --- Add these debug logs ---
console.log("DEBUG: Transcribed text before /case-intake call:", transcribedText);
console.log("DEBUG: Type of transcribedText:", typeof transcribedText);
// --- End debug logs ---
            const intakeResponse = await fetch('/case-intake', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: transcribedText })
            });

            if (!intakeResponse.ok) {
                const errorData = await intakeResponse.json();
                throw new Error(errorData.error || `HTTP error! status: ${intakeResponse.status}`);
            }

            const intakeData = await intakeResponse.json();
            console.log('Case Intake Data:', intakeData);

            // Display structured data in chat or provide a prompt
            let intakeMessage = `Audio transcribed and processed! Here are the extracted details:\n\n`;
            intakeMessage += `**Client Name:** ${intakeData.client_name || 'N/A'}\n`;
            intakeMessage += `**Opposing Party:** ${intakeData.opposing_party || 'N/A'}\n`;
            intakeMessage += `**Case Type:** ${intakeData.case_type || 'N/A'}\n`;
            intakeMessage += `**Summary of Facts:** ${intakeData.summary_of_facts || 'N/A'}\n`;
            intakeMessage += `**Key Dates:** ${intakeData.key_dates && intakeData.key_dates.length > 0 ? intakeData.key_dates.join(', ') : 'N/A'}\n\n`;
            intakeMessage += `Would you like me to create a new case in the system with this information, or anything else?`;

            addMessage(intakeMessage, 'agent');
            fetchCases(); // Refresh dashboard to potentially see new case


        } catch (error) {
            console.error('Error during transcription or intake:', error);
            addMessage(`An error occurred during file processing: ${error.message}`, 'agent');
        } finally {
            transcribeButton.textContent = 'Transcribe Audio';
            transcribeButton.disabled = false;
            if (fileUploadZone) {
                const bElement = fileUploadZone.querySelector('b');
                const smallTextElement = fileUploadZone.querySelector('.small-text');
                if (bElement) bElement.textContent = 'Drag and drop audio file here';
                if (smallTextElement) smallTextElement.textContent = 'or click to select file';
            }
            audioUploadInput.value = ''; // Clear selected file input
            responseContainer.scrollTop = responseContainer.scrollHeight; // Scroll to bottom
        }
    });

});