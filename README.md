# Shiv Traders — Manufacturing & Infrastructure Website

A professional business website for **Shiv Traders**, a premier manufacturer of heavy-duty interlocking paver blocks and specialized infrastructure contractor based in Rajasthan, India.

## 🌐 Live Features

- **Public Website** — Products, Projects, Services, Manufacturing, Government Tenders, Credentials
- **Admin Portal** — Full CMS to manage products, projects, enquiries, company info
- **Firebase Integration** — Live Firestore database + Analytics
- **Enquiry System** — Customer leads saved directly to Firestore

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + Flask |
| Database | Firebase Firestore (+ local JSON fallback) |
| Frontend | HTML5, CSS3, Vanilla JS |
| Icons | Font Awesome 6 |
| Image Optimization | Pillow (WebP conversion) |
| Rate Limiting | Flask-Limiter |

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install flask flask-limiter pillow werkzeug requests
```

### 2. Run the server
```bash
python app.py
```

### 3. Open in browser
- **Website:** http://127.0.0.1:5000
- **Admin Portal:** http://127.0.0.1:5000/admin/login

## 📁 Project Structure

```
web1/
├── app.py                  # Main Flask application
├── config.py               # App configuration
├── firebase_config.py      # Firebase Firestore integration
├── templates/
│   ├── base.html           # Base layout (navbar, footer)
│   ├── index.html          # Homepage
│   ├── about.html          # About Us
│   ├── products.html       # Products catalog
│   ├── manufacturing.html  # Manufacturing plant
│   ├── services.html       # Services
│   ├── projects.html       # Projects portfolio
│   ├── government.html     # Government tenders
│   ├── credentials.html    # Certifications
│   ├── contact.html        # Contact / Quote
│   └── admin/              # Admin portal templates
├── static/
│   ├── css/
│   │   ├── style.css       # Public website styles (White & Red theme)
│   │   └── admin.css       # Admin portal styles
│   ├── js/
│   │   └── main.js         # Frontend scripts
│   └── images/             # Static images
├── data/                   # Local JSON database (gitignored)
├── tests/
│   └── test_app.py         # Automated test suite
└── scripts/
    └── launch.py           # Smart background launcher
```

## 🔑 Firebase Setup

This project uses **Firebase Firestore** for live data storage.

1. Create a Firebase project at https://console.firebase.google.com
2. Enable **Firestore Database**
3. Add your Firebase config to `config.py`

## 📊 Company Stats

- **Founded:** 2018
- **Experience:** 8+ Years
- **Daily Capacity:** 7,000+ Sq. Ft. / Day
- **Total Area Paved:** 3 Million+ Sq. Ft.
- **Certifications:** ISO 9001:2015 & BIS IS-15658 Compliant

## 📄 License

© 2026 Shiv Traders. All Rights Reserved.
