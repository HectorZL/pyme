/**
 * Handles AJAX updates for anime list status changes and tab loading
 */

document.addEventListener('DOMContentLoaded', function() {
    // Global variables
    const tabContents = {
        'watching': { loading: 'watching-loading', content: 'watching-content' },
        'completed': { loading: 'completed-loading', content: 'completed-content' },
        'on-hold': { loading: 'on-hold-loading', content: 'on-hold-content' },
        'dropped': { loading: 'dropped-loading', content: 'dropped-content' },
        'plan-to-watch': { loading: 'plan-to-watch-loading', content: 'plan-to-watch-content' }
    };
    
    // Initialize tooltips
    const initTooltips = () => {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    };
    
    // Handle tab changes
    document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function (e) {
            const tabId = e.target.getAttribute('aria-controls');
            if (tabId !== 'all' && tabContents[tabId]) {
                loadTabContent(tabId);
            }
        });
    });
    
    // Load content for a specific tab
    function loadTabContent(tabId) {
        const tab = tabContents[tabId];
        if (!tab) return;
        
        const loadingEl = document.getElementById(tab.loading);
        const contentEl = document.getElementById(tab.content);
        
        // Show loading, hide content
        if (loadingEl) loadingEl.style.display = 'block';
        if (contentEl) contentEl.innerHTML = '';
        
        // Convert tab ID to status (e.g., 'on-hold' -> 'on_hold')
        const status = tabId.replace('-', '_');
        
        // Fetch content
        fetch(`/anime/api/list/${status}/`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Update content
                if (contentEl) {
                    contentEl.innerHTML = data.html;
                    initTooltips(); // Reinitialize tooltips for new content
                }
                
                // Update tab badges with new counts
                updateTabBadges(data.status_counts);
                
                // Update stats cards if they exist
                updateStatsCards(data.status_counts);
            } else {
                throw new Error(data.message || 'Error al cargar la lista');
            }
        })
        .catch(error => {
            console.error('Error loading tab content:', error);
            if (contentEl) {
                contentEl.innerHTML = `
                    <div class="col-12 text-center py-5">
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Error al cargar la lista. Por favor, intenta de nuevo.
                        </div>
                    </div>`;
            }
        })
        .finally(() => {
            if (loadingEl) loadingEl.style.display = 'none';
        });
    }
    
    // Update tab badges with new counts
    function updateTabBadges(counts) {
        const statusMap = {
            'watching': 'Viendo',
            'completed': 'Completados',
            'on_hold': 'En Pausa',
            'dropped': 'Abandonados',
            'plan_to_watch': 'Por Ver'
        };
        
        // Update each tab's badge
        Object.entries(statusMap).forEach(([status, label]) => {
            const tabElement = document.querySelector(`[aria-controls="${status.replace('_', '-')}"]`);
            if (tabElement) {
                const badge = tabElement.querySelector('.badge');
                if (badge) {
                    badge.textContent = counts[status] || 0;
                }
            }
        });
    }
    
    // Update stats cards with new counts
    function updateStatsCards(counts) {
        const statsMap = {
            'watching': { element: '.stat-watching', icon: 'fa-tv' },
            'completed': { element: '.stat-completed', icon: 'fa-check-circle' },
            'on_hold': { element: '.stat-on-hold', icon: 'fa-pause-circle' },
            'dropped': { element: '.stat-dropped', icon: 'fa-times-circle' },
            'plan_to_watch': { element: '.stat-plan-to-watch', icon: 'fa-bookmark' }
        };
        
        // Update each stat card
        Object.entries(statsMap).forEach(([status, { element, icon }]) => {
            const statElement = document.querySelector(`${element} .stat-count`);
            if (statElement) {
                statElement.textContent = counts[status] || 0;
            }
        });
        
        // Update total count
        const totalElement = document.querySelector('.stat-total .stat-count');
        if (totalElement) {
            const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
            totalElement.textContent = total;
        }
    }
    
    // Handle status updates
    document.addEventListener('click', function(e) {
        const statusLink = e.target.closest('.update-status');
        if (!statusLink) return;
        
        e.preventDefault();
        
        const animeId = statusLink.dataset.animeId;
        const status = statusLink.dataset.status;
        const dropdown = statusLink.closest('.dropdown');
        const button = dropdown ? dropdown.querySelector('.dropdown-toggle') : null;
        const originalButtonHTML = button ? button.innerHTML : '';
        
        // Show loading state
        if (button) {
            button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
            button.disabled = true;
        }
        
        // Send AJAX request
        fetch(updateAnimeStatusUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFTTOKEN': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
            },
            body: `anime_id=${animeId}&status=${status}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Update UI based on the response
                updateUIAfterStatusChange(animeId, status, data, button, originalButtonHTML);
                
                // Show success message
                showAlert('success', data.message);
                
                // If we're on the user's list page, refresh the current tab
                if (window.location.pathname.includes('my-list')) {
                    const activeTab = document.querySelector('.tab-pane.active');
                    if (activeTab && activeTab.id !== 'all') {
                        loadTabContent(activeTab.id);
                    }
                }
            } else {
                throw new Error(data.message || 'Error al actualizar el estado');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('danger', error.message || 'Error al actualizar el estado');
        })
        .finally(() => {
            // Restore button state
            if (button && !button.disabled) {
                button.innerHTML = originalButtonHTML;
            }
        });
    });
    
    // Initialize tooltips on page load
    initTooltips();
});

/**
 * Updates the UI after a successful status change
 */
function updateUIAfterStatusChange(animeId, status, data, button, originalButtonHTML) {
    // Skip if no button was passed
    if (!button) return;
    
    // Update button text and style
    if (status === 'none') {
        // If removing from list
        button.innerHTML = 'Añadir a mi lista';
        button.className = button.className.replace(/\bbtn-(watching|completed|on_hold|dropped|plan_to_watch)\b/g, '');
        button.classList.add('btn-outline-primary');
    } else {
        // If changing status
        button.innerHTML = data.status_display;
        
        // Remove all status classes and add the new one
        button.className = button.className.replace(
            /\b(btn-outline-|btn-)(primary|success|info|warning|danger|secondary|dark|light|link)\b/g, 
            ''
        );
        button.classList.add('btn', `btn-${status}`);
    }
    
    // Re-enable the button
    button.disabled = false;
    
    // Update the count in the tab if we're on the user's list page
    if (window.location.pathname.includes('my-list')) {
        updateTabCounts(status, data.status_display);
    }
}

/**
 * Updates the count in the status tabs
 */
function updateTabCounts(newStatus, statusDisplay) {
    // Update the current tab's count
    const currentTab = document.querySelector('.nav-link.active');
    if (currentTab) {
        const currentBadge = currentTab.querySelector('.badge');
        if (currentBadge) {
            const currentCount = parseInt(currentBadge.textContent) || 0;
            if (currentCount > 0) {
                currentBadge.textContent = currentCount - 1;
            }
        }
    }
    
    // Update the new status tab's count
    const newTab = document.querySelector(`[data-bs-target="#${newStatus}"]`);
    if (newTab) {
        const newBadge = newTab.querySelector('.badge');
        if (newBadge) {
            const newCount = parseInt(newBadge.textContent) || 0;
            newBadge.textContent = newCount + 1;
        }
    }
}

/**
 * Shows a temporary alert message
 */
function showAlert(type, message) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alert.style.top = '20px';
    alert.style.right = '20px';
    alert.style.zIndex = '1100';
    alert.style.maxWidth = '350px';
    alert.role = 'alert';
    
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(alert);
    
    // Remove alert after 3 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 3000);
}
