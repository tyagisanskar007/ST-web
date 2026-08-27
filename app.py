import os
import sys

# Ensure application directory is always in Python module search path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import re
import uuid
import logging
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_file, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from PIL import Image
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from firebase_config import firebase_db

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask Application
app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[Config.RATELIMIT_DEFAULT],
    storage_uri=Config.RATELIMIT_STORAGE_URI
)

# -------------------------------------------------------------
# AUTHENTICATION DECORATOR & HELPERS
# -------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please log in to access the administrator portal.', 'error')
            return redirect(url_for('admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def save_and_optimize_image(file, subfolder='products', max_width=1200):
    """
    Saves and optimizes uploaded images into WebP format for fast delivery.
    """
    if not file or file.filename == '':
        return None

    filename = secure_filename(file.filename)
    name, _ = os.path.splitext(filename)
    unique_name = f"{name}_{uuid.uuid4().hex[:8]}.webp"
    
    target_dir = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, unique_name)

    try:
        image = Image.open(file)
        # Convert RGBA/P to RGB if needed for saving
        if image.mode in ('RGBA', 'LA'):
            # Keep alpha for WebP
            pass
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        # Resize if larger than max_width maintaining aspect ratio
        if image.width > max_width:
            ratio = max_width / float(image.width)
            new_height = int(float(image.height) * float(ratio))
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

        image.save(file_path, 'WEBP', quality=85, optimize=True)
        return f"/static/uploads/{subfolder}/{unique_name}"
    except Exception as e:
        logger.error(f"Error optimizing image: {e}")
        # Fallback to direct save
        fallback_path = os.path.join(target_dir, filename)
        file.seek(0)
        file.save(fallback_path)
        return f"/static/uploads/{subfolder}/{filename}"

# Context processor to make company info and statistics available to all templates
@app.context_processor
def inject_global_data():
    company = firebase_db.get_company_info()
    stats = firebase_db.get_statistics()
    return {
        'company': company,
        'stats': stats,
        'firebase_connected': firebase_db.is_connected
    }

# -------------------------------------------------------------
# PUBLIC WEBSITE ROUTES
# -------------------------------------------------------------

@app.route('/')
def index():
    products = firebase_db.get_products(available_only=True)
    projects = firebase_db.get_projects()
    services = firebase_db.get_services()
    return render_template(
        'index.html',
        active_page='home',
        products=products,
        projects=projects,
        services=services
    )

@app.route('/about')
def about():
    return render_template('about.html', active_page='about')

@app.route('/products')
def products():
    category = request.args.get('cat', 'All')
    all_products = firebase_db.get_products(category=category if category != 'All' else None)
    return render_template(
        'products.html',
        active_page='products',
        products=all_products,
        current_category=category
    )

@app.route('/products/<product_id>')
def product_details(product_id):
    product = firebase_db.get_product(product_id)
    if not product:
        abort(404)
    
    # Fetch related products in the same category
    all_cat_products = firebase_db.get_products(category=product.get('category'))
    related = [p for p in all_cat_products if p.get('product_id') != product_id]
    
    return render_template(
        'product_details.html',
        active_page='products',
        product=product,
        related_products=related
    )

@app.route('/manufacturing')
def manufacturing():
    return render_template('manufacturing.html', active_page='manufacturing')

@app.route('/services')
def services():
    all_services = firebase_db.get_services()
    return render_template(
        'services.html',
        active_page='services',
        services=all_services
    )

@app.route('/projects')
def projects():
    category = request.args.get('cat', 'All')
    all_projects = firebase_db.get_projects(category=category if category != 'All' else None)
    return render_template(
        'projects.html',
        active_page='projects',
        projects=all_projects,
        current_category=category
    )

@app.route('/projects/<project_id>')
def project_details(project_id):
    project = firebase_db.get_project(project_id)
    if not project:
        abort(404)
    return render_template(
        'project_details.html',
        active_page='projects',
        project=project
    )

@app.route('/government')
def government():
    return render_template('government.html', active_page='government')

@app.route('/credentials')
def credentials():
    creds = firebase_db.get_credentials()
    return render_template(
        'credentials.html',
        active_page='credentials',
        credentials=creds
    )

@app.route('/contact')
def contact():
    selected_product = request.args.get('product', '')
    return render_template(
        'contact.html',
        active_page='contact',
        selected_product=selected_product
    )

# -------------------------------------------------------------
# API: CUSTOMER ENQUIRY SUBMISSION
# -------------------------------------------------------------
@app.route('/api/enquiry', methods=['POST'])
@limiter.limit("10 per minute")
def api_submit_enquiry():
    data = request.get_json(silent=True) or request.form.to_dict()

    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    city = data.get('city', '').strip()
    company_name = data.get('company', '').strip()
    project_type = data.get('project_type', 'General Inquiry').strip()
    quantity = data.get('quantity', '').strip()
    message = data.get('message', '').strip()

    # Form Validation
    if not name or not phone or not city:
        return jsonify({
            'success': False,
            'error': 'Please provide your name, contact phone number, and site location.'
        }), 400

    enquiry_data = {
        'name': name,
        'phone': phone,
        'email': email,
        'city': city,
        'company': company_name,
        'project_type': project_type,
        'quantity': quantity,
        'message': message,
        'status': 'New',
        'created_at': datetime.utcnow().isoformat()
    }

    try:
        enquiry_id = firebase_db.create_enquiry(enquiry_data)
        logger.info(f"New enquiry recorded in Firestore: {enquiry_id} from {name}")
        return jsonify({
            'success': True,
            'message': 'Thank you for contacting Shiv Traders. Our engineering team will get in touch with you shortly.',
            'enquiry_id': enquiry_id
        }), 201
    except Exception as e:
        logger.error(f"Error submitting enquiry: {e}")
        return jsonify({
            'success': False,
            'error': 'An internal error occurred. Please call or contact us via WhatsApp directly.'
        }), 500

# -------------------------------------------------------------
# ADMIN AUTHENTICATION
# -------------------------------------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("15 per minute")
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        user = firebase_db.get_user_by_email(email)
        if user and check_password_hash(user.get('password_hash', ''), password):
            session['admin_logged_in'] = True
            session['admin_id'] = user.get('user_id')
            session['admin_email'] = user.get('email')
            session['admin_name'] = user.get('name', 'Administrator')
            flash('Welcome to the Shiv Traders Management Hub.', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('admin_dashboard'))
        else:
            flash('Invalid administrator credentials. Please try again.', 'error')

    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('You have been securely logged out.', 'info')
    return redirect(url_for('admin_login'))

# -------------------------------------------------------------
# ADMIN DASHBOARD & CRUD
# -------------------------------------------------------------
@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    recent_enquiries = firebase_db.get_enquiries()[:8]
    return render_template(
        'admin/dashboard.html',
        active_admin_page='dashboard',
        recent_enquiries=recent_enquiries
    )

# --- Products CRUD ---
@app.route('/admin/products')
@admin_required
def admin_products():
    all_products = firebase_db.get_products()
    return render_template(
        'admin/products.html',
        active_admin_page='products',
        products=all_products
    )

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', 'Interlock Tiles').strip()
        thickness = request.form.get('thickness', '').strip()
        grade = request.form.get('grade', '').strip()
        compressive_strength = request.form.get('compressive_strength', '').strip()
        dimensions = request.form.get('dimensions', '').strip()
        finish = request.form.get('finish', '').strip()
        description = request.form.get('description', '').strip()
        available = bool(request.form.get('available'))
        featured = bool(request.form.get('featured'))

        colors = [c.strip() for c in request.form.get('colors', '').split(',') if c.strip()]
        applications = [a.strip() for a in request.form.get('applications', '').split(',') if a.strip()]

        image_file = request.files.get('image')
        image_url = save_and_optimize_image(image_file, subfolder='products') or '/static/images/products/zigzag_paver.webp'

        gallery_files = request.files.getlist('gallery')
        gallery = [image_url]
        for gf in gallery_files:
            g_url = save_and_optimize_image(gf, subfolder='products')
            if g_url:
                gallery.append(g_url)

        product_data = {
            'name': name,
            'category': category,
            'thickness': thickness,
            'grade': grade,
            'compressive_strength': compressive_strength,
            'dimensions': dimensions,
            'finish': finish,
            'description': description,
            'image_url': image_url,
            'gallery': gallery,
            'colors': colors,
            'applications': applications,
            'available': available,
            'featured': featured
        }

        firebase_db.save_product(product_data)
        flash(f'Product "{name}" successfully added to Firestore.', 'success')
        return redirect(url_for('admin_products'))

    return render_template('admin/add_product.html', active_admin_page='products')

@app.route('/admin/products/edit/<product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    product = firebase_db.get_product(product_id)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('admin_products'))

    if request.method == 'POST':
        product['name'] = request.form.get('name', '').strip()
        product['category'] = request.form.get('category', 'Interlock Tiles').strip()
        product['thickness'] = request.form.get('thickness', '').strip()
        product['grade'] = request.form.get('grade', '').strip()
        product['compressive_strength'] = request.form.get('compressive_strength', '').strip()
        product['dimensions'] = request.form.get('dimensions', '').strip()
        product['finish'] = request.form.get('finish', '').strip()
        product['description'] = request.form.get('description', '').strip()
        product['available'] = bool(request.form.get('available'))
        product['featured'] = bool(request.form.get('featured'))

        product['colors'] = [c.strip() for c in request.form.get('colors', '').split(',') if c.strip()]
        product['applications'] = [a.strip() for a in request.form.get('applications', '').split(',') if a.strip()]

        image_file = request.files.get('image')
        if image_file and image_file.filename != '':
            new_img = save_and_optimize_image(image_file, subfolder='products')
            if new_img:
                product['image_url'] = new_img

        gallery_files = request.files.getlist('gallery')
        if 'gallery' not in product:
            product['gallery'] = [product.get('image_url')]
        for gf in gallery_files:
            g_url = save_and_optimize_image(gf, subfolder='products')
            if g_url:
                product['gallery'].append(g_url)

        firebase_db.save_product(product, product_id=product_id)
        flash(f'Product "{product["name"]}" updated in Firestore.', 'success')
        return redirect(url_for('admin_products'))

    return render_template('admin/edit_product.html', active_admin_page='products', product=product)

@app.route('/admin/products/delete/<product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    firebase_db.delete_product(product_id)
    flash('Product deleted successfully.', 'success')
    return redirect(url_for('admin_products'))

# --- Projects CRUD ---
@app.route('/admin/projects')
@admin_required
def admin_projects():
    all_projects = firebase_db.get_projects()
    return render_template(
        'admin/projects.html',
        active_admin_page='projects',
        projects=all_projects
    )

@app.route('/admin/projects/add', methods=['GET', 'POST'])
@admin_required
def admin_add_project():
    if request.method == 'POST':
        project_name = request.form.get('project_name', '').strip()
        category = request.form.get('category', 'Street Development').strip()
        location = request.form.get('location', '').strip()
        area_sqft = request.form.get('area_sqft', '').strip()
        completion_date = request.form.get('completion_date', '').strip()
        status = request.form.get('status', 'Completed').strip()
        description = request.form.get('description', '').strip()
        featured = bool(request.form.get('featured'))

        image_file = request.files.get('image')
        image_url = save_and_optimize_image(image_file, subfolder='projects') or '/static/images/projects/smart_city_street.webp'

        more_images = request.files.getlist('images')
        images = [image_url]
        for mf in more_images:
            m_url = save_and_optimize_image(mf, subfolder='projects')
            if m_url:
                images.append(m_url)

        project_data = {
            'project_name': project_name,
            'category': category,
            'location': location,
            'area_sqft': area_sqft,
            'completion_date': completion_date,
            'status': status,
            'description': description,
            'image_url': image_url,
            'images': images,
            'featured': featured
        }

        firebase_db.save_project(project_data)
        flash(f'Project "{project_name}" saved to Firestore.', 'success')
        return redirect(url_for('admin_projects'))

    return render_template('admin/add_project.html', active_admin_page='projects')

@app.route('/admin/projects/edit/<project_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_project(project_id):
    project = firebase_db.get_project(project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('admin_projects'))

    if request.method == 'POST':
        project['project_name'] = request.form.get('project_name', '').strip()
        project['category'] = request.form.get('category', 'Street Development').strip()
        project['location'] = request.form.get('location', '').strip()
        project['area_sqft'] = request.form.get('area_sqft', '').strip()
        project['completion_date'] = request.form.get('completion_date', '').strip()
        project['status'] = request.form.get('status', 'Completed').strip()
        project['description'] = request.form.get('description', '').strip()
        project['featured'] = bool(request.form.get('featured'))

        image_file = request.files.get('image')
        if image_file and image_file.filename != '':
            new_img = save_and_optimize_image(image_file, subfolder='projects')
            if new_img:
                project['image_url'] = new_img

        more_images = request.files.getlist('images')
        if 'images' not in project:
            project['images'] = [project.get('image_url')]
        for mf in more_images:
            m_url = save_and_optimize_image(mf, subfolder='projects')
            if m_url:
                project['images'].append(m_url)

        firebase_db.save_project(project, project_id=project_id)
        flash(f'Project "{project["project_name"]}" updated.', 'success')
        return redirect(url_for('admin_projects'))

    return render_template('admin/edit_project.html', active_admin_page='projects', project=project)

@app.route('/admin/projects/delete/<project_id>', methods=['POST'])
@admin_required
def admin_delete_project(project_id):
    firebase_db.delete_project(project_id)
    flash('Project deleted successfully.', 'success')
    return redirect(url_for('admin_projects'))

# --- Services CRUD ---
@app.route('/admin/services')
@admin_required
def admin_services():
    all_services = firebase_db.get_services()
    return render_template('admin/services.html', active_admin_page='services', services=all_services)

@app.route('/admin/services/add', methods=['GET', 'POST'])
@admin_required
def admin_add_service():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        icon = request.form.get('icon', 'fa-layer-group').strip()
        description = request.form.get('description', '').strip()
        features = [f.strip() for f in request.form.get('features', '').splitlines() if f.strip()]

        service_data = {
            'title': title,
            'category': category,
            'icon': icon,
            'description': description,
            'features': features
        }
        firebase_db.save_service(service_data)
        flash(f'Service "{title}" added.', 'success')
        return redirect(url_for('admin_services'))

    return render_template('admin/add_service.html', active_admin_page='services')

@app.route('/admin/services/edit/<service_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_service(service_id):
    service = firebase_db.get_service(service_id)
    if not service:
        flash('Service not found.', 'error')
        return redirect(url_for('admin_services'))

    if request.method == 'POST':
        service['title'] = request.form.get('title', '').strip()
        service['category'] = request.form.get('category', '').strip()
        service['icon'] = request.form.get('icon', 'fa-layer-group').strip()
        service['description'] = request.form.get('description', '').strip()
        service['features'] = [f.strip() for f in request.form.get('features', '').splitlines() if f.strip()]

        firebase_db.save_service(service, service_id=service_id)
        flash(f'Service "{service["title"]}" updated.', 'success')
        return redirect(url_for('admin_services'))

    return render_template('admin/edit_service.html', active_admin_page='services', service=service)

@app.route('/admin/services/delete/<service_id>', methods=['POST'])
@admin_required
def admin_delete_service(service_id):
    firebase_db.delete_service(service_id)
    flash('Service deleted successfully.', 'success')
    return redirect(url_for('admin_services'))

# --- Enquiries Management ---
@app.route('/admin/enquiries')
@admin_required
def admin_enquiries():
    status_filter = request.args.get('status', 'All')
    all_enqs = firebase_db.get_enquiries()
    
    # Compute counts per status
    status_counts = {}
    for e in all_enqs:
        st = e.get('status', 'New')
        status_counts[st] = status_counts.get(st, 0) + 1

    filtered_enqs = all_enqs
    if status_filter and status_filter != 'All':
        filtered_enqs = [e for e in all_enqs if e.get('status') == status_filter]

    return render_template(
        'admin/enquiries.html',
        active_admin_page='enquiries',
        enquiries=filtered_enqs,
        current_status=status_filter,
        status_counts=status_counts,
        all_count=len(all_enqs)
    )

@app.route('/admin/enquiries/<enquiry_id>')
@admin_required
def admin_enquiry_details(enquiry_id):
    enquiry = firebase_db.get_enquiry(enquiry_id)
    if not enquiry:
        flash('Enquiry not found.', 'error')
        return redirect(url_for('admin_enquiries'))
    return render_template('admin/enquiry_details.html', active_admin_page='enquiries', enquiry=enquiry)

@app.route('/admin/api/enquiries/<enquiry_id>/status', methods=['POST'])
@admin_required
def admin_update_enquiry_status_ajax(enquiry_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    if not new_status:
        return jsonify({'success': False, 'error': 'Status is required'}), 400

    updated = firebase_db.update_enquiry_status(enquiry_id, new_status)
    if updated:
        return jsonify({'success': True, 'message': f'Status updated to {new_status}'})
    return jsonify({'success': False, 'error': 'Invalid status'}), 400

@app.route('/admin/enquiries/<enquiry_id>/status', methods=['POST'])
@admin_required
def admin_update_enquiry_status_form(enquiry_id):
    new_status = request.form.get('status')
    if new_status:
        firebase_db.update_enquiry_status(enquiry_id, new_status)
        flash(f'Status updated to {new_status}.', 'success')
    return redirect(url_for('admin_enquiry_details', enquiry_id=enquiry_id))

@app.route('/admin/enquiries/delete/<enquiry_id>', methods=['POST'])
@admin_required
def admin_delete_enquiry(enquiry_id):
    firebase_db.delete_enquiry(enquiry_id)
    flash('Enquiry deleted.', 'success')
    return redirect(url_for('admin_enquiries'))

# --- Company Information Settings ---
@app.route('/admin/company', methods=['GET', 'POST'])
@admin_required
def admin_company():
    current_info = firebase_db.get_company_info()
    if request.method == 'POST':
        updated_info = {
            'company_name': request.form.get('company_name', '').strip(),
            'tagline': request.form.get('tagline', '').strip(),
            'description': request.form.get('description', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'whatsapp_number': request.form.get('whatsapp_number', '').strip(),
            'email': request.form.get('email', '').strip(),
            'business_hours': request.form.get('business_hours', '').strip(),
            'address': request.form.get('address', '').strip(),
            'city': request.form.get('city', '').strip(),
            'state': request.form.get('state', '').strip(),
            'pincode': request.form.get('pincode', '').strip(),
            'gst_number': request.form.get('gst_number', '').strip(),
            'trademark_information': request.form.get('trademark_information', '').strip(),
            'daily_capacity': request.form.get('daily_capacity', '').strip(),
            'total_area_paved': request.form.get('total_area_paved', '').strip(),
            'quality_certification': current_info.get('quality_certification', 'ISO 9001:2015 & BIS IS-15658 Compliant'),
            'experience_years': current_info.get('experience_years', '14+'),
            'founding_year': current_info.get('founding_year', '2012')
        }
        firebase_db.save_company_info(updated_info)
        flash('Company profile successfully synced to Firestore.', 'success')
        return redirect(url_for('admin_company'))

    return render_template('admin/company.html', active_admin_page='company', company=current_info)

# --- Credentials Management ---
@app.route('/admin/credentials')
@admin_required
def admin_credentials():
    creds = firebase_db.get_credentials()
    return render_template('admin/credentials.html', active_admin_page='credentials', credentials=creds)

@app.route('/admin/credentials/add', methods=['POST'])
@admin_required
def admin_add_credential():
    title = request.form.get('title', '').strip()
    registration_number = request.form.get('registration_number', '').strip()
    issuer = request.form.get('issuer', '').strip()
    issue_date = request.form.get('issue_date', '').strip()
    description = request.form.get('description', '').strip()

    file = request.files.get('file')
    file_url = save_and_optimize_image(file, subfolder='certificates') or '/static/images/certificates/gst_certificate.webp'

    cred_data = {
        'title': title,
        'registration_number': registration_number,
        'issuer': issuer,
        'issue_date': issue_date,
        'description': description,
        'verified': True,
        'file_url': file_url
    }
    firebase_db.save_credential(cred_data)
    flash(f'Credential "{title}" registered.', 'success')
    return redirect(url_for('admin_credentials'))

@app.route('/admin/credentials/delete/<cred_id>', methods=['POST'])
@admin_required
def admin_delete_credential(cred_id):
    firebase_db.delete_credential(cred_id)
    flash('Credential deleted successfully.', 'success')
    return redirect(url_for('admin_credentials'))

# --- Admin Settings & Password ---
@app.route('/admin/settings')
@admin_required
def admin_settings():
    return render_template('admin/settings.html', active_admin_page='settings')

@app.route('/admin/settings/password', methods=['POST'])
@admin_required
def admin_update_password():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    new_password = request.form.get('new_password', '').strip()

    user_id = session.get('admin_id', 'admin_1')
    user = firebase_db.get_user_by_email(session.get('admin_email', '')) or {}

    user['name'] = name
    user['email'] = email
    if new_password:
        user['password_hash'] = generate_password_hash(new_password)

    firebase_db.save_user(user, user_id=user_id)
    session['admin_name'] = name
    session['admin_email'] = email

    flash('Security credentials updated successfully.', 'success')
    return redirect(url_for('admin_settings'))

@app.route('/admin/export-data')
@admin_required
def admin_export_data():
    local_db_path = os.path.join(os.path.dirname(__file__), 'data', 'local_db.json')
    if os.path.exists(local_db_path):
        return send_file(local_db_path, as_attachment=True, download_name='shiv_traders_database_backup.json')
    flash('Local database file not available.', 'error')
    return redirect(url_for('admin_settings'))

# -------------------------------------------------------------
# ERROR HANDLERS
# -------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', content='<div class="container text-center" style="padding: 8rem 0;"><h1 class="gold-gradient-text" style="font-size: 5rem;">404</h1><h2 style="margin-bottom: 1rem;">Page Not Found</h2><p style="color: var(--text-secondary); margin-bottom: 2rem;">The requested infrastructure page or specification does not exist.</p><a href="/" class="btn btn-primary">Return to Homepage</a></div>'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', content='<div class="container text-center" style="padding: 8rem 0;"><h1 style="color: #ef4444; font-size: 4rem;">500</h1><h2 style="margin-bottom: 1rem;">Internal Server Error</h2><p style="color: var(--text-secondary); margin-bottom: 2rem;">We encountered an unexpected server error. Please try again shortly.</p><a href="/" class="btn btn-primary">Return to Homepage</a></div>'), 500

if __name__ == '__main__':
    import threading
    import webbrowser
    port = int(os.environ.get('PORT', 5000))
    url = f"http://127.0.0.1:{port}"

    def open_browser():
        try:
            webbrowser.open(url)
        except Exception:
            pass

    # Open browser automatically if not in debug reloader child
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.config.get('DEBUG'):
        threading.Timer(1.2, open_browser).start()
    elif not os.environ.get('WERKZEUG_RUN_MAIN'):
        threading.Timer(1.2, open_browser).start()

    print(f"\n==================================================")
    print(f"  SHIV TRADERS WEB APPLICATION RUNNING LIVE")
    print(f"  Website URL:  {url}")
    print(f"  Admin Portal: {url}/admin/login")
    print(f"==================================================\n")
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
