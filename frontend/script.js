document.addEventListener('DOMContentLoaded', () => {
    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const submitButton = document.getElementById('submit-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    const responseText = document.getElementById('response-text');

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