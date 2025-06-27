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
});