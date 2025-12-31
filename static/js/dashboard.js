/**
 * Dashboard AJAX auto-update functionality
 */

(function() {
    'use strict';

    const UPDATE_INTERVAL = 5000; // 5 seconds

    /**
     * Update dashboard with latest status
     */
    function updateDashboard() {
        fetch('/api/status')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                updateMonitorCards(data.monitors);
            })
            .catch(error => {
                console.error('Failed to update dashboard:', error);
            });
    }

    /**
     * Update individual monitor cards
     */
    function updateMonitorCards(monitors) {
        monitors.forEach(monitor => {
            const card = document.querySelector(`[data-monitor-id="${monitor.id}"]`);
            if (!card) return;

            // Update status classes
            card.className = `monitor-card status-${monitor.status}`;

            // Update status badge
            const statusBadge = card.querySelector('.status-badge');
            if (statusBadge) {
                statusBadge.className = `status-badge status-${monitor.status}`;
                statusBadge.textContent = monitor.status.toUpperCase();
            }

            // Update response time
            const responseTime = card.querySelector('.response-time');
            if (responseTime && monitor.response_time) {
                responseTime.textContent = Math.round(monitor.response_time) + 'ms';
            }

            // Update error message
            const errorMessage = card.querySelector('.error-message');
            if (monitor.error_message) {
                if (!errorMessage) {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'error-message';
                    errorDiv.textContent = monitor.error_message;
                    card.querySelector('.monitor-header').after(errorDiv);
                } else {
                    errorMessage.textContent = monitor.error_message;
                }
            } else if (errorMessage) {
                errorMessage.remove();
            }

            // Update incident banner
            const incidentBanner = card.querySelector('.incident-banner');
            if (monitor.ongoing_incident_id) {
                if (!incidentBanner) {
                    const bannerDiv = document.createElement('div');
                    bannerDiv.className = 'incident-banner';
                    bannerDiv.textContent = `Ongoing incident #${monitor.ongoing_incident_id}`;
                    card.querySelector('.monitor-header').after(bannerDiv);
                }
            } else if (incidentBanner) {
                incidentBanner.remove();
            }

            // Update last checked time
            const lastChecked = card.querySelector('.last-checked');
            if (lastChecked && monitor.last_checked) {
                lastChecked.textContent = 'Last checked: ' + formatTimeAgo(new Date(monitor.last_checked));
            }
        });
    }

    /**
     * Format timestamp as "time ago" string
     */
    function formatTimeAgo(timestamp) {
        const now = new Date();
        const seconds = Math.floor((now - timestamp) / 1000);

        if (seconds < 60) {
            return seconds + 's ago';
        } else if (seconds < 3600) {
            return Math.floor(seconds / 60) + 'm ago';
        } else if (seconds < 86400) {
            return Math.floor(seconds / 3600) + 'h ago';
        } else {
            return Math.floor(seconds / 86400) + 'd ago';
        }
    }

    // Start auto-update when page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setInterval(updateDashboard, UPDATE_INTERVAL);
        });
    } else {
        setInterval(updateDashboard, UPDATE_INTERVAL);
    }

    console.log('Dashboard auto-update enabled (interval: ' + UPDATE_INTERVAL + 'ms)');
})();
