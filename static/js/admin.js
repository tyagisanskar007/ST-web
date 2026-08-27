/**
 * Shiv Traders - Admin Dashboard JavaScript
 * Handles table filtering, AJAX status updates, image previews, and modal operations.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Sidebar Toggle
    const sidebarToggle = document.getElementById('admin-sidebar-toggle');
    const sidebar = document.querySelector('.admin-sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // 2. Real-Time Table Search Filter
    const searchInput = document.getElementById('table-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const rows = document.querySelectorAll('.admin-table tbody tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(query)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    // 3. Image Upload Live Preview
    const imageInputs = document.querySelectorAll('input[type="file"].preview-target');
    imageInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            const previewBox = document.getElementById(input.getAttribute('data-preview-id'));
            if (file && previewBox) {
                const reader = new FileReader();
                reader.onload = (re) => {
                    previewBox.innerHTML = `<img src="${re.target.result}" alt="Preview" style="width:100%;height:100%;object-fit:cover;">`;
                };
                reader.readAsDataURL(file);
            }
        });
    });

    // 4. Inline Enquiry Status Updater
    const statusSelects = document.querySelectorAll('.status-select-ajax');
    statusSelects.forEach(select => {
        select.addEventListener('change', async (e) => {
            const enquiryId = select.getAttribute('data-enquiry-id');
            const newStatus = select.value;
            const originalValue = select.getAttribute('data-current-value');

            try {
                const response = await fetch(`/admin/api/enquiries/${enquiryId}/status`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: newStatus })
                });
                const res = await response.json();
                if (response.ok && res.success) {
                    select.setAttribute('data-current-value', newStatus);
                    showAdminToast(`Status updated to ${newStatus}`, 'success');
                } else {
                    select.value = originalValue;
                    showAdminToast(res.error || 'Failed to update status', 'error');
                }
            } catch (err) {
                console.error(err);
                select.value = originalValue;
                showAdminToast('Network error while updating status', 'error');
            }
        });
    });
});

// Admin Toast Notifications
function showAdminToast(message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    toast.innerHTML = `<i class="fas ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Modal helper
function openModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.add('active');
}

function closeModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.remove('active');
}
