// js/global.js

document.addEventListener('DOMContentLoaded', () => {
    feather.replace(); // Initialize Feather icons on initial load

    // Function to set the active navigation link
    function setActiveNavLink() {
        const path = window.location.pathname.split('/').pop(); // Get current page filename
        const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
        navItems.forEach(item => {
            item.classList.remove('active'); // Remove active from all
            if (item.getAttribute('href') === path) {
                item.classList.add('active'); // Add active to current page
            }
        });
    }

    // Set active link on load
    setActiveNavLink();

    // If you have dynamic content loading or SPA-like navigation,
    // you might need to call setActiveNavLink() again after routing changes.

    // Global Search Bar functionality (placeholder for now)
    const globalSearchInput = document.getElementById('global-search');
    if (globalSearchInput) {
        globalSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const query = globalSearchInput.value.trim();
                if (query) {
                    console.log('Global search initiated:', query);
                    // In a real app, you'd trigger a global search API call here
                    // For now, let's just clear the input
                    globalSearchInput.value = '';
                }
            }
        });
    }
});