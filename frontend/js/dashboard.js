// frontend/js/dashboard.js

document.addEventListener('DOMContentLoaded', async () => {
    feather.replace(); // Ensure icons are rendered

    // Function to fetch and render overview counts
    async function renderOverview() {
        try {
            const response = await fetch('/api/dashboard/overview');
            if (!response.ok) throw new Error('Failed to fetch overview data');
            const data = await response.json();

            document.getElementById('active-contracts-count').textContent = data.active_contracts;
            document.getElementById('upcoming-deadlines-count').textContent = data.upcoming_deadlines;
            document.getElementById('new-notifications-count').textContent = data.new_notifications;

            // Also update the badge in the header if it exists
            const notificationBadge = document.querySelector('.notification-icon .badge');
            if (notificationBadge) {
                notificationBadge.textContent = data.new_notifications;
                notificationBadge.style.display = data.new_notifications > 0 ? 'block' : 'none';
            }

        } catch (error) {
            console.error('Error rendering overview:', error);
            // Optionally display an error message on the UI
        }
    }

    // Function to fetch and render lists (recent activity, deadlines, notifications)
    async function renderList(endpoint, containerId, itemTemplateFunc) {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) throw new Error(`Failed to fetch data from ${endpoint}`);
            const data = await response.json();

            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = ''; // Clear existing placeholders
                if (data.length === 0) {
                    container.innerHTML = `<p class="text-secondary" style="text-align: center; padding: 20px;">No items to display.</p>`;
                    return;
                }
                data.forEach(item => {
                    const itemHtml = itemTemplateFunc(item);
                    container.insertAdjacentHTML('beforeend', itemHtml);
                });
            }
        } catch (error) {
            console.error(`Error rendering list from ${endpoint}:`, error);
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = `<p class="text-secondary" style="text-align: center; padding: 20px;">Error loading data.</p>`;
            }
        }
    }

    // Item template functions
    function activityItemTemplate(activity) {
        const iconMapping = {
            "Contract Review": "file-text",
            "Legal Research": "search",
            "Case Management": "briefcase",
            "Client Onboarding": "users",
            // Add more as needed
        };
        const icon = iconMapping[activity.activity_type] || "activity"; // Default icon
        const timeAgo = new Date(activity.performed_at).toLocaleDateString(undefined, {
            year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: 'numeric'
        }); // Or use a library like moment.js for "X days ago"

        return `
            <div class="flex items-center gap-4">
                <i data-feather="${icon}" class="text-secondary" style="width: 20px; height: 20px;"></i>
                <span class="text-primary flex-grow-1">${activity.description}</span>
                <span class="text-secondary text-sm">${activity.activity_type} - ${timeAgo}</span>
            </div>
        `;
    }

    function deadlineItemTemplate(deadline) {
        const iconMapping = {
            "Review": "file-text",
            "Litigation": "tool",
            "Compliance": "shield",
            "Intake": "user-plus",
            "Communication": "message-square"
            // Add more as needed
        };
        const icon = iconMapping[deadline.task_type] || "calendar";
        const dueDate = new Date(deadline.due_date);
        const now = new Date();
        let dueText = '';
        if (dueDate < now && deadline.status !== 'Completed') {
            dueText = `<span style="color: #EF4444; font-weight: 600;">Overdue</span>`; // Red for overdue
        } else {
            const diffDays = Math.ceil((dueDate - now) / (1000 * 60 * 60 * 24));
            if (diffDays === 0) {
                dueText = `Due Today`;
            } else if (diffDays === 1) {
                dueText = `Due Tomorrow`;
            } else if (diffDays > 0) {
                dueText = `Due in ${diffDays} days`;
            } else {
                dueText = `Past Due`; // Should be caught by overdue logic, but fallback
            }
        }
        
        return `
            <div class="flex items-center gap-4">
                <i data-feather="${icon}" class="text-secondary" style="width: 20px; height: 20px;"></i>
                <span class="text-primary flex-grow-1">${deadline.title}</span>
                <span class="text-secondary text-sm">${dueText}</span>
            </div>
        `;
    }

    function notificationItemTemplate(notification) {
        const iconMapping = {
            "Contract Review": "file-text",
            "Legal Research": "search",
            "Case Status": "briefcase",
            "Welcome": "bell",
            // Add more as needed
        };
        const icon = iconMapping[notification.notification_type] || "bell";
        const timeAgo = new Date(notification.created_at).toLocaleDateString(undefined, {
            year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: 'numeric'
        });

        // Add class for unread notifications for styling if desired
        const readClass = notification.is_read ? '' : 'font-semibold'; // Unread notifications are bold
        const readColor = notification.is_read ? 'text-secondary' : 'text-primary';

        return `
            <div class="flex items-center gap-4 ${readClass}" ${notification.is_read ? '' : 'style="background-color: rgba(27, 185, 154, 0.05); padding: 8px 12px; border-radius: 8px; margin: -8px -12px;"'}>
                <i data-feather="${icon}" class="${notification.is_read ? 'text-secondary' : 'text-accent'}" style="width: 20px; height: 20px;"></i>
                <span class="${readColor} flex-grow-1">${notification.message}</span>
                <span class="${readColor} text-sm">${notification.notification_type}</span>
            </div>
        `;
    }

    // Initial render calls
    await renderOverview();
    await renderList('/api/dashboard/recent-activity', 'recent-activity-container', activityItemTemplate);
    await renderList('/api/dashboard/upcoming-deadlines', 'upcoming-deadlines-container', deadlineItemTemplate);
    await renderList('/api/dashboard/notifications', 'notifications-container', notificationItemTemplate);

    // Re-render Feather icons after dynamic content is added
    feather.replace();
});