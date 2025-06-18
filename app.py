from flask import Flask, render_template, request, jsonify, send_file
import os
import json
import requests
from datetime import datetime
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

def get_coordinates(city, api_key):
    """Get coordinates for a city using Google Maps Geocoding API."""
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={city}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    
    if data['status'] != 'OK':
        raise Exception(f"Geocoding failed: {data['status']}")
    
    location = data['results'][0]['geometry']['location']
    return location['lat'], location['lng']

def search_places(lat, lng, business_type, radius, api_key):
    """Search for places using Google Places API."""
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        'location': f"{lat},{lng}",
        'radius': radius,
        'type': business_type,
        'key': api_key
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data['status'] != 'OK':
        raise Exception(f"Places search failed: {data['status']}")
    
    return data['results']

def get_place_details(place_id, api_key):
    """Get detailed information about a place using Google Places API."""
    url = f"https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        'place_id': place_id,
        'fields': 'name,formatted_address,formatted_phone_number,rating,user_ratings_total,price_level,types,opening_hours,website,geometry',
        'key': api_key
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data['status'] != 'OK':
        raise Exception(f"Place details failed: {data['status']}")
    
    return data['result']

def is_potential_lead(place):
    """Check if a place meets the criteria for a potential lead."""
    # Check if the place has fewer than 15 reviews or no reviews
    reviews = place.get('user_ratings_total', 0)
    if reviews >= 15:
        return False
    
    # Check if the place has a website
    if 'website' in place:
        return False
    
    # Check if the place is operational
    if place.get('business_status') != 'OPERATIONAL':
        return False
    
    return True

def format_opening_hours(hours):
    """Format opening hours into a readable string."""
    if not hours or 'weekday_text' not in hours:
        return 'Not available'
    return '\n'.join(hours['weekday_text'])

def format_business_types(types):
    """Format business types into a readable string."""
    if not types:
        return 'Not available'
    return ', '.join(types)

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """Handle the search request."""
    try:
        # Get form data
        city = request.form.get('city')
        business_type = request.form.get('business_type')
        radius = int(request.form.get('radius', 5000))
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        
        if not api_key:
            return jsonify({'error': 'API key not configured'}), 500
            
        if not all([city, business_type]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Get coordinates
        lat, lng = get_coordinates(city, api_key)
        
        # Search for places
        places = search_places(lat, lng, business_type, radius, api_key)
        
        # Process results
        leads = []
        for place in places:
            if is_potential_lead(place):
                # Get detailed information
                details = get_place_details(place['place_id'], api_key)
                
                lead = {
                    'name': details.get('name', 'N/A'),
                    'address': details.get('formatted_address', 'N/A'),
                    'phone': details.get('formatted_phone_number', 'N/A'),
                    'rating': details.get('rating', 'N/A'),
                    'reviews': details.get('user_ratings_total', 0),
                    'price_level': '★' * details.get('price_level', 0),
                    'business_types': format_business_types(details.get('types', [])),
                    'opening_hours': format_opening_hours(details.get('opening_hours', {})),
                    'google_maps_url': f"https://www.google.com/maps/place/?q=place_id:{place['place_id']}",
                    'latitude': details.get('geometry', {}).get('location', {}).get('lat', 'N/A'),
                    'longitude': details.get('geometry', {}).get('location', {}).get('lng', 'N/A'),
                    'business_status': place.get('business_status', 'N/A')
                }
                leads.append(lead)
        
        return jsonify({
            'success': True,
            'leads': leads
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    """Handle the download request."""
    try:
        # Get leads data
        data = request.get_json()
        leads = data.get('leads', [])
        
        if not leads:
            return jsonify({'error': 'No leads to download'}), 400
        
        # Create DataFrame
        df = pd.DataFrame(leads)
        
        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Leads')
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Leads']
            
            # Style the header
            header_font = Font(bold=True, color='FFFFFF')
            header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
            header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            
            # Style the data
            data_alignment = Alignment(vertical='center', wrap_text=True)
            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for row in worksheet.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = data_alignment
                    cell.border = border
            
            # Adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'leads_{timestamp}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 