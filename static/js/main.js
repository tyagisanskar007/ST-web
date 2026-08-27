/**
 * Shiv Traders - Public Website Main JavaScript
 * Handles filtering, responsive navigation, quote calculation, and AJAX submissions.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Menu Toggle
    const mobileToggle = document.querySelector('.mobile-menu-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (mobileToggle && navLinks) {
        mobileToggle.addEventListener('click', () => {
            navLinks.classList.toggle('show');
            const icon = mobileToggle.querySelector('i');
            if (icon) {
                if (navLinks.classList.contains('show')) {
                    icon.classList.remove('fa-bars');
                    icon.classList.add('fa-times');
                } else {
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            }
        });
    }

    // 2. Sticky Header Transition
    const header = document.querySelector('.main-header');
    if (header) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        });
    }

    // 3. Category Filter for Products & Projects
    const filterBtns = document.querySelectorAll('.filter-btn');
    const filterItems = document.querySelectorAll('.filter-item');

    if (filterBtns.length > 0) {
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const filterValue = btn.getAttribute('data-filter');

                filterItems.forEach(item => {
                    const itemCat = item.getAttribute('data-category');
                    if (filterValue === 'all' || itemCat === filterValue) {
                        item.style.display = '';
                        setTimeout(() => {
                            item.style.opacity = '1';
                            item.style.transform = 'scale(1)';
                        }, 50);
                    } else {
                        item.style.opacity = '0';
                        item.style.transform = 'scale(0.95)';
                        setTimeout(() => {
                            item.style.display = 'none';
                        }, 250);
                    }
                });
            });
        });
    }

    // 4. Live Quote Estimator Calculator
    const areaInput = document.getElementById('calc-area');
    const productSelect = document.getElementById('calc-product');
    const estOutput = document.getElementById('calc-result');

    if (areaInput && productSelect && estOutput) {
        const calculateEstimate = () => {
            const area = parseFloat(areaInput.value) || 0;
            const rate = parseFloat(productSelect.selectedOptions[0]?.getAttribute('data-rate')) || 45;
            if (area > 0) {
                const totalBlocks = Math.round(area * 3.5); // avg 3.5 to 4 blocks per sq ft for standard sizes
                const estPriceMin = Math.round(area * rate);
                const estPriceMax = Math.round(area * (rate + 12));
                estOutput.innerHTML = `
                    <div style="background: rgba(205, 168, 81, 0.1); border: 1px solid var(--gold-border); padding: 1.25rem; border-radius: var(--radius-sm); margin-top: 1rem;">
                        <h4 style="color: var(--gold-light); margin-bottom: 0.5rem;"><i class="fas fa-calculator"></i> Estimated Material Requirement</h4>
                        <p style="font-size: 0.95rem; color: #fff; margin-bottom: 0.25rem;">Approx. Blocks: <strong>${totalBlocks.toLocaleString()} Units</strong></p>
                        <p style="font-size: 0.95rem; color: var(--text-secondary);">Estimated Price Range: <strong style="color: var(--gold-light);">₹${estPriceMin.toLocaleString()} - ₹${estPriceMax.toLocaleString()}*</strong></p>
                        <small style="color: var(--text-muted); display:block; margin-top: 0.5rem;">*Indicative ex-factory rate. Freight & laying charges extra as per site conditions.</small>
                    </div>
                `;
            } else {
                estOutput.innerHTML = '';
            }
        };

        areaInput.addEventListener('input', calculateEstimate);
        productSelect.addEventListener('change', calculateEstimate);
    }

    // 5. Contact / Enquiry AJAX Form Submission
    const contactForm = document.getElementById('contact-form') || document.getElementById('enquiry-form');
    if (contactForm) {
        contactForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = contactForm.querySelector('button[type="submit"]');
            const originalText = submitBtn ? submitBtn.innerHTML : 'Submit';

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
            }

            const formData = new FormData(contactForm);
            const dataObj = Object.fromEntries(formData.entries());

            try {
                const response = await fetch('/api/enquiry', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(dataObj)
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast(result.message || 'Thank you for contacting Shiv Traders. Our team will get in touch with you shortly.', 'success');
                    contactForm.reset();
                    if (estOutput) estOutput.innerHTML = '';
                } else {
                    showToast(result.error || 'Failed to send message. Please check the fields.', 'error');
                }
            } catch (err) {
                console.error('Submission error:', err);
                showToast('Network error. Please try again or reach out via WhatsApp.', 'error');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }
            }
        });
    }

    // 6. Floating WhatsApp Button URL generator with dynamic default message
    const whatsappBtn = document.querySelector('.floating-whatsapp');
    if (whatsappBtn) {
        const phone = whatsappBtn.getAttribute('data-phone') || '919829012345';
        const cleanPhone = phone.replace(/[^0-9]/g, '');
        const message = encodeURIComponent("Hello Shiv Traders, I am visiting your website and would like an estimate/inquiry regarding your interlock pavers and infrastructure services.");
        whatsappBtn.setAttribute('href', `https://wa.me/${cleanPhone}?text=${message}`);
        whatsappBtn.setAttribute('target', '_blank');
    }
});

// Toast notification helper
function showToast(message, type = 'success') {
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
        toast.style.transition = 'all 0.4s ease';
        setTimeout(() => toast.remove(), 400);
    }, 4500);
}
