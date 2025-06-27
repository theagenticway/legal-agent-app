document.addEventListener('DOMContentLoaded', () => {
    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const submitButton = document.getElementById('submit-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    const responseText = document.getElementById('response-text');
    // At the top, with the other element selectors
    const audioUploadInput = document.getElementById('audio-upload-input');
    const transcribeButton = document.getElementById('transcribe-button');
    const transcribeLoadingIndicator = document.getElementById('transcribe-loading-indicator');
// Add this new event listener inside the main 'DOMContentLoaded' listener
transcribeButton.addEventListener('click', async () => {
    const file = audioUploadInput.files[0];
    if (!file) {
        alert('Please select an audio file first.');
        return;
    }

    // --- UI Loading State ---
    transcribeButton.disabled = true;
    transcribeLoadingIndicator.style.display = 'block';

    // Use FormData to send the file
    const formData = new FormData();
    formData.append('audio_file', file);

    try {
        const response = await fetch('/transcribe-audio', {
            method: 'POST',
            body: formData, // No 'Content-Type' header needed, browser sets it for FormData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Transcription failed.');
        }

        const data = await response.json();

        // The magic! Put the transcribed text into the main query box.
        queryInput.value = data.text;
        queryInput.focus(); // Set focus to the input box for convenience

    } catch (error) {
        console.error('Error during transcription:', error);
        alert(`Transcription Error: ${error.message}`);
    } finally {
        // --- Reset UI ---
        transcribeButton.disabled = false;
        transcribeLoadingIndicator.style.display = 'none';
    }
});
    queryForm.addEventListener('submit', async (event) => {
        // Prevent the default form submission which reloads the page
        event.preventDefault();

        const userQuery = queryInput.value.trim();
        if (!userQuery) {
            return;
        }

        // --- Update UI for loading state ---
        submitButton.disabled = true;
        submitButton.textContent = 'Thinking...';
        loadingIndicator.style.display = 'block';
        responseText.textContent = ''; // Clear previous response

        try {
            // --- Make the API call to our backend ---
            const response = await fetch('/agent-query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: userQuery }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // --- Display the response ---
            responseText.textContent = data.answer;

        } catch (error) {
            console.error('Error fetching response:', error);
            responseText.textContent = 'An error occurred while fetching the response. Please check the console.';
        } finally {
            // --- Reset UI from loading state ---
            submitButton.disabled = false;
            submitButton.textContent = 'Ask Agent';
            loadingIndicator.style.display = 'none';
        }
    });
});
