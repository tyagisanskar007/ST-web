import os
import sys

# Ensure application directory is always in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import json
import logging
import requests
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, storage
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

# Directory for local persistence fallback
DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
LOCAL_DATA_FILE = os.path.join(DATA_DIR, 'local_db.json')

def encode_firestore(data):
    fields = {}
    for k, v in data.items():
        if isinstance(v, bool):
            fields[k] = {'booleanValue': v}
        elif isinstance(v, (int, float)):
            fields[k] = {'doubleValue': float(v)}
        elif isinstance(v, str):
            fields[k] = {'stringValue': v}
        elif isinstance(v, list):
            fields[k] = {'arrayValue': {'values': [{'stringValue': str(x)} for x in v]}}
        elif isinstance(v, dict):
            fields[k] = {'mapValue': encode_firestore(v)}
    return {'fields': fields}

def decode_firestore(doc):
    if not doc or 'fields' not in doc:
        return {}
    res = {}
    for k, v in doc['fields'].items():
        if 'stringValue' in v:
            res[k] = v['stringValue']
        elif 'booleanValue' in v:
            res[k] = v['booleanValue']
        elif 'doubleValue' in v:
            res[k] = v['doubleValue']
        elif 'integerValue' in v:
            res[k] = int(v['integerValue'])
        elif 'arrayValue' in v:
            res[k] = [x.get('stringValue', '') for x in v['arrayValue'].get('values', [])]
        elif 'mapValue' in v:
            res[k] = decode_firestore(v['mapValue'])
    return res

