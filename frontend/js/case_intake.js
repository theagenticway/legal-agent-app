// frontend/js/case_intake.js

document.addEventListener('DOMContentLoaded', () => {
    const manualIntakeForm = document.getElementById('manual-intake-form');

    const fileUploadZone = document.getElementById('file-upload-zone');
    const audioUploadInput = document.getElementById('audio-upload-input');
    const transcribeButton = document.getElementById('transcribe-button');
    const transcriptionStatus = document.getElementById('transcription-status');

    // --- IMPORTANT: Null check for elements ---
    if (!transcribeButton || !audioUploadInput || !fileUploadZone) {
        console.error("Error: Case Intake elements not found in the DOM. Audio intake functionality may be limited.");
        if (transcribeButton) transcribeButton.disabled = true; // Disable button if missing
        if (fileUploadZone) fileUploadZone.style.pointerEvents = 'none'; // Make dropzone unclickable
        return; // Exit if critical elements are missing
    }
    // --- End Null check ---


    // --- Manual Intake Form ---
    manualIntakeForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(manualIntakeForm);
        const data = {};
        formData.forEach((value, key) => {
            if (key === 'key_dates') {
                data[key] = value.split(',').map(s => s.trim()).filter(s => s);
            } else {
                data[key] = value;
            }
        });

        // For manual intake, we send the entire summary to the case-intake endpoint
        // as if it were a transcribed text. This reuses the /case-intake endpoint logic.
        const combinedText = `Client: ${data.client_name || ''}\n` +
                             `Opposing Party: ${data.opposing_party || ''}\n` +
                             `Case Type: ${data.case_type || ''}\n` +
                             `Summary of Facts: ${data.summary_of_facts || ''}\n` +
                             `Key Dates: ${(data.key_dates || []).join(', ')}\n`;

        console.log("Submitting manual intake text for processing:", combinedText);

        try {
            const response = await fetch('/case-intake', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: combinedText })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log('Manual Intake Processed:', result);
            alert('Case manually submitted and processed successfully!\n\n' + JSON.stringify(result, null, 2));
            manualIntakeForm.reset(); // Clear form
            transcriptionStatus.textContent = 'Manual intake submitted successfully.';
            transcriptionStatus.style.color = 'var(--primary-accent)';

        } catch (error) {
            console.error('Error submitting manual intake:', error);
            alert(`Error submitting manual intake: ${error.message}`);
            transcriptionStatus.textContent = `Error submitting manual intake: ${error.message}`;
            transcriptionStatus.style.color = 'red';
        }
    });


    // --- File Upload & Transcription ---
    fileUploadZone.addEventListener('click', () => {
        audioUploadInput.click();
    });
    // --- ADD THIS LINE ---
    audioUploadInput.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent the click from bubbling up to fileUploadZone
    });
    // --- END ADD THIS LINE ---
    audioUploadInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            console.log('Selected file:', file.name);
            const bElement = fileUploadZone.querySelector('b');
            const smallTextElement = fileUploadZone.querySelector('.small-text');
            if (bElement) bElement.textContent = file.name;
            if (smallTextElement) smallTextElement.textContent = 'Click to change file';
            transcribeButton.disabled = false; // Enable button once file is selected
        } else {
            transcribeButton.disabled = true; // Disable if no file
            fileUploadZone.querySelector('b').textContent = 'Drag and drop audio file here';
            fileUploadZone.querySelector('.small-text').textContent = 'or click to select file';
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
        transcriptionStatus.textContent = 'Uploading and transcribing audio...';
        transcriptionStatus.style.color = 'var(--text-secondary)';

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

            transcriptionStatus.textContent = 'Audio transcribed. Processing for case intake...';
            transcriptionStatus.style.color = 'var(--text-secondary)';

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

            transcriptionStatus.textContent = 'Case processed successfully!';
            transcriptionStatus.style.color = 'var(--primary-accent)';
            alert('Audio transcribed and case processed successfully!\n\nExtracted details:\n' + JSON.stringify(intakeData, null, 2));

            // Optionally, you might want to redirect to the dashboard or refresh it
            // window.location.href = 'dashboard.html';

        } catch (error) {
            console.error('Error during transcription or intake:', error);
            transcriptionStatus.textContent = `Error: ${error.message}`;
            transcriptionStatus.style.color = 'red';
            alert(`An error occurred during file processing: ${error.message}`);
        } finally {
            transcribeButton.textContent = 'Transcribe Audio & Process Intake';
            transcribeButton.disabled = false;
            const bElement = fileUploadZone.querySelector('b');
            const smallTextElement = fileUploadZone.querySelector('.small-text');
            if (bElement) bElement.textContent = 'Drag and drop audio file here';
            if (smallTextElement) smallTextElement.textContent = 'or click to select file';
            audioUploadInput.value = ''; // Clear selected file input
        }
    });

});