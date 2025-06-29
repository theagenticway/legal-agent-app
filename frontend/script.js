document.addEventListener('DOMContentLoaded', () => {
    // --- Get all our HTML elements ---
    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const submitButton = document.getElementById('submit-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    const responseContainer = document.getElementById('response-container');
    
    const audioUploadInput = document.getElementById('audio-upload-input');
    const transcribeButton = document.getElementById('transcribe-button');
    const transcribeLoadingIndicator = document.getElementById('transcribe-loading-indicator');

    // --- SIMPLIFIED NAVIGATION (since we only have one view currently) ---
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            
            // Manage active state for links
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // For now, just log which section was clicked
            const linkText = link.textContent;
            console.log(`Navigation clicked: ${linkText}`);
            
            // You can add specific functionality for each nav item here
            if (linkText === 'Dashboard') {
                // Already showing dashboard
                console.log('Dashboard view active');
            } else if (linkText === 'Intake') {
                // Focus on the chat input for intake
                queryInput.focus();
                queryInput.placeholder = "Describe your legal issue...";
            } else if (linkText === 'Contracts') {
                queryInput.focus();
                queryInput.placeholder = "Ask about contracts...";
            } else if (linkText === 'Research') {
                queryInput.focus();
                queryInput.placeholder = "What would you like to research?";
            }
        });
    });

    // --- THE MEMORY STORE ---
    let chatHistory = [];

    // --- Function to display messages in the chat log ---
    function addMessageToLog(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-message', `${sender}-message`);
        
        // Create avatar
        const avatar = document.createElement('div');
        avatar.classList.add('avatar');
        if (sender === 'human') {
            avatar.innerHTML = '👤';
        } else {
            avatar.innerHTML = '🤖';
        }
        
        // Create message content container
        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');
        
        // Create sender name
        const senderName = document.createElement('div');
        senderName.classList.add('sender-name');
        senderName.textContent = sender === 'human' ? 'You' : 'Legal Agent';
        
        // Create message bubble
        const messageBubble = document.createElement('div');
        messageBubble.classList.add('message-bubble');
        messageBubble.textContent = message;
        
        // Assemble the message
        messageContent.appendChild(senderName);
        messageContent.appendChild(messageBubble);
        messageElement.appendChild(avatar);
        messageElement.appendChild(messageContent);
        
        responseContainer.appendChild(messageElement);
        
        // Scroll to the bottom
        responseContainer.scrollTop = responseContainer.scrollHeight;
    }

    // --- MAIN AGENT QUERY FORM ---
    queryForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const userQuery = queryInput.value.trim();
        if (!userQuery) return;

        console.log('Submitting query:', userQuery);

        // Add user's message to UI and history
        addMessageToLog('human', userQuery);
        chatHistory.push({ role: 'human', content: userQuery });

        // --- UI Loading State ---
        submitButton.disabled = true;
        loadingIndicator.style.display = 'flex';
        queryInput.value = ''; // Clear input after sending

        try {
            console.log('Making API call to /agent-query...');
            
            // --- Make the API call ---
            const response = await fetch('/agent-query', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ 
                    text: userQuery,
                    history: chatHistory.slice(0, -1) // Send history before current message
                }),
            });

            console.log('Response status:', response.status);
            console.log('Response headers:', Object.fromEntries(response.headers));

            if (!response.ok) {
                const errorText = await response.text();
                console.error('HTTP error response:', errorText);
                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
            }
            
            const data = await response.json();
            console.log('Response data:', data);
            
            if (!data.answer) {
                throw new Error('No answer received from server');
            }
            
            // Add agent's response to UI and history
            addMessageToLog('agent', data.answer);
            chatHistory.push({ role: 'ai', content: data.answer });

        } catch (error) {
            console.error('Error fetching response:', error);
            const errorMessage = `Sorry, I encountered an error: ${error.message}. Please try again.`;
            addMessageToLog('agent', errorMessage);
            
            // Also show error to user in a more visible way
            alert(`Error: ${error.message}`);
        } finally {
            // --- Reset UI ---
            submitButton.disabled = false;
            loadingIndicator.style.display = 'none';
        }
    });

    // --- AUDIO TRANSCRIPTION LISTENER ---
    transcribeButton.addEventListener('click', async () => {
        const file = audioUploadInput.files[0];
        if (!file) {
            alert('Please select an audio file first.');
            return;
        }
        
        console.log('Starting transcription for file:', file.name);
        
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
                const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
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

    // --- CASE DASHBOARD LOGIC ---
    const dashboardOptions = {
        valueNames: [
            'case_id',
            'status',
            'caller_phone_number',
            { name: 'created_at', attr: 'data-timestamp' } 
        ],
        item: `<tr>
                   <td class="case_id"></td>
                   <td class="status"></td>
                   <td class="caller_phone_number"></td>
                   <td class="created_at" data-timestamp=""></td>
                   <td><button class="summarize-btn">Summarize</button></td>
               </tr>`
    };

    // Initialize List.js only if the element exists
    let caseList = null;
    const dashboardElement = document.getElementById('cases-dashboard');
    if (dashboardElement) {
        try {
            caseList = new List('cases-dashboard', dashboardOptions);
        } catch (error) {
            console.error('Error initializing List.js:', error);
        }
    }

    // Function to fetch and load cases
    async function loadCases() {
        if (!caseList) {
            console.log('Case list not initialized, skipping load');
            return;
        }
        
        try {
            console.log('Loading cases from API...');
            const response = await fetch('/api/cases');
            
            if (!response.ok) {
                throw new Error(`Failed to fetch cases: ${response.status}`);
            }
            
            let cases = await response.json();
            console.log('Loaded cases:', cases);
            
            // Format the data before adding it to the list
            cases = cases.map(caseItem => {
                return {
                    ...caseItem,
                    created_at: new Date(caseItem.created_at).toLocaleString()
                };
            });

            if (cases.length > 0) {
                caseList.clear();
                caseList.add(cases);
            } else {
                caseList.clear();
                const tbody = document.querySelector('#cases-dashboard .list');
                if (tbody) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No cases found in the database.</td></tr>';
                }
            }

        } catch (error) {
            console.error('Error loading cases:', error);
        }
    }

    // Handle summarize button clicks
    const dashboardList = document.querySelector('#cases-dashboard .list');
    if (dashboardList) {
        dashboardList.addEventListener('click', (event) => {
            if (event.target.classList.contains('summarize-btn')) {
                const row = event.target.closest('tr');
                const caseId = row.querySelector('.case_id').textContent;
                
                console.log('Summarizing case:', caseId);
                
                // Find the full case data
                const caseItem = caseList.get('case_id', caseId)[0]?.values();
                
                if (!caseItem) {
                    alert('Could not find case data');
                    return;
                }
                
                // Construct summary prompt
                const summaryPrompt = `Please provide a concise summary of the following case:
                
Case ID: ${caseItem.case_id}
Status: ${caseItem.status}
Phone: ${caseItem.caller_phone_number}

Please provide your summary now.`;
                
                // Add to chat and submit
                addMessageToLog('human', summaryPrompt);
                chatHistory.push({ role: 'human', content: summaryPrompt });
                
                queryInput.value = summaryPrompt;
                queryForm.dispatchEvent(new Event('submit'));
                
                // Scroll to chat area
                responseContainer.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

    // Load cases on page load
    loadCases();

    // Add some basic error handling for the page
    window.addEventListener('error', (event) => {
        console.error('Global error:', event.error);
    });
    
    console.log('Script initialized successfully');
});