class FirebaseManager:
    """
    Firebase Management & Firestore Data Abstraction Layer.
    Provides live Google Cloud Firebase (Admin SDK + REST API) connectivity
    with automatic data seeding and fallback local datastore engine.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.is_connected = False
        self.is_rest_mode = False
        self.db = None
        self.bucket = None
        self.project_id = os.environ.get('FIREBASE_PROJECT_ID', 'shiv-trader')
        self.api_key = os.environ.get('FIREBASE_API_KEY', 'AIzaSyB0PPldQrPlfUhdl--4cOF7FHHSrGhgGAk')
        self.storage_bucket = os.environ.get('FIREBASE_STORAGE_BUCKET', 'shiv-trader.firebasestorage.app')
        
        self._ensure_data_dir()
        self._init_firebase()
        self._seed_initial_data_if_needed()
        self._initialized = True

    def _ensure_data_dir(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        uploads_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)

    def _init_firebase(self):
        """Attempts to initialize Firebase Admin SDK or REST API."""
        try:
            if firebase_admin._apps:
                self.db = firestore.client()
                self.is_connected = True
                logger.info("Firebase Admin SDK active.")
                return

            cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH', 'serviceAccountKey.json')
            client_email = os.environ.get('FIREBASE_CLIENT_EMAIL')
            private_key = os.environ.get('FIREBASE_PRIVATE_KEY')

            cred = None
            if os.path.exists(cred_path):
                logger.info(f"Loading Firebase credentials from file: {cred_path}")
                cred = credentials.Certificate(cred_path)
            elif self.project_id and client_email and private_key:
                logger.info("Loading Firebase credentials from environment variables.")
                key_dict = {
                    "type": "service_account",
                    "project_id": self.project_id,
                    "private_key": private_key.replace('\\n', '\n'),
                    "client_email": client_email,
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
                cred = credentials.Certificate(key_dict)

            if cred:
                options = {}
                if self.storage_bucket:
                    options['storageBucket'] = self.storage_bucket
                
                firebase_admin.initialize_app(cred, options)
                self.db = firestore.client()
                self.is_connected = True
                logger.info(f"Connected to Firebase Cloud Firestore for project: {self.project_id}")
            else:
                # Check if Firestore REST API is reachable for shiv-trader
                if self.project_id and self.api_key:
                    test_url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/company/main_info?key={self.api_key}"
                    try:
                        res = requests.get(test_url, timeout=3)
                        if res.status_code in (200, 404):
                            self.is_connected = True
                            self.is_rest_mode = True
                            logger.info(f"Connected to Firebase Firestore via REST API for project: {self.project_id}")
                        else:
                            logger.info(f"Firestore API returned status {res.status_code}. Using local datastore with cloud sync.")
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Firebase initialization notice: {e}")
            self.is_connected = False

    # -------------------------------------------------------------
    # LOCAL DATASTORE ENGINE
    # -------------------------------------------------------------
    def _read_local_db(self):
        if not os.path.exists(LOCAL_DATA_FILE):
            return {}
        try:
            with open(LOCAL_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading local db: {e}")
            return {}

    def _write_local_db(self, data):
        try:
            with open(LOCAL_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error writing local db: {e}")

    # -------------------------------------------------------------
    # FIRESTORE REST API SYNC HELPERS
    # -------------------------------------------------------------
    def _firestore_rest_get(self, collection, doc_id):
        if not self.is_rest_mode:
            return None
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{collection}/{doc_id}?key={self.api_key}"
        try:
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                return decode_firestore(res.json())
        except Exception as e:
            logger.debug(f"Firestore REST get error: {e}")
        return None

    def _firestore_rest_set(self, collection, doc_id, data):
        if not self.is_rest_mode:
            return False
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{collection}/{doc_id}?key={self.api_key}"
        try:
            payload = encode_firestore(data)
            res = requests.patch(url, json=payload, timeout=4)
            return res.status_code in (200, 201)
        except Exception as e:
            logger.debug(f"Firestore REST set error: {e}")
        return False

    def _firestore_rest_delete(self, collection, doc_id):
        if not self.is_rest_mode:
            return False
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{collection}/{doc_id}?key={self.api_key}"
        try:
            res = requests.delete(url, timeout=4)
            return res.status_code in (200, 204)
        except Exception as e:
            logger.debug(f"Firestore REST delete error: {e}")
        return False

    def _firestore_rest_list(self, collection):
        """Fetch all documents in a Firestore collection via REST API."""
        if not self.is_rest_mode:
            return None
        results = []
        page_token = None
        try:
            while True:
                url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{collection}?key={self.api_key}&pageSize=100"
                if page_token:
                    url += f"&pageToken={page_token}"
                res = requests.get(url, timeout=6)
                if res.status_code != 200:
                    logger.debug(f"Firestore REST list error for {collection}: HTTP {res.status_code}")
                    return None
                data = res.json()
                for doc in data.get('documents', []):
                    decoded = decode_firestore(doc)
                    results.append(decoded)
                page_token = data.get('nextPageToken')
                if not page_token:
                    break
        except Exception as e:
            logger.debug(f"Firestore REST list exception for {collection}: {e}")
            return None
        return results

    # -------------------------------------------------------------
    # SEED DATA GENERATOR
    # -------------------------------------------------------------
    def _seed_initial_data_if_needed(self):
        local_data = self._read_local_db()
        if local_data and 'products' in local_data and len(local_data['products']) > 0:
            return

        initial_data = {
            "company": {
                "company_id": "main_info",
                "company_name": "Shiv Traders",
                "tagline": "Building Strong Foundations. Creating Better Spaces.",
                "description": "Shiv Traders is a premier manufacturer and infrastructure contractor specializing in high-grade interlocking paver blocks, industrial heavy-duty tiles, and comprehensive infrastructure execution for government, commercial, and industrial developments.",
                "phone": "+91 98290 12345",
                "whatsapp_number": "+919829012345",
                "email": "contact@shivtraders.com",
                "address": "Plot No. 45-48, RIICO Industrial Area, Phase II",
                "city": "Jaipur",
                "state": "Rajasthan",
                "pincode": "302013",
                "country": "India",
                "gst_number": "08AABCS1429K1Z5",
                "trademark_information": "Registered Trademark No. 4928172 (Class 19)",
                "business_hours": "Monday - Saturday: 8:00 AM - 7:30 PM (Sunday by Appointment)",
                "founding_year": "2018",
                "experience_years": "8+",
                "total_area_paved": "3 Million+ Sq. Ft.",
                "daily_capacity": "7,000+ Sq. Ft. / Day",
                "quality_certification": "ISO 9001:2015 & BIS IS-15658:2021 Compliant",
                "updated_at": datetime.utcnow().isoformat()
            },
            "users": {
                "admin_1": {
                    "user_id": "admin_1",
                    "email": os.environ.get('ADMIN_EMAIL', 'admin@shivtraders.com'),
                    "password_hash": generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'Admin@ShivTraders2026')),
                    "name": "Shiv Traders Administrator",
                    "role": "Super Admin",
                    "created_at": datetime.utcnow().isoformat()
                }
            },
            "products": {
                "prod-1": {
                    "product_id": "prod-1",
                    "name": "Zig-Zag Interlock Paver Block",
                    "category": "Interlock Tiles",
                    "thickness": "80mm / 60mm",
                    "grade": "M40 / M50",
                    "finish": "Shot Blasted / Smooth Vibro",
                    "dimensions": "225mm x 112mm x 80mm",
                    "compressive_strength": "45 - 55 N/mm²",
                    "description": "High-tensile interlocking design engineered for maximum inter-block load distribution. Ideal for container terminals, heavy transport yards, highways, and high-traffic public roads.",
                    "image_url": "/static/images/products/zigzag_paver.webp",
                    "gallery": [
                        "/static/images/products/zigzag_paver.webp",
                        "/static/images/products/zigzag_installed.webp"
                    ],
                    "colors": ["Grey", "Red", "Yellow", "Charcoal"],
                    "applications": ["Heavy Vehicle Terminals", "Toll Plazas", "Petrol Pumps", "Industrial Access Roads"],
                    "available": True,
                    "featured": True,
                    "created_at": "2026-01-10T10:00:00Z",
                    "updated_at": "2026-01-10T10:00:00Z"
                },
                "prod-2": {
                    "product_id": "prod-2",
                    "name": "Unipaver I-Shape Paver Block",
                    "category": "Interlock Tiles",
                    "thickness": "60mm / 80mm",
                    "grade": "M35 / M40",
                    "finish": "Vibro-Compacted Dual Layer",
                    "dimensions": "200mm x 165mm x 60/80mm",
                    "compressive_strength": "40 - 50 N/mm²",
                    "description": "Ergonomic classic I-section design offering exceptional locking friction and aesthetic symmetry for medium to heavy commercial traffic and urban street corridors.",
                    "image_url": "/static/images/products/unipaver_ishape.webp",
                    "gallery": [
                        "/static/images/products/unipaver_ishape.webp"
                    ],
                    "colors": ["Terra Cotta", "Concrete Grey", "Mustard Yellow", "Black"],
                    "applications": ["Commercial Complex Parking", "Factory Yards", "Municipal Walkways"],
                    "available": True,
                    "featured": True,
                    "created_at": "2026-01-11T10:00:00Z",
                    "updated_at": "2026-01-11T10:00:00Z"
                },
                "prod-3": {
                    "product_id": "prod-3",
                    "name": "Hexagonal Architectural Paver",
                    "category": "Paver Blocks",
                    "thickness": "60mm",
                    "grade": "M35",
                    "finish": "Reflective Micro-Finish",
                    "dimensions": "200mm Side-to-Side x 60mm",
                    "compressive_strength": "35 - 42 N/mm²",
                    "description": "Geometric luxury paving stone designed for upscale architectural landscaping, municipal parks, resort pathways, and modern luxury residential driveways.",
                    "image_url": "/static/images/products/hexagonal_paver.webp",
                    "gallery": [
                        "/static/images/products/hexagonal_paver.webp"
                    ],
                    "colors": ["Silver Grey", "Copper Red", "Tan Beige"],
                    "applications": ["Architectural Plazas", "Luxury Residences", "Walkways & Promenades"],
                    "available": True,
                    "featured": True,
                    "created_at": "2026-01-12T10:00:00Z",
                    "updated_at": "2026-01-12T10:00:00Z"
                },
                "prod-4": {
                    "product_id": "prod-4",
                    "name": "Heavy-Duty Industrial Dock Paver",
                    "category": "Heavy-Duty Industrial Pavers",
                    "thickness": "100mm / 120mm",
                    "grade": "M50 / M60",
                    "finish": "High Abrasion Resistant Top Layer",
                    "dimensions": "200mm x 100mm x 100mm",
                    "compressive_strength": "55 - 65 N/mm²",
                    "description": "Ultra-reinforced concrete paving solution engineered specifically for reach stackers, heavy axle loads, crane bays, and logistics transshipment hubs.",
                    "image_url": "/static/images/products/industrial_heavy_paver.webp",
                    "gallery": [
                        "/static/images/products/industrial_heavy_paver.webp"
                    ],
                    "colors": ["Industrial Charcoal", "Natural Basalt Grey"],
                    "applications": ["Inland Container Depots", "Heavy Steel Manufacturing Plants", "Port Terminals"],
                    "available": True,
                    "featured": True,
                    "created_at": "2026-01-13T10:00:00Z",
                    "updated_at": "2026-01-13T10:00:00Z"
                },
                "prod-5": {
                    "product_id": "prod-5",
                    "name": "Hydraulic Pressed Kerb Stone",
                    "category": "Kerb Stones",
                    "thickness": "150mm Base x 300mm Height",
                    "grade": "M30 / M35",
                    "finish": "Chamfered Edge Hydraulic Press",
                    "dimensions": "450mm x 300mm x 150mm",
                    "compressive_strength": "35 N/mm²",
                    "description": "High-density concrete road edging kerbs engineered according to CPWD and IRC highway specifications for robust edge containment and drainage channel separation.",
                    "image_url": "/static/images/products/kerb_stone.webp",
                    "gallery": [
                        "/static/images/products/kerb_stone.webp"
                    ],
                    "colors": ["Natural Grey", "Reflective Painted Stripes"],
                    "applications": ["Highway Medians", "Road Dividers", "Industrial Site Perimeters"],
                    "available": True,
                    "featured": False,
                    "created_at": "2026-01-14T10:00:00Z",
                    "updated_at": "2026-01-14T10:00:00Z"
                },
                "prod-6": {
                    "product_id": "prod-6",
                    "name": "Eco-Grid Concrete Grass Paver",
                    "category": "Grass Pavers",
                    "thickness": "80mm / 100mm",
                    "grade": "M35",
                    "finish": "Porous Grid Structure",
                    "dimensions": "400mm x 400mm x 80mm",
                    "compressive_strength": "35 - 40 N/mm²",
                    "description": "Permeable eco-friendly paving block allowing natural rainwater harvesting and vegetation growth while bearing medium vehicle loads without ground sinking.",
                    "image_url": "/static/images/products/grass_paver.webp",
                    "gallery": [
                        "/static/images/products/grass_paver.webp"
                    ],
                    "colors": ["Natural Grey"],
                    "applications": ["Eco Parking Lots", "Fire Access Roads", "Landscape Green Drives"],
                    "available": True,
                    "featured": False,
                    "created_at": "2026-01-15T10:00:00Z",
                    "updated_at": "2026-01-15T10:00:00Z"
                },
                "prod-7": {
                    "product_id": "prod-7",
                    "name": "Chequered Industrial Flooring Tile",
                    "category": "Chequered Tiles",
                    "thickness": "25mm / 30mm",
                    "grade": "M30",
                    "finish": "Diamond Grip / Anti-Skid Texture",
                    "dimensions": "300mm x 300mm x 25mm",
                    "compressive_strength": "30 - 38 N/mm²",
                    "description": "Heavy-duty anti-skid chequered tiles engineered for ramps, basements, public transit corridors, and plant work zones requiring dependable wet grip.",
                    "image_url": "/static/images/products/chequered_tile.webp",
                    "gallery": [
                        "/static/images/products/chequered_tile.webp"
                    ],
                    "colors": ["Red & Grey", "Yellow & Black", "Solid Concrete"],
                    "applications": ["Basement Parking Ramps", "Railway Platforms", "Industrial Walkways"],
                    "available": True,
                    "featured": False,
                    "created_at": "2026-01-16T10:00:00Z",
                    "updated_at": "2026-01-16T10:00:00Z"
                },
                "prod-8": {
                    "product_id": "prod-8",
                    "name": "High-Strength Concrete Cover Blocks",
                    "category": "Cover Blocks",
                    "thickness": "20mm / 25mm / 40mm / 50mm / 75mm",
                    "grade": "M50 / M60",
                    "finish": "High Density Moulded with Binding Wire Slot",
                    "dimensions": "Standard Structural Diameters",
                    "compressive_strength": "50+ N/mm²",
                    "description": "High-density concrete cover blocks ensuring precise rebar placement and long-term corrosion prevention for bridges, columns, slabs, and heavy foundations.",
                    "image_url": "/static/images/products/cover_blocks.webp",
                    "gallery": [
                        "/static/images/products/cover_blocks.webp"
                    ],
                    "colors": ["Natural Grey"],
                    "applications": ["RCC Slabs & Beams", "Heavy Foundation Footings", "Flyover Columns"],
                    "available": True,
                    "featured": False,
                    "created_at": "2026-01-17T10:00:00Z",
                    "updated_at": "2026-01-17T10:00:00Z"
                }
            },
            "projects": {
                "proj-1": {
                    "project_id": "proj-1",
                    "project_name": "Smart City Urban Corridor Pavement",
                    "category": "Street Development",
                    "location": "Jaipur Urban Boulevard Zone",
                    "area_sqft": "145,000 Sq. Ft.",
                    "completion_date": "2025-11-20",
                    "description": "Comprehensive smart street redevelopment featuring heavy-duty 80mm interlocking pavers, specialized pedestrian tactile tracks, and hydraulic kerb edging for modern urban transit.",
                    "image_url": "/static/images/projects/smart_city_street.webp",
                    "images": [
                        "/static/images/projects/smart_city_street.webp",
                        "/static/images/projects/smart_city_detail.webp"
                    ],
                    "status": "Completed",
                    "featured": True,
                    "created_at": "2025-12-01T10:00:00Z"
                },
                "proj-2": {
                    "project_id": "proj-2",
                    "project_name": "Logistics Hub Heavy-Duty Transshipment Yard",
                    "category": "Factory Construction",
                    "location": "Delhi-Mumbai Industrial Freight Corridor",
                    "area_sqft": "380,000 Sq. Ft.",
                    "completion_date": "2025-08-15",
                    "description": "Heavy-duty 100mm M50-grade industrial interlock paving installation engineered to withstand 70-ton multi-axle trailer loading and continuous forklift operations.",
                    "image_url": "/static/images/projects/logistics_yard.webp",
                    "images": [
                        "/static/images/projects/logistics_yard.webp"
                    ],
                    "status": "Completed",
                    "featured": True,
                    "created_at": "2025-09-01T10:00:00Z"
                },
                "proj-3": {
                    "project_id": "proj-3",
                    "project_name": "Multi-Level Commercial Complex Parking Arena",
                    "category": "Parking Area",
                    "location": "Central Business District",
                    "area_sqft": "92,000 Sq. Ft.",
                    "completion_date": "2026-01-05",
                    "description": "Dual-shade aesthetic unipaver block layout with integrated drainage slopes, EV charging bay demarcations, and anti-skid entrance ramps.",
                    "image_url": "/static/images/projects/commercial_parking.webp",
                    "images": [
                        "/static/images/projects/commercial_parking.webp"
                    ],
                    "status": "Completed",
                    "featured": True,
                    "created_at": "2026-01-10T10:00:00Z"
                },
                "proj-4": {
                    "project_id": "proj-4",
                    "project_name": "Regional Agro-Wholesale Market Development",
                    "category": "Market Development",
                    "location": "State Agricultural Terminal",
                    "area_sqft": "210,000 Sq. Ft.",
                    "completion_date": "2025-05-30",
                    "description": "Robust all-weather paving infrastructure designed for tractor-trailer maneuvers, market loading bays, and heavy produce truck movement.",
                    "image_url": "/static/images/projects/market_terminal.webp",
                    "images": [
                        "/static/images/projects/market_terminal.webp"
                    ],
                    "status": "Completed",
                    "featured": False,
                    "created_at": "2025-06-15T10:00:00Z"
                },
                "proj-5": {
                    "project_id": "proj-5",
                    "project_name": "National Highway Toll Plaza Rigid Interlock Paving",
                    "category": "Government Infrastructure",
                    "location": "National Highway NH-48 Section",
                    "area_sqft": "165,000 Sq. Ft.",
                    "completion_date": "2025-10-10",
                    "description": "High-durability M50 interlocking pavement executed strictly under NHAI & MoRTH guidelines to resist extreme braking shear forces at multi-lane toll collection gates.",
                    "image_url": "/static/images/projects/toll_plaza.webp",
                    "images": [
                        "/static/images/projects/toll_plaza.webp"
                    ],
                    "status": "Completed",
                    "featured": True,
                    "created_at": "2025-10-25T10:00:00Z"
                },
                "proj-6": {
                    "project_id": "proj-6",
                    "project_name": "Heavy Engineering Plant Internal Road Network",
                    "category": "Interlock Tile Installation",
                    "location": "RIICO Industrial Hub",
                    "area_sqft": "120,000 Sq. Ft.",
                    "completion_date": "2026-04-30",
                    "description": "Turnkey site excavation, WMM sub-base preparation, laser-guided sand bedding, and automated paver block laying for a heavy machinery manufacturing facility.",
                    "image_url": "/static/images/projects/industrial_roads.webp",
                    "images": [
                        "/static/images/projects/industrial_roads.webp"
                    ],
                    "status": "In Progress",
                    "featured": False,
                    "created_at": "2026-02-01T10:00:00Z"
                }
            },
            "services": {
                "serv-1": {
                    "service_id": "serv-1",
                    "title": "Turnkey Interlock Paving Contracting",
                    "category": "Infrastructure Contracting",
                    "icon": "fa-layer-group",
                    "description": "End-to-end paving contracting from ground surveys, laser leveling, sub-base compaction, to automated laying and edge kerb locking for commercial and industrial hubs.",
                    "features": ["Sub-base compaction & leveling", "High-capacity automated laying", "CPWD & IS-15658 standards compliance", "Comprehensive warranty support"],
                    "image_url": "/static/images/manufacturing/service_paving.webp"
                },
                "serv-2": {
                    "service_id": "serv-2",
                    "title": "Heavy-Duty Industrial Flooring",
                    "category": "Industrial Solutions",
                    "icon": "fa-industry",
                    "description": "Specialized pavement engineering for container freight stations, warehouse docking bays, foundry access routes, and high-axle load zones.",
                    "features": ["M50 / M60 grade heavy pavers", "Shear-resistant interlocking joints", "High point-load capacity", "Quick turnaround minimal downtime"],
                    "image_url": "/static/images/manufacturing/service_industrial.webp"
                },
                "serv-3": {
                    "service_id": "serv-3",
                    "title": "Government & Municipal Roadworks",
                    "category": "Public Infrastructure",
                    "icon": "fa-landmark",
                    "description": "Tender execution and urban redevelopment paving for smart cities, municipal corporation avenues, public parks, and highway median kerbing.",
                    "features": ["Strict PWD/CPWD/MoRTH adherence", "Certified third-party lab testing", "Large-scale daily supply capability", "Dedicated project managers"],
                    "image_url": "/static/images/manufacturing/service_government.webp"
                },
                "serv-4": {
                    "service_id": "serv-4",
                    "title": "Precision Hydraulic Paver Manufacturing",
                    "category": "Manufacturing Prowess",
                    "icon": "fa-cogs",
                    "description": "State-of-the-art automated manufacturing facility utilizing high-pressure vibro-hydraulic pressing, premium 53-grade cement, and German synthetic pigments.",
                    "features": ["7,000+ sq ft daily production capacity", "Uniform density & zero voids", "German UV-stable pigments", "In-house NABL-traceable testing lab"],
                    "image_url": "/static/images/manufacturing/plant_press.webp"
                }
            },
            "credentials": {
                "cred-1": {
                    "cred_id": "cred-1",
                    "title": "GST Registration Certificate",
                    "issuer": "Government of India - GSTIN",
                    "registration_number": "08AABCS1429K1Z5",
                    "issue_date": "2017-07-01",
                    "description": "Verified Central & State GST registration for legitimate manufacturing, supply, and works contracting.",
                    "verified": True,
                    "file_url": "/static/images/certificates/gst_certificate.webp"
                },
                "cred-2": {
                    "cred_id": "cred-2",
                    "title": "ISO 9001:2015 Quality Management System",
                    "issuer": "International Accreditation Service (IAS)",
                    "registration_number": "ISO-QMS-2023-8841",
                    "issue_date": "2023-04-12",
                    "description": "Certified quality management standard for the manufacture and supply of precast concrete pavers and civil infrastructure contracting.",
                    "verified": True,
                    "file_url": "/static/images/certificates/iso_certificate.webp"
                },
                "cred-3": {
                    "cred_id": "cred-3",
                    "title": "Registered Trademark - Class 19",
                    "issuer": "Trade Marks Registry, Govt. of India",
                    "registration_number": "TM-4928172",
                    "issue_date": "2021-03-18",
                    "description": "Exclusive statutory trademark protection for Shiv Traders® building materials and pavers.",
                    "verified": True,
                    "file_url": "/static/images/certificates/tm_certificate.webp"
                },
                "cred-4": {
                    "cred_id": "cred-4",
                    "title": "BIS & CPWD Lab Test Conformity Report",
                    "issuer": "NABL Accredited Civil Testing Laboratory",
                    "registration_number": "IS 15658:2021-TR-904",
                    "issue_date": "2025-11-15",
                    "description": "Certified compliance for compressive strength (52.4 N/mm²), water absorption (<4.2%), and abrasion resistance index.",
                    "verified": True,
                    "file_url": "/static/images/certificates/lab_report.webp"
                }
            },
            "enquiries": {
                "enq-1": {
                    "enquiry_id": "enq-1",
                    "name": "Rajesh Sharma",
                    "company": "Apex Logistics & Warehousing Ltd",
                    "phone": "+91 98290 99887",
                    "email": "r.sharma@apexlogistics.in",
                    "city": "Jaipur",
                    "project_type": "Factory / Logistics Pavement",
                    "quantity": "75,000 Sq. Ft.",
                    "message": "We require M50 grade 80mm zig-zag pavers for our new freight dispatch yard. Please provide an estimate including sub-base laying and delivery timeline.",
                    "status": "In Progress",
                    "created_at": "2026-02-20T14:30:00Z"
                },
                "enq-2": {
                    "enquiry_id": "enq-2",
                    "name": "Vikramaditya Chauhan",
                    "company": "Heritage Grand Resorts",
                    "phone": "+91 94140 11223",
                    "email": "infrastructure@heritagegrand.com",
                    "city": "Udaipur",
                    "project_type": "Resort & Architectural Paving",
                    "quantity": "30,000 Sq. Ft.",
                    "message": "Looking for premium hexagonal and grass pavers in terracotta and silver grey shades for driveway and landscaping.",
                    "status": "New",
                    "created_at": "2026-02-25T11:15:00Z"
                },
                "enq-3": {
                    "enquiry_id": "enq-3",
                    "name": "Sunil Mittal",
                    "company": "Municipal Infrastructure Consortium",
                    "phone": "+91 97840 55443",
                    "email": "smittal@mici.org",
                    "city": "Kota",
                    "project_type": "Smart City Street Development",
                    "quantity": "120,000 Sq. Ft.",
                    "message": "Tender requirement for CPWD compliant 80mm interlock pavers and hydraulic kerb stones with test batch inspection.",
                    "status": "Contacted",
                    "created_at": "2026-02-22T09:45:00Z"
                }
            }
        }

        self._write_local_db(initial_data)
        logger.info("Initialized local datastore with Shiv Traders seed data.")

        # Attempt to seed Firestore if connected
        if self.is_connected and self.db:
            try:
                comp_ref = self.db.collection('company').document('main_info')
                if not comp_ref.get().exists:
                    comp_ref.set(initial_data['company'])
                    for k, v in initial_data['products'].items():
                        self.db.collection('products').document(k).set(v)
                    for k, v in initial_data['projects'].items():
                        self.db.collection('projects').document(k).set(v)
                    for k, v in initial_data['services'].items():
                        self.db.collection('services').document(k).set(v)
                    for k, v in initial_data['credentials'].items():
                        self.db.collection('credentials').document(k).set(v)
                    for k, v in initial_data['enquiries'].items():
                        self.db.collection('enquiries').document(k).set(v)
                    for k, v in initial_data['users'].items():
                        self.db.collection('users').document(k).set(v)
                    logger.info("Successfully seeded live Firestore with initial datasets.")
            except Exception as e:
                logger.error(f"Error seeding live Firestore: {e}")

    # =============================================================
    # PRODUCTS CRUD
    # =============================================================
    def get_products(self, category=None, available_only=False):
        if self.is_connected and self.db:
            try:
                query = self.db.collection('products')
                if available_only:
                    query = query.where('available', '==', True)
                if category and category != 'All':
                    query = query.where('category', '==', category)
                docs = query.stream()
                products = [doc.to_dict() for doc in docs]
                return sorted(products, key=lambda x: x.get('created_at', ''), reverse=True)
            except Exception as e:
                logger.error(f"Firestore get_products error: {e}")

        # REST API live read
        if self.is_rest_mode:
            rest_products = self._firestore_rest_list('products')
            if rest_products is not None:
                if available_only:
                    rest_products = [p for p in rest_products if p.get('available', True)]
                if category and category != 'All':
                    rest_products = [p for p in rest_products if p.get('category') == category]
                return sorted(rest_products, key=lambda x: x.get('created_at', ''), reverse=True)

        # Local fallback
        db = self._read_local_db()
        products = list(db.get('products', {}).values())
        if available_only:
            products = [p for p in products if p.get('available', True)]
        if category and category != 'All':
            products = [p for p in products if p.get('category') == category]
        return sorted(products, key=lambda x: x.get('created_at', ''), reverse=True)

    def get_product(self, product_id):
        if self.is_connected and self.db:
            try:
                doc = self.db.collection('products').document(product_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.error(f"Firestore get_product error: {e}")

        db = self._read_local_db()
        return db.get('products', {}).get(product_id)

    def save_product(self, data, product_id=None):
        if not product_id:
            product_id = f"prod-{int(datetime.utcnow().timestamp())}"
            data['product_id'] = product_id
            data['created_at'] = datetime.utcnow().isoformat()
        data['updated_at'] = datetime.utcnow().isoformat()

        if self.is_connected and self.db:
            try:
                self.db.collection('products').document(product_id).set(data, merge=True)
            except Exception as e:
                logger.error(f"Firestore save_product error: {e}")

        self._firestore_rest_set('products', product_id, data)

        db = self._read_local_db()
        if 'products' not in db:
            db['products'] = {}
        db['products'][product_id] = data
        self._write_local_db(db)
        return product_id

    def delete_product(self, product_id):
        if self.is_connected and self.db:
            try:
                self.db.collection('products').document(product_id).delete()
            except Exception as e:
                logger.error(f"Firestore delete_product error: {e}")

        self._firestore_rest_delete('products', product_id)

        db = self._read_local_db()
        if 'products' in db and product_id in db['products']:
            del db['products'][product_id]
            self._write_local_db(db)
            return True
        return False

    # =============================================================
    # PROJECTS CRUD
    # =============================================================
    def get_projects(self, category=None):
        if self.is_connected and self.db:
            try:
                query = self.db.collection('projects')
                if category and category != 'All':
                    query = query.where('category', '==', category)
                docs = query.stream()
                projects = [doc.to_dict() for doc in docs]
                return sorted(projects, key=lambda x: x.get('created_at', ''), reverse=True)
            except Exception as e:
                logger.error(f"Firestore get_projects error: {e}")

        if self.is_rest_mode:
            rest_projects = self._firestore_rest_list('projects')
            if rest_projects is not None:
                if category and category != 'All':
                    rest_projects = [p for p in rest_projects if p.get('category') == category]
                return sorted(rest_projects, key=lambda x: x.get('created_at', ''), reverse=True)

        db = self._read_local_db()
        projects = list(db.get('projects', {}).values())
        if category and category != 'All':
            projects = [p for p in projects if p.get('category') == category]
        return sorted(projects, key=lambda x: x.get('created_at', ''), reverse=True)

    def get_project(self, project_id):
        if self.is_connected and self.db:
            try:
                doc = self.db.collection('projects').document(project_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.error(f"Firestore get_project error: {e}")

        db = self._read_local_db()
        return db.get('projects', {}).get(project_id)

    def save_project(self, data, project_id=None):
        if not project_id:
            project_id = f"proj-{int(datetime.utcnow().timestamp())}"
            data['project_id'] = project_id
            data['created_at'] = datetime.utcnow().isoformat()

        if self.is_connected and self.db:
            try:
                self.db.collection('projects').document(project_id).set(data, merge=True)
            except Exception as e:
                logger.error(f"Firestore save_project error: {e}")

        self._firestore_rest_set('projects', project_id, data)

        db = self._read_local_db()
        if 'projects' not in db:
            db['projects'] = {}
        db['projects'][project_id] = data
        self._write_local_db(db)
        return project_id

    def delete_project(self, project_id):
        if self.is_connected and self.db:
            try:
                self.db.collection('projects').document(project_id).delete()
            except Exception as e:
                logger.error(f"Firestore delete_project error: {e}")

        self._firestore_rest_delete('projects', project_id)

        db = self._read_local_db()
        if 'projects' in db and project_id in db['projects']:
            del db['projects'][project_id]
            self._write_local_db(db)
            return True
        return False

    # =============================================================
    # SERVICES CRUD
    # =============================================================
    def get_services(self):
        if self.is_connected and self.db:
            try:
                docs = self.db.collection('services').stream()
                return [doc.to_dict() for doc in docs]
            except Exception as e:
                logger.error(f"Firestore get_services error: {e}")

        if self.is_rest_mode:
            rest_services = self._firestore_rest_list('services')
            if rest_services is not None:
                return rest_services

        db = self._read_local_db()
        return list(db.get('services', {}).values())

    def get_service(self, service_id):
        if self.is_connected and self.db:
            try:
                doc = self.db.collection('services').document(service_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.error(f"Firestore get_service error: {e}")

        db = self._read_local_db()
        return db.get('services', {}).get(service_id)

    def save_service(self, data, service_id=None):
        if not service_id:
            service_id = f"serv-{int(datetime.utcnow().timestamp())}"
            data['service_id'] = service_id

        if self.is_connected and self.db:
            try:
                self.db.collection('services').document(service_id).set(data, merge=True)
            except Exception as e:
                logger.error(f"Firestore save_service error: {e}")

        self._firestore_rest_set('services', service_id, data)

        db = self._read_local_db()
        if 'services' not in db:
            db['services'] = {}
        db['services'][service_id] = data
        self._write_local_db(db)
        return service_id

    def delete_service(self, service_id):
        if self.is_connected and self.db:
            try:
                self.db.collection('services').document(service_id).delete()
            except Exception as e:
                logger.error(f"Firestore delete_service error: {e}")

        self._firestore_rest_delete('services', service_id)

        db = self._read_local_db()
        if 'services' in db and service_id in db['services']:
            del db['services'][service_id]
            self._write_local_db(db)
            return True
        return False

    # =============================================================
    # ENQUIRIES CRUD
    # =============================================================
    def get_enquiries(self, status_filter=None, search=None):
        if self.is_connected and self.db:
            try:
                query = self.db.collection('enquiries')
                if status_filter and status_filter != 'All':
                    query = query.where('status', '==', status_filter)
                docs = query.stream()
                enquiries = [doc.to_dict() for doc in docs]
                if search:
                    s = search.lower()
                    enquiries = [e for e in enquiries if s in e.get('name', '').lower() or s in e.get('email', '').lower() or s in e.get('phone', '').lower() or s in e.get('company', '').lower()]
                return sorted(enquiries, key=lambda x: x.get('created_at', ''), reverse=True)
            except Exception as e:
                logger.error(f"Firestore get_enquiries error: {e}")

        if self.is_rest_mode:
            rest_enquiries = self._firestore_rest_list('enquiries')
            if rest_enquiries is not None:
                if status_filter and status_filter != 'All':
                    rest_enquiries = [e for e in rest_enquiries if e.get('status') == status_filter]
                if search:
                    s = search.lower()
                    rest_enquiries = [e for e in rest_enquiries if s in e.get('name', '').lower() or s in e.get('email', '').lower() or s in e.get('phone', '').lower() or s in e.get('company', '').lower()]
                return sorted(rest_enquiries, key=lambda x: x.get('created_at', ''), reverse=True)

        db = self._read_local_db()
        enquiries = list(db.get('enquiries', {}).values())
        if status_filter and status_filter != 'All':
            enquiries = [e for e in enquiries if e.get('status') == status_filter]
        if search:
            s = search.lower()
            enquiries = [e for e in enquiries if s in e.get('name', '').lower() or s in e.get('email', '').lower() or s in e.get('phone', '').lower() or s in e.get('company', '').lower()]
        return sorted(enquiries, key=lambda x: x.get('created_at', ''), reverse=True)

    def get_enquiry(self, enquiry_id):
        if self.is_connected and self.db:
            try:
                doc = self.db.collection('enquiries').document(enquiry_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.error(f"Firestore get_enquiry error: {e}")

        db = self._read_local_db()
        return db.get('enquiries', {}).get(enquiry_id)

    def create_enquiry(self, data):
        enquiry_id = f"enq-{int(datetime.utcnow().timestamp())}"
        data['enquiry_id'] = enquiry_id
        if 'status' not in data:
            data['status'] = 'New'
        data['created_at'] = datetime.utcnow().isoformat()

        if self.is_connected and self.db:
            try:
                self.db.collection('enquiries').document(enquiry_id).set(data)
            except Exception as e:
                logger.error(f"Firestore create_enquiry error: {e}")

        self._firestore_rest_set('enquiries', enquiry_id, data)

        db = self._read_local_db()
        if 'enquiries' not in db:
            db['enquiries'] = {}
        db['enquiries'][enquiry_id] = data
        self._write_local_db(db)
        return enquiry_id

    def update_enquiry_status(self, enquiry_id, status):
        valid_statuses = ['New', 'Contacted', 'In Progress', 'Completed', 'Cancelled']
        if status not in valid_statuses:
            return False

        if self.is_connected and self.db:
            try:
                self.db.collection('enquiries').document(enquiry_id).update({'status': status, 'updated_at': datetime.utcnow().isoformat()})
            except Exception as e:
                logger.error(f"Firestore update_enquiry_status error: {e}")

        db = self._read_local_db()
        if 'enquiries' in db and enquiry_id in db['enquiries']:
            db['enquiries'][enquiry_id]['status'] = status
            db['enquiries'][enquiry_id]['updated_at'] = datetime.utcnow().isoformat()
            self._write_local_db(db)
            self._firestore_rest_set('enquiries', enquiry_id, db['enquiries'][enquiry_id])
            return True
        return False

    def delete_enquiry(self, enquiry_id):
        if self.is_connected and self.db:
            try:
                self.db.collection('enquiries').document(enquiry_id).delete()
            except Exception as e:
                logger.error(f"Firestore delete_enquiry error: {e}")

        self._firestore_rest_delete('enquiries', enquiry_id)

        db = self._read_local_db()
        if 'enquiries' in db and enquiry_id in db['enquiries']:
            del db['enquiries'][enquiry_id]
            self._write_local_db(db)
            return True
        return False

    # =============================================================
    # COMPANY INFORMATION & CREDENTIALS
    # =============================================================
    def get_company_info(self):
        if self.is_connected and self.db:
            try:
                doc = self.db.collection('company').document('main_info').get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.error(f"Firestore get_company_info error: {e}")

        if self.is_rest_mode:
            rest_company = self._firestore_rest_get('company', 'main_info')
            if rest_company:
                return rest_company

        db = self._read_local_db()
        return db.get('company', {})

    def save_company_info(self, data):
        data['company_id'] = 'main_info'
        data['updated_at'] = datetime.utcnow().isoformat()

        if self.is_connected and self.db:
            try:
                self.db.collection('company').document('main_info').set(data, merge=True)
            except Exception as e:
                logger.error(f"Firestore save_company_info error: {e}")

        self._firestore_rest_set('company', 'main_info', data)

        db = self._read_local_db()
        db['company'] = data
        self._write_local_db(db)
        return True

    def get_credentials(self):
        if self.is_connected and self.db:
            try:
                docs = self.db.collection('credentials').stream()
                return [doc.to_dict() for doc in docs]
            except Exception as e:
                logger.error(f"Firestore get_credentials error: {e}")

        if self.is_rest_mode:
            rest_creds = self._firestore_rest_list('credentials')
            if rest_creds is not None:
                return rest_creds

        db = self._read_local_db()
        return list(db.get('credentials', {}).values())

    def save_credential(self, data, cred_id=None):
        if not cred_id:
            cred_id = f"cred-{int(datetime.utcnow().timestamp())}"
            data['cred_id'] = cred_id

        if self.is_connected and self.db:
            try:
                self.db.collection('credentials').document(cred_id).set(data, merge=True)
            except Exception as e:
                logger.error(f"Firestore save_credential error: {e}")

        self._firestore_rest_set('credentials', cred_id, data)

        db = self._read_local_db()
        if 'credentials' not in db:
            db['credentials'] = {}
        db['credentials'][cred_id] = data
        self._write_local_db(db)
        return cred_id

    def delete_credential(self, cred_id):
        if self.is_connected and self.db:
            try:
                self.db.collection('credentials').document(cred_id).delete()
            except Exception as e:
                logger.error(f"Firestore delete_credential error: {e}")

        self._firestore_rest_delete('credentials', cred_id)

        db = self._read_local_db()
        if 'credentials' in db and cred_id in db['credentials']:
            del db['credentials'][cred_id]
            self._write_local_db(db)
            return True
        return False

    # =============================================================
    # ADMIN USER AUTHENTICATION
    # =============================================================
    def get_user_by_email(self, email):
        if self.is_connected and self.db:
            try:
                docs = self.db.collection('users').where('email', '==', email).limit(1).stream()
                for doc in docs:
                    return doc.to_dict()
            except Exception as e:
                logger.error(f"Firestore get_user_by_email error: {e}")

        db = self._read_local_db()
        users = db.get('users', {})
        for u in users.values():
            if u.get('email', '').lower() == email.lower():
                return u
        return None

    def save_user(self, data, user_id=None):
        if not user_id:
            user_id = f"user-{int(datetime.utcnow().timestamp())}"
            data['user_id'] = user_id
            data['created_at'] = datetime.utcnow().isoformat()

        if self.is_connected and self.db:
            try:
                self.db.collection('users').document(user_id).set(data, merge=True)
            except Exception as e:
                logger.error(f"Firestore save_user error: {e}")

        self._firestore_rest_set('users', user_id, data)

        db = self._read_local_db()
        if 'users' not in db:
            db['users'] = {}
        db['users'][user_id] = data
        self._write_local_db(db)
        return user_id

    # =============================================================
    # STATISTICS
    # =============================================================
    def get_statistics(self):
        products = self.get_products()
        projects = self.get_projects()
        enquiries = self.get_enquiries()

        new_enquiries = [e for e in enquiries if e.get('status') == 'New']
        in_progress_enquiries = [e for e in enquiries if e.get('status') == 'In Progress']
        completed_enquiries = [e for e in enquiries if e.get('status') == 'Completed']

        return {
            'total_products': len(products),
            'total_projects': len(projects),
            'new_enquiries': len(new_enquiries),
            'in_progress_enquiries': len(in_progress_enquiries),
            'completed_enquiries': len(completed_enquiries),
            'total_enquiries': len(enquiries),
            'firebase_connected': self.is_connected
        }

# Singleton instance
firebase_db = FirebaseManager()
