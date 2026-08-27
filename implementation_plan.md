# Implementation Plan - Shiv Traders Luxury Manufacturing & Infrastructure Website

Shiv Traders is a luxury manufacturing and infrastructure contracting brand specializing in high-grade interlocking paver blocks, industrial pavements, urban street development, parking lots, factory construction, and government infrastructure projects. This plan outlines the complete development of a production-ready, highly aesthetic, fast, SEO-friendly, and secure Flask web application with seamless Firebase Cloud Firestore, Firebase Storage, and Firebase Authentication integrations.

---

## User Review Required

> [!IMPORTANT]
> - **Dual Storage & Database Engine (Firebase + Robust Hybrid Fallback)**: The architecture natively connects to Google Cloud Firebase (Firestore, Storage, Auth) using the official `firebase-admin` SDK when credentials are provided in `.env`. To ensure instant local operability without requiring an immediate cloud project setup, a robust local JSON-backed datastore engine with identical collections, schemas, and queries will initialize automatically as an active fallback.
> - **Production Security**: Admin credentials and sensitive Firebase Service Account private keys will be securely managed via environment variables and server-side sessions. Passwords will be securely hashed with Werkzeug.

---

## Architecture & Visual Identity

### 1. Aesthetic & Color Direction
- **Primary / Dark Foundations**: Deep Charcoal / Rich Obsidian (`#0f1115`, `#16181d`, `#1c1f26`)
- **Luxury Accents**: Brushed Metallic Gold / Amber Brass (`#cda851`, `#dfbe6f`, `#b59139`)
- **Industrial Accents**: Concrete Slate (`#383d47`, `#5a6270`), Clean Off-White (`#f8f9fb`)
- **Typography**: Clean, high-end geometric sans-serif for luxury architecture (`Plus Jakarta Sans` / `Outfit` + `Cinzel` accents)
- **Visuals**: High-resolution imagery with subtle glassmorphism cards, cinematic hero headers, crisp interactive UI components, and mobile-first responsiveness.

---

## Proposed Changes & File Structure

### Configuration & Core Backend
- `config.py`: Application configurations, session keys, Firebase project settings, security constants.
- `firebase_config.py`: Firebase Admin SDK initialization, Firestore client provider, Storage bucket handler, and synchronous dual-mode repository layer with seed data.
- `app.py`: Flask application routes, view handlers, API endpoints, rate limiting, and secure admin authentication decorators.
- `requirements.txt` & `.env.example`: Complete dependencies and environment variable templates.

### Templates (`templates/`)
- `base.html`: Luxury master layout with dynamic header, contact bar, mega-navigation, floating WhatsApp button, dynamic company footer, and notifications toast system.
- `index.html`: Hero banner, dynamic statistics counters, product showcase carousel/grid, featured infrastructure projects, manufacturing prowess preview, credibility badges, and quote calculator.
- `about.html`: Company heritage, vision & mission, engineering standards, testing lab & compressive strength benchmarks (M30, M40, M50).
- `products.html`: Interactive product catalog with category filter tabs, specifications summary, search bar, and direct enquiry links.
- `product_details.html`: High-res gallery preview, technical specification sheet, heavy-duty applications, dimension details, and quote request modal.
- `manufacturing.html`: Factory infrastructure, high-tonnage hydraulic presses, vibro-compaction technology, German pigment blending, automated curing chambers, and ISO compliance.
- `services.html`: Turnkey infrastructure execution services (Interlock Paving, Industrial Flooring, Road Construction, Municipal Development).
- `projects.html`: Portfolio gallery with sector filters (Street Development, Parking Area, Market Development, Factory Construction, Government Infrastructure).
- `project_details.html`: In-depth project case study, location, area in sq. ft., completion timeline, and photo gallery.
- `government.html`: Public sector tenders, municipal infrastructure, CPWD/PWD specifications compliance, and municipal streetscape standards.
- `credentials.html`: Verified credentials showcase (GST registration, MSME/Udyam, ISO 9001:2015, BIS lab test reports, Trademark information).
- `contact.html`: Contact form, interactive quote inquiry generator, location details, factory address, and business hours.

### Admin Dashboard Templates (`templates/admin/`)
- `base_admin.html`: Admin sidebar, top navigation, quick search, alert messages, and user profile.
- `login.html`: Luxury admin login page with password visibility toggle and rate limiting.
- `dashboard.html`: Analytics overview (Total Products, Total Projects, New Enquiries, Total Inquiries), monthly trend cards, and quick actions.
- `products.html`, `add_product.html`, `edit_product.html`: Complete product CRUD with image upload & gallery management.
- `projects.html`, `add_project.html`, `edit_project.html`: Complete project CRUD with multi-image uploads and status updates.
- `services.html`, `add_service.html`, `edit_service.html`: Manage company services catalog.
- `enquiries.html`, `enquiry_details.html`: Filterable enquiry list (New, Contacted, In Progress, Completed, Cancelled) with status switcher and search.
- `company.html`: Edit company address, GST, phone, WhatsApp number, email, and working hours.
- `credentials.html`: Add/update official certifications and credentials.
- `settings.html`: Admin account settings, password change, and Firebase connection status tester.

### Assets (`static/`)
- `static/css/style.css`: Custom luxury CSS styling, glassmorphism, responsive grid, gold gradients, animations.
- `static/css/admin.css`: Clean, dark-themed modern dashboard styling.
- `static/js/main.js`: Public website interactions (filtering, quote calculator, smooth scrolling, modal lightbox, dynamic WhatsApp URL).
- `static/js/admin.js`: Admin interactions (live image preview, table search/filter, quick status update AJAX, charts).
- `static/images/*`: High-quality realistic images for paver products, factory machinery, pavers installation, government streets, and brand logos.

---

## Verification Plan

### Automated Tests
- Test Flask startup and route availability (`pytest` or Python test script).
- Verify Firestore/repository CRUD operations for Products, Projects, Enquiries, and Company Information.
- Test enquiry form submission API with validation and rate limiting.
- Test admin authentication (login, protected routes, logout).

### Manual Verification
- Test all public pages on desktop and mobile viewport dimensions.
- Test adding, editing, and deleting products and projects in the Admin Dashboard, verifying that changes immediately reflect on the public website.
- Submit customer enquiry on public contact form and verify it appears with "New" status in the Admin Enquiries dashboard.
- Test status changes (New -> Contacted -> Completed) and verify persistent storage.
- Verify dynamic WhatsApp floating button with customized message and phone number loaded from Firestore.
