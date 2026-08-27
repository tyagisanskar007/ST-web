import os
import sys
import unittest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from firebase_config import firebase_db

class ShivTradersWebTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_01_public_pages(self):
        """Verify all public pages load with HTTP 200"""
        prods = firebase_db.get_products()
        prod_id = prods[0]['product_id'] if prods else 'prod-1'
        projs = firebase_db.get_projects()
        proj_id = projs[0]['project_id'] if projs else 'proj-1'

        pages = [
            '/',
            '/about',
            '/products',
            f'/products/{prod_id}',
            '/manufacturing',
            '/services',
            '/projects',
            f'/projects/{proj_id}',
            '/government',
            '/credentials',
            '/contact'
        ]
        for url in pages:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Page {url} failed with status {response.status_code}")
            self.assertIn(b'Shiv Traders', response.data)

    def test_02_enquiry_submission(self):
        """Test public contact/enquiry submission API"""
        payload = {
            'name': 'Test Contractor',
            'phone': '+91 99999 88888',
            'email': 'test@contractor.in',
            'city': 'Jaipur',
            'company': 'Apex Builders',
            'project_type': 'Industrial Pavement',
            'quantity': '40,000 Sq. Ft.',
            'message': 'Need 80mm M50 interlock pavers quotation.'
        }
        response = self.client.post('/api/enquiry',
                                   data=json.dumps(payload),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 201)
        res_data = json.loads(response.data)
        self.assertTrue(res_data.get('success'))
        self.assertIn('enquiry_id', res_data)

        # Verify it exists in database
        enq_id = res_data['enquiry_id']
        enq = firebase_db.get_enquiry(enq_id)
        self.assertIsNotNone(enq)
        self.assertEqual(enq.get('name'), 'Test Contractor')
        self.assertEqual(enq.get('status'), 'New')

    def test_03_admin_protection(self):
        """Verify admin routes require login"""
        response = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login', response.headers.get('Location'))

    def test_04_admin_login_and_dashboard(self):
        """Test admin login flow and dashboard access"""
        response = self.client.post('/admin/login', data={
            'email': 'admin@shivtraders.com',
            'password': 'Admin@ShivTraders2026'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Executive Dashboard', response.data)
        self.assertIn(b'Products Catalog', response.data)

    def test_05_admin_product_crud(self):
        """Test Product CRUD operations in admin"""
        # Login first
        self.client.post('/admin/login', data={
            'email': 'admin@shivtraders.com',
            'password': 'Admin@ShivTraders2026'
        })

        # Add Product
        new_prod = {
            'name': 'Test Paver Block 90mm',
            'category': 'Interlock Tiles',
            'thickness': '90mm',
            'grade': 'M50',
            'compressive_strength': '55 N/mm²',
            'dimensions': '200x100x90mm',
            'finish': 'Shot Blasted',
            'description': 'Heavy loading test block',
            'colors': 'Grey, Red',
            'applications': 'Container Depots',
            'available': '1'
        }
        res_add = self.client.post('/admin/products/add', data=new_prod, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)
        self.assertIn(b'Test Paver Block 90mm', res_add.data)

        # Retrieve product ID from DB
        products = firebase_db.get_products()
        matching = [p for p in products if p.get('name') == 'Test Paver Block 90mm']
        self.assertTrue(len(matching) > 0)
        prod_id = matching[0]['product_id']

        # Edit Product
        new_prod['name'] = 'Test Paver Block 90mm Updated'
        res_edit = self.client.post(f'/admin/products/edit/{prod_id}', data=new_prod, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        self.assertIn(b'Test Paver Block 90mm Updated', res_edit.data)

        # Delete Product
        res_del = self.client.post(f'/admin/products/delete/{prod_id}', follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)
        prod_deleted = firebase_db.get_product(prod_id)
        self.assertIsNone(prod_deleted)

    def test_06_enquiry_status_ajax(self):
        """Test AJAX status update for enquiries"""
        # Login
        self.client.post('/admin/login', data={
            'email': 'admin@shivtraders.com',
            'password': 'Admin@ShivTraders2026'
        })

        # Create a test enquiry
        enq_id = firebase_db.create_enquiry({
            'name': 'Status Check User',
            'phone': '9876543210',
            'city': 'Jaipur',
            'status': 'New'
        })

        # Update status to 'In Progress' via AJAX endpoint
        res = self.client.post(f'/admin/api/enquiries/{enq_id}/status',
                              data=json.dumps({'status': 'In Progress'}),
                              content_type='application/json')
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.data)
        self.assertTrue(res_json.get('success'))

        # Check DB
        enq = firebase_db.get_enquiry(enq_id)
        self.assertEqual(enq.get('status'), 'In Progress')

if __name__ == '__main__':
    unittest.main()
