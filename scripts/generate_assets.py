import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_gradient(width, height, start_color, end_color):
    base = Image.new('RGB', (width, height), start_color)
    top = Image.new('RGB', (width, height), end_color)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        for x in range(width):
            mask_data.append(int(255 * (y / height)))
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def draw_pattern(img, pattern_type='grid', color=(255, 255, 255, 15)):
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    if pattern_type == 'grid':
        for x in range(0, w, 40):
            draw.line([(x, 0), (x, h)], fill=color, width=1)
        for y in range(0, h, 40):
            draw.line([(0, y), (w, y)], fill=color, width=1)
    elif pattern_type == 'zigzag':
        for y in range(0, h, 50):
            points = []
            for x in range(0, w + 50, 40):
                offset = 20 if (x // 40) % 2 == 0 else 0
                points.append((x, y + offset))
            draw.line(points, fill=color, width=2)
    elif pattern_type == 'hex':
        for y in range(0, h, 60):
            for x in range(0, w, 60):
                draw.polygon([
                    (x + 30, y), (x + 60, y + 15), (x + 60, y + 45),
                    (x + 30, y + 60), (x, y + 45), (x, y + 15)
                ], outline=color, width=1)

def generate_product_image(filename, title, subtitle, spec, color_theme, pattern='zigzag'):
    w, h = 800, 600
    # Create dark luxury gradient
    bg = create_gradient(w, h, (18, 20, 24), (28, 32, 38))
    draw_pattern(bg, pattern, (205, 168, 81, 25))
    
    draw = ImageDraw.Draw(bg, 'RGBA')
    
    # Draw central luxury product pedestal
    pedestal_poly = [(160, 420), (640, 420), (560, 490), (240, 490)]
    draw.polygon(pedestal_poly, fill=(12, 14, 16, 200), outline=(205, 168, 81, 100), width=2)
    
    # Draw 3D Isometric Paver Representation
    cx, cy = 400, 300
    theme_rgb = color_theme
    # Top face
    top_poly = [(cx, cy - 80), (cx + 140, cy - 10), (cx, cy + 60), (cx - 140, cy - 10)]
    draw.polygon(top_poly, fill=theme_rgb, outline=(255, 255, 255, 120), width=2)
    
    # Left face
    left_color = (max(0, theme_rgb[0]-40), max(0, theme_rgb[1]-40), max(0, theme_rgb[2]-40))
    left_poly = [(cx - 140, cy - 10), (cx, cy + 60), (cx, cy + 130), (cx - 140, cy + 60)]
    draw.polygon(left_poly, fill=left_color, outline=(20, 20, 20, 100), width=2)
    
    # Right face
    right_color = (max(0, theme_rgb[0]-70), max(0, theme_rgb[1]-70), max(0, theme_rgb[2]-70))
    right_poly = [(cx, cy + 60), (cx + 140, cy - 10), (cx + 140, cy + 60), (cx, cy + 130)]
    draw.polygon(right_poly, fill=right_color, outline=(20, 20, 20, 100), width=2)
    
    # Metallic gold brand tag
    draw.rectangle([(50, 45), (320, 85)], fill=(205, 168, 81, 30), outline=(205, 168, 81, 200), width=1)
    draw.text((65, 55), "SHIV TRADERS • LUXURY SPEC", fill=(225, 190, 100))
    
    # Title & Specs
    draw.text((50, 500), title, fill=(255, 255, 255))
    draw.text((50, 530), f"{subtitle} | {spec}", fill=(180, 190, 200))
    draw.text((620, 530), "M35 - M60 GRADE", fill=(205, 168, 81))
    
    bg.save(filename, 'WEBP', quality=90)
    print(f"Generated product asset: {filename}")

def generate_project_image(filename, title, category, area, loc):
    w, h = 900, 600
    bg = create_gradient(w, h, (15, 18, 22), (32, 38, 46))
    draw_pattern(bg, 'grid', (205, 168, 81, 30))
    draw = ImageDraw.Draw(bg, 'RGBA')
    
    # Geometric infrastructure lines & prospective roadway
    draw.polygon([(0, 600), (350, 280), (550, 280), (900, 600)], fill=(22, 26, 32, 230), outline=(205, 168, 81, 120), width=2)
    
    # Road centerline dashes
    for i in range(5):
        y1 = 300 + i * 55
        y2 = y1 + 35
        x1 = 450 - i * 3
        x2 = 450 + i * 3
        draw.polygon([(x1, y1), (x2, y1), (x2+4, y2), (x1-4, y2)], fill=(205, 168, 81, 200))
        
    # Overlay card
    draw.rectangle([(40, 40), (860, 110)], fill=(12, 14, 18, 220), outline=(205, 168, 81, 150), width=1)
    draw.text((60, 55), "SHIV TRADERS INFRASTRUCTURE PORTFOLIO", fill=(205, 168, 81))
    draw.text((60, 78), f"CATEGORY: {category.upper()} • VERIFIED PROJECT", fill=(200, 210, 220))
    
    draw.rectangle([(40, 480), (860, 560)], fill=(12, 14, 18, 230), outline=(50, 60, 75, 200), width=1)
    draw.text((60, 495), title, fill=(255, 255, 255))
    draw.text((60, 525), f"Location: {loc}  |  Area: {area}", fill=(180, 190, 200))
    draw.text((700, 510), "COMPLETED", fill=(100, 220, 150))
    
    bg.save(filename, 'WEBP', quality=90)
    print(f"Generated project asset: {filename}")

def generate_manufacturing_image(filename, step_name, tech_highlight):
    w, h = 900, 600
    bg = create_gradient(w, h, (10, 12, 16), (25, 30, 38))
    draw_pattern(bg, 'grid', (205, 168, 81, 25))
    draw = ImageDraw.Draw(bg, 'RGBA')
    
    # Machinery silhouettes
    draw.rectangle([(200, 180), (700, 460)], fill=(20, 25, 32, 240), outline=(205, 168, 81, 160), width=2)
    draw.rectangle([(240, 220), (660, 360)], fill=(30, 36, 46, 255), outline=(100, 110, 130), width=1)
    
    # Hydraulic cylinder representation
    draw.rectangle([(420, 100), (480, 220)], fill=(180, 150, 80), outline=(255, 255, 255, 180), width=2)
    draw.rectangle([(400, 80), (500, 100)], fill=(205, 168, 81))
    
    draw.rectangle([(40, 40), (860, 100)], fill=(12, 14, 18, 220), outline=(205, 168, 81, 120), width=1)
    draw.text((60, 52), "SHIV TRADERS ADVANCED MANUFACTURING PLANT", fill=(205, 168, 81))
    draw.text((60, 74), f"STAGE: {step_name.upper()}", fill=(220, 225, 230))
    
    draw.rectangle([(40, 490), (860, 560)], fill=(12, 14, 18, 230), outline=(50, 60, 75, 200), width=1)
    draw.text((60, 505), step_name, fill=(255, 255, 255))
    draw.text((60, 530), tech_highlight, fill=(180, 190, 200))
    
    bg.save(filename, 'WEBP', quality=90)
    print(f"Generated manufacturing asset: {filename}")

def generate_certificate_image(filename, cert_title, reg_num, authority):
    w, h = 800, 580
    bg = Image.new('RGB', (w, h), (248, 249, 250))
    draw = ImageDraw.Draw(bg, 'RGBA')
    
    # Luxury border
    draw.rectangle([(25, 25), (w - 25, h - 25)], outline=(205, 168, 81), width=4)
    draw.rectangle([(35, 35), (w - 35, h - 35)], outline=(30, 35, 45), width=1)
    
    # Gold seal
    cx, cy = 680, 460
    draw.ellipse([(cx-45, cy-45), (cx+45, cy+45)], fill=(205, 168, 81, 230), outline=(170, 130, 40), width=3)
    draw.text((cx-30, cy-10), "VERIFIED", fill=(255, 255, 255))
    
    draw.text((60, 60), "OFFICIAL ACCREDITATION & CERTIFICATE OF COMPLIANCE", fill=(140, 100, 20))
    draw.text((60, 95), cert_title.upper(), fill=(15, 20, 30))
    
    draw.line([(60, 140), (740, 140)], fill=(205, 168, 81), width=2)
    
    draw.text((60, 160), "ISSUED TO: SHIV TRADERS", fill=(40, 45, 55))
    draw.text((60, 190), f"REGISTRATION / CERTIFICATE NO: {reg_num}", fill=(20, 25, 35))
    draw.text((60, 220), f"AUTHORITY: {authority}", fill=(80, 90, 100))
    
    draw.text((60, 280), "This official documentation confirms that Shiv Traders strictly adheres to", fill=(70, 75, 85))
    draw.text((60, 305), "statutory industrial manufacturing standards, certified compressive strength limits,", fill=(70, 75, 85))
    draw.text((60, 330), "and government infrastructure specification benchmarks.", fill=(70, 75, 85))
    
    draw.text((60, 420), "Status: FULLY ACTIVE & VERIFIED", fill=(20, 140, 60))
    draw.text((60, 450), "Audit Reference: BIS/CPWD-ST-2026", fill=(100, 110, 120))
    
    bg.save(filename, 'WEBP', quality=90)
    print(f"Generated certificate asset: {filename}")

def generate_hero_banner():
    w, h = 1920, 1080
    bg = create_gradient(w, h, (10, 12, 15), (24, 28, 36))
    draw_pattern(bg, 'grid', (205, 168, 81, 35))
    draw = ImageDraw.Draw(bg, 'RGBA')
    
    # Dramatic infrastructure perspective diagonals
    draw.polygon([(0, 1080), (800, 520), (1120, 520), (1920, 1080)], fill=(16, 20, 26, 220), outline=(205, 168, 81, 100), width=3)
    
    # Gold aesthetic lighting glow
    bg.save('static/images/hero/hero_bg.webp', 'WEBP', quality=85)
    print("Generated hero banner")

if __name__ == '__main__':
    # Products
    generate_product_image('static/images/products/zigzag_paver.webp', 'Zig-Zag Interlock Paver', 'Heavy Duty Multi-Axle Traffic', '80mm / M40-M50 Grade', (170, 80, 70), 'zigzag')
    generate_product_image('static/images/products/zigzag_installed.webp', 'Zig-Zag Paver In-Situ', 'High Interlock Friction Pavement', '80mm Industrial', (150, 70, 60), 'zigzag')
    generate_product_image('static/images/products/unipaver_ishape.webp', 'Unipaver I-Shape Paver', 'Commercial & Municipal Corridors', '60mm / 80mm M35', (120, 125, 135), 'zigzag')
    generate_product_image('static/images/products/hexagonal_paver.webp', 'Hexagonal Architectural Tile', 'Luxury Plazas & Residential Drives', '60mm M35 Reflective', (185, 140, 90), 'hex')
    generate_product_image('static/images/products/industrial_heavy_paver.webp', 'Industrial Heavy-Duty Dock Paver', 'Port & Container Terminals', '100mm M50-M60 Extreme Load', (75, 80, 90), 'grid')
    generate_product_image('static/images/products/kerb_stone.webp', 'Hydraulic Pressed Kerb Stone', 'CPWD Road Edging & Medians', '450x300x150mm Chamfered', (140, 145, 155), 'grid')
    generate_product_image('static/images/products/grass_paver.webp', 'Eco-Grid Concrete Grass Paver', 'Permeable Green Parking', '80mm M35 Eco-System', (85, 130, 90), 'grid')
    generate_product_image('static/images/products/chequered_tile.webp', 'Chequered Anti-Skid Flooring Tile', 'Basement Ramps & Heavy Transit', '300x300x25mm Diamond Grip', (160, 60, 60), 'grid')
    generate_product_image('static/images/products/cover_blocks.webp', 'High-Strength Concrete Cover Blocks', 'Structural RCC Rebar Spacers', 'M50 High Density Moulded', (110, 115, 125), 'hex')

    # Projects
    generate_project_image('static/images/projects/smart_city_street.webp', 'Smart City Urban Corridor Pavement', 'Street Development', '145,000 Sq. Ft.', 'Jaipur Urban Boulevard')
    generate_project_image('static/images/projects/smart_city_detail.webp', 'Smart City Boulevard Pedestrian Track', 'Street Development', 'Tactile Pavers', 'Jaipur Central Zone')
    generate_project_image('static/images/projects/logistics_yard.webp', 'Logistics Freight Transshipment Terminal', 'Factory Construction', '380,000 Sq. Ft.', 'Industrial Freight Corridor')
    generate_project_image('static/images/projects/commercial_parking.webp', 'Commercial Hub Multi-Deck Parking Plaza', 'Parking Area', '92,000 Sq. Ft.', 'Central Business District')
    generate_project_image('static/images/projects/market_terminal.webp', 'Regional Agro-Terminal Market Yard', 'Market Development', '210,000 Sq. Ft.', 'State Agricultural Hub')
    generate_project_image('static/images/projects/toll_plaza.webp', 'National Highway Toll Plaza Interlock Surface', 'Government Infrastructure', '165,000 Sq. Ft.', 'NH-48 Corridor')
    generate_project_image('static/images/projects/industrial_roads.webp', 'Heavy Engineering Plant Internal Road Network', 'Interlock Tile Installation', '120,000 Sq. Ft.', 'Industrial Hub')

    # Manufacturing & Services
    generate_manufacturing_image('static/images/manufacturing/plant_press.webp', 'Automated High-Tonnage Vibro-Press', '120-Ton Hydraulic Compression for Zero Porosity')
    generate_manufacturing_image('static/images/manufacturing/service_paving.webp', 'Laser-Guided Paving & Compaction', 'Turnkey Site Preparation & Mechanical Laying')
    generate_manufacturing_image('static/images/manufacturing/service_industrial.webp', 'Heavy Industrial Pavement Engineering', 'M50/M60 High Axle Load Interlocking Solutions')
    generate_manufacturing_image('static/images/manufacturing/service_government.webp', 'Government & CPWD Infrastructure Works', 'Strict MoRTH/IRC Quality Benchmark Execution')

    # Certificates
    generate_certificate_image('static/images/certificates/gst_certificate.webp', 'GST Registration Certificate', '08AABCS1429K1Z5', 'Government of India - GSTIN')
    generate_certificate_image('static/images/certificates/iso_certificate.webp', 'ISO 9001:2015 Quality Management', 'ISO-QMS-2023-8841', 'International Accreditation Service')
    generate_certificate_image('static/images/certificates/tm_certificate.webp', 'Registered Trademark Certificate Class 19', 'TM-4928172', 'Trade Marks Registry, Govt. of India')
    generate_certificate_image('static/images/certificates/lab_report.webp', 'BIS & CPWD Lab Test Conformity Report', 'IS 15658:2021-TR-904', 'NABL Accredited Civil Testing Lab')

    # Hero
    generate_hero_banner()
    print("All image assets generated successfully!")
