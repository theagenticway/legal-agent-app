// frontend/js/agent.js

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element References ---
    const queryForm = document.getElementById('query-form'); // This is now the parent container of the input area (if it's still a form, otherwise it's just the enclosing div/section)
    const queryInput = document.getElementById('query-input');
    const submitButton = document.getElementById('submit-button'); // The send button
    const attachButton = document.getElementById('attach-button'); // The new paperclip button
    const docUploadInput = document.getElementById('doc-upload-input'); // The hidden file input
    const responseContainer = document.getElementById('response-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const selectedFilesPreview = document.getElementById('selected-files-preview');
    const fileNamesSpan = document.getElementById('file-names');
    const clearFilesButton = document.getElementById('clear-files-button');
    const docUploadStatus = document.getElementById('doc-upload-status'); // For displaying RAG upload/delete status
    const indexedDocsList = document.getElementById('indexed-docs-list'); // For listing RAG documents

    // --- State Variables ---
    let chatHistory = []; // Stores the conversation history for the agent
    let selectedFiles = null; // To hold the FileList for RAG documents

    // --- Utility Functions ---

    /**
     * Adds a message to the chat display.
     * @param {string} text - The message content.
     * @param {'human'|'agent'} sender - The sender of the message.
     */
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
        messageBubble.innerHTML = text.replace(/\n/g, '<br>');
        messageBubble.innerHTML = messageBubble.innerHTML.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        contentDiv.appendChild(senderName);
        contentDiv.appendChild(messageBubble);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);

        responseContainer.appendChild(messageDiv);
        responseContainer.scrollTop = responseContainer.scrollHeight;
    }

    /** Clears any selected files from the UI and internal state. */
    function clearSelectedFiles() {
        selectedFiles = null;
        docUploadInput.value = ''; // Clear file input element
        selectedFilesPreview.style.display = 'none';
        fileNamesSpan.textContent = '';
        docUploadStatus.textContent = ''; // Clear status related to upload/delete
        queryInput.placeholder = "Ask the agent or attach documents..."; // Reset placeholder
        queryInput.disabled = false; // Enable text input
        submitButton.title = "Send"; // Reset send button tooltip
        // Reset submit button's icon if it changed visually
        const submitIcon = submitButton.querySelector('i');
        if (submitIcon) submitIcon.setAttribute('data-feather', 'send');
        feather.replace(); // Re-render icon
    }

    // --- Chat Input & Send Button Logic ---

    // Auto-resize textarea based on content
    queryInput.addEventListener('input', () => {
        queryInput.style.height = 'auto';
        queryInput.style.height = queryInput.scrollHeight + 'px';
        const maxHeight = 150;
        if (queryInput.scrollHeight > maxHeight) {
            queryInput.style.overflowY = 'auto';
            queryInput.style.height = maxHeight + 'px';
        } else {
            queryInput.style.overflowY = 'hidden';
        }
    });

    // Handle Send Button Click (submit query or upload files)
    submitButton.addEventListener('click', async (e) => {
        e.preventDefault(); // Prevent form default submission (if parent is a form)

        if (selectedFiles && selectedFiles.length > 0) {
            // If files are selected, process them for RAG
            await processDocumentsForRAG(selectedFiles);
        } else {
            // Otherwise, send the text query to the agent
            const query = queryInput.value.trim();
            if (!query) return;
            await sendAgentQuery(query);
        }
    });

    /**
     * Sends a text query to the agent backend.
     * @param {string} query - The user's query text.
     */
    async function sendAgentQuery(query) {
        addMessage(query, 'human');
        queryInput.value = ''; // Clear text input after sending
        queryInput.style.height = 'auto'; // Reset textarea height
        loadingIndicator.style.display = 'flex'; // Show loading indicator

        try {
            const response = await fetch('/agent-query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: query,
                    history: chatHistory
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            addMessage(data.answer, 'agent');
            chatHistory.push({ role: 'human', content: query });
            chatHistory.push({ role: 'ai', content: data.answer });

        } catch (error) {
            console.error('Error sending query to agent:', error);
            addMessage(`Sorry, I'm having trouble connecting to the agent right now. Please try again later. (Error: ${error.message})`, 'agent');
        } finally {
            loadingIndicator.style.display = 'none'; // Hide loading indicator
            responseContainer.scrollTop = responseContainer.scrollHeight; // Scroll to bottom
        }
    }

    // --- Document Attachment & Upload Logic ---

    // Trigger hidden file input when attach button is clicked
    attachButton.addEventListener('click', () => {
        docUploadInput.click();
    });

    // Prevent propagation from hidden file input to avoid double dialog
    docUploadInput.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    // Handle file selection (when files are chosen via dialog or drag/drop)
    docUploadInput.addEventListener('change', (e) => {
        selectedFiles = e.target.files;
        if (selectedFiles.length > 0) {
            const fileNames = Array.from(selectedFiles).map(file => file.name).join(', ');
            fileNamesSpan.textContent = fileNames;
            selectedFilesPreview.style.display = 'flex'; // Show file preview area

            queryInput.placeholder = `Ready to upload ${selectedFiles.length} file(s). Click send!`;
            queryInput.value = ''; // Clear text input if files are selected
            queryInput.disabled = true; // Disable text input while files are selected
            submitButton.title = "Upload Documents"; // Change send button tooltip
            // Optionally change send button icon to an upload icon
            const submitIcon = submitButton.querySelector('i');
            if (submitIcon) submitIcon.setAttribute('data-feather', 'upload-cloud');
            feather.replace(); // Re-render icon
        } else {
            clearSelectedFiles(); // No files selected, revert to text mode
        }
    });

    // Clear selected files button
    clearFilesButton.addEventListener('click', () => {
        clearSelectedFiles();
    });

    // Handle drag and drop for the entire chat input area
    const chatInputArea = document.querySelector('.chat-input-area');
    if (chatInputArea) {
        chatInputArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            chatInputArea.classList.add('drag-over');
            queryInput.placeholder = "Drop files here to upload...";
        });

        chatInputArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            chatInputArea.classList.remove('drag-over');
            if (!selectedFiles || selectedFiles.length === 0) {
                queryInput.placeholder = "Ask the agent or attach documents...";
            } else {
                queryInput.placeholder = `Ready to upload ${selectedFiles.length} file(s). Click send!`;
            }
        });

        chatInputArea.addEventListener('drop', (e) => {
            e.preventDefault();
            chatInputArea.classList.remove('drag-over');
            selectedFiles = e.dataTransfer.files;
            docUploadInput.files = selectedFiles; // Assign dropped files to hidden input
            docUploadInput.dispatchEvent(new Event('change')); // Trigger change event as if user selected files
        });
    }

    /**
     * Processes selected documents by uploading them for RAG indexing.
     * @param {FileList} files - The FileList object containing documents to upload.
     */
    async function processDocumentsForRAG(files) {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('documents', files[i]); // 'documents' matches the backend parameter name
        }

        const submitIcon = submitButton.querySelector('i');
        if (submitIcon) submitIcon.setAttribute('data-feather', 'loader'); // Change to spinner/loader icon
        feather.replace();
        submitButton.disabled = true;
        attachButton.disabled = true;
        queryInput.disabled = true; // Ensure text input is disabled during upload
        loadingIndicator.style.display = 'flex'; // Show main loading indicator
        docUploadStatus.textContent = 'Uploading and processing documents...';
        docUploadStatus.style.color = 'var(--text-secondary)';


        try {
            const response = await fetch('/process-rag-documents', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            docUploadStatus.textContent = data.message || 'Documents processed successfully!';
            docUploadStatus.style.color = 'var(--primary-accent)';
            addMessage(data.message || 'I have updated my knowledge base with the new documents.', 'agent');

        } catch (error) {
            console.error('Error processing documents:', error);
            docUploadStatus.textContent = `Error: ${error.message}`;
            docUploadStatus.style.color = 'red';
            addMessage(`An error occurred while updating my knowledge base: ${error.message}`, 'agent');
        } finally {
            if (submitIcon) submitIcon.setAttribute('data-feather', 'send'); // Reset to send icon
            feather.replace();
            submitButton.disabled = false;
            attachButton.disabled = false;
            queryInput.disabled = false;
            loadingIndicator.style.display = 'none'; // Hide main loading indicator
            clearSelectedFiles(); // Clear selected files after processing
            responseContainer.scrollTop = responseContainer.scrollHeight;
            await fetchIndexedRagDocuments(indexedDocsList); // Refresh the list of indexed documents
        }
    }

    // --- RAG Document Listing and Deletion ---

    /**
     * Fetches and displays documents currently indexed in the RAG system.
     * @param {HTMLElement} listElement - The tbody element to populate with indexed documents.
     */
    async function fetchIndexedRagDocuments(listElement) {
        if (!listElement) {
            console.warn("Indexed documents list element (tbody#indexed-docs-list) not found. Cannot display RAG documents.");
            return;
        }

        try {
            const response = await fetch('/api/rag-documents');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const docs = await response.json();
            console.log('Fetched indexed RAG documents:', docs);

            listElement.innerHTML = ''; // Clear existing list

            if (docs.length === 0) {
                listElement.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-secondary);">No documents currently indexed. Upload some!</td></tr>';
                return;
            }

            docs.forEach(doc => {
                const row = document.createElement('tr');
                const filenameCell = document.createElement('td');
                filenameCell.textContent = doc.filename;
                const chunksCell = document.createElement('td');
                chunksCell.textContent = doc.num_chunks;
                const indexedAtCell = document.createElement('td');
                indexedAtCell.textContent = new Date(doc.indexed_at).toLocaleString();

                const actionsCell = document.createElement('td');
                const deleteButton = document.createElement('button');
                deleteButton.classList.add('button', 'secondary-button');
                deleteButton.style.padding = '4px 8px';
                deleteButton.style.fontSize = '12px';
                deleteButton.textContent = 'Delete';
                deleteButton.onclick = async () => {
                    if (confirm(`Are you sure you want to delete "${doc.filename}"? This cannot be undone.`)) {
                        await deleteRagDocument(doc.filename);
                    }
                };
                actionsCell.appendChild(deleteButton);

                row.appendChild(filenameCell);
                row.appendChild(chunksCell);
                row.appendChild(indexedAtCell);
                row.appendChild(actionsCell);
                listElement.appendChild(row);
            });

        } catch (error) {
            console.error('Error fetching indexed RAG documents:', error);
            listElement.innerHTML = `<tr><td colspan="4" style="text-align: center; color: red;">Error loading documents: ${error.message}</td></tr>`;
        }
    }

    /**
     * Deletes a document from the RAG system.
     * @param {string} filename - The filename of the document to delete.
     */
    async function deleteRagDocument(filename) {
        docUploadStatus.textContent = `Deleting "${filename}"...`;
        docUploadStatus.style.color = 'var(--text-secondary)';
        loadingIndicator.style.display = 'flex'; // Show main loading indicator

        try {
            const response = await fetch(`/api/rag-documents/${encodeURIComponent(filename)}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            docUploadStatus.textContent = data.message;
            docUploadStatus.style.color = 'var(--primary-accent)';
            addMessage(data.message, 'agent');
            await fetchIndexedRagDocuments(indexedDocsList); // Refresh the list after deletion
        } catch (error) {
            console.error('Error deleting document:', error);
            docUploadStatus.textContent = `Error deleting "${filename}": ${error.message}`;
            docUploadStatus.style.color = 'red';
            addMessage(`An error occurred while deleting "${filename}": ${error.message}`, 'agent');
        } finally {
            loadingIndicator.style.display = 'none'; // Hide main loading indicator
        }
    }

    // --- Initializations ---

    // Initial welcome message from the agent
    addMessage("Hello! How can I assist you with your legal queries today? You can ask questions or attach documents to expand my knowledge base.", 'agent');

    // Handle initial query from dashboard (if redirected)
    const initialQuery = sessionStorage.getItem('agentChatInitialQuery');
    if (initialQuery) {
        sessionStorage.removeItem('agentChatInitialQuery');
        queryInput.value = initialQuery;
        // Optionally, auto-send the query if desired:
        // submitButton.click();
    }

    // Fetch and display indexed RAG documents on load and periodically
    fetchIndexedRagDocuments(indexedDocsList);
    setInterval(() => fetchIndexedRagDocuments(indexedDocsList), 60000); // Refresh every 60 seconds
});