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
from typing import Union, BinaryIO

# Load environment variables
load_dotenv()

app = Flask(__name__)

def get_coordinates(location, api_key):
    """Get coordinates for a location using Google Geocoding API."""
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': location,
            'key': api_key
        }
        print(f"Geocoding URL: {url}")  # Debug print
        print(f"Geocoding params: {params}")  # Debug print
        
        response = requests.get(url, params=params)
        print(f"Geocoding response status: {response.status_code}")  # Debug print
        data = response.json()
        print(f"Geocoding response data: {data}")  # Debug print
        
        if data.get('status') == 'REQUEST_DENIED':
            error_message = data.get('error_message', 'No error message provided')
            print(f"Geocoding request denied. Error message: {error_message}")  # Debug print
            raise Exception(f"Geocoding request denied: {error_message}")
            
        if data.get('status') != 'OK':
            error_msg = f"Geocoding failed: {data.get('status')}"
            if data.get('error_message'):
                error_msg += f" - {data.get('error_message')}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)
            
        location = data['results'][0]['geometry']['location']
        return location
        
    except requests.exceptions.RequestException as e:
        print(f"Geocoding request exception: {str(e)}")  # Debug print
        raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error in get_coordinates: {str(e)}")  # Debug print
        raise

def search_places(lat, lng, business_type, radius, api_key):
    """Search for places using Google Places API."""
    try:
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        
        # Convert business type to a format Google Places API understands
        # Remove any spaces and convert to lowercase
        business_type = business_type.lower().strip()
        
        params = {
            'location': f"{lat},{lng}",
            'radius': radius,
            'keyword': business_type,  # Use keyword instead of type for more flexible searching
            'key': api_key
        }
        print(f"Searching places with params: {params}")  # Debug print
        
        response = requests.get(url, params=params)
        print(f"Places API Response status: {response.status_code}")  # Debug print
        data = response.json()
        print(f"Places API Response data: {data}")  # Debug print
        
        if data.get('status') == 'REQUEST_DENIED':
            error_message = data.get('error_message', 'No error message provided')
            print(f"Places API request denied. Error message: {error_message}")  # Debug print
            raise Exception(f"Places API request denied: {error_message}")
            
        if data.get('status') != 'OK':
            error_msg = f"Places search failed: {data.get('status')}"
            if data.get('error_message'):
                error_msg += f" - {data.get('error_message')}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)
        
        leads = []
        for place in data.get('results', []):
            # Get place details for additional information
            try:
                place_id = place.get('place_id')
                if place_id:
                    details_url = f"https://maps.googleapis.com/maps/api/place/details/json"
                    details_params = {
                        'place_id': place_id,
                        'fields': 'name,formatted_address,formatted_phone_number,website,rating,opening_hours',
                        'key': api_key
                    }
                    details_response = requests.get(details_url, params=details_params)
                    details_data = details_response.json()
                    
                    if details_data.get('status') == 'OK':
                        details = details_data.get('result', {})
                        lead = {
                            'place_id': place_id,  # Add place_id for deduplication
                            'name': details.get('name', place.get('name', '')),
                            'address': details.get('formatted_address', place.get('vicinity', '')),
                            'lat': place['geometry']['location']['lat'],
                            'lng': place['geometry']['location']['lng'],
                            'rating': details.get('rating', place.get('rating', '')),
                            'website': details.get('website', ''),
                            'phone': details.get('formatted_phone_number', ''),
                            'opening_hours': details.get('opening_hours', {}).get('weekday_text', [])
                        }
                    else:
                        # Fallback to basic place data if details request fails
                        lead = {
                            'place_id': place_id,
                            'name': place.get('name', ''),
                            'address': place.get('vicinity', ''),
                            'lat': place['geometry']['location']['lat'],
                            'lng': place['geometry']['location']['lng'],
                            'rating': place.get('rating', ''),
                            'website': '',
                            'phone': '',
                            'opening_hours': []
                        }
                else:
                    # Fallback to basic place data if no place_id
                    lead = {
                        'place_id': f"temp_{len(leads)}",  # Generate temporary ID
                        'name': place.get('name', ''),
                        'address': place.get('vicinity', ''),
                        'lat': place['geometry']['location']['lat'],
                        'lng': place['geometry']['location']['lng'],
                        'rating': place.get('rating', ''),
                        'website': '',
                        'phone': '',
                        'opening_hours': []
                    }
                
                leads.append(lead)
                print(f"Found lead: {lead}")  # Debug print
                
            except Exception as e:
                print(f"Error getting details for place: {str(e)}")  # Debug print
                continue
        
        return leads
        
    except requests.exceptions.RequestException as e:
        print(f"Places API request exception: {str(e)}")  # Debug print
        raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error in search_places: {str(e)}")  # Debug print
        raise

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
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    print(f"API Key present: {bool(api_key)}")  # Debug print
    if not api_key:
        print("Warning: Google Maps API key is not configured")  # Debug print
        return render_template('index.html', api_key='')
    return render_template('index.html', api_key=api_key)

@app.route('/search', methods=['POST'])
def search():
    """Search for businesses in a city."""
    try:
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if not api_key:
            raise Exception("Google Maps API key is not configured")
            
        data = request.json
        if not data:
            raise Exception("No data provided in request")
            
        city = data.get('city', '').strip()
        state = data.get('state', '').strip()
        business_type = data.get('business_type', '').strip()
        radius = float(data.get('radius', 5))  # Default to 5 miles
        lat = data.get('lat')
        lng = data.get('lng')
        
        print(f"Search API Key present: {bool(api_key)}")  # Debug print
        print(f"City: {city}, State: {state}")  # Debug print
        print(f"Business Type: {business_type}")  # Debug print
        print(f"Coordinates: {lat}, {lng}")  # Debug print
            
        if not business_type:
            raise Exception("Business type is required")
            
        if lat is not None and lng is not None:
            # Use provided coordinates
            center = {'lat': float(lat), 'lng': float(lng)}
        elif city:
            # Get coordinates for city
            location = f"{city}, {state}" if state else city
            center = get_coordinates(location, api_key)
        else:
            raise Exception("Either city or coordinates must be provided")
            
        # Convert radius from miles to meters
        radius_meters = radius * 1609.34
        
        # Search for places
        leads = search_places(center['lat'], center['lng'], business_type, radius_meters, api_key)
        
        return jsonify({
            'leads': leads,
            'center': center
        })
        
    except Exception as e:
        print(f"Search error: {str(e)}")  # Debug print
        return jsonify({'error': str(e)}), 400

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.json
        if not data or 'leads' not in data:
            raise Exception("No leads data provided")
            
        leads = data['leads']
        if not leads:
            raise Exception("No leads to export")
            
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
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'business_leads_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/export', methods=['POST'])
def export_to_excel():
    try:
        data = request.json
        if not data or 'leads' not in data:
            raise Exception("No leads data provided")
            
        leads = data['leads']
        if not leads:
            raise Exception("No leads to export")
            
        # Create DataFrame
        df = pd.DataFrame(leads)
        
        # Reorder columns for better presentation
        columns = ['name', 'address', 'phone', 'website', 'rating', 'opening_hours']
        df = df[columns]
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Business Leads', index=False)
            
            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Business Leads']
            
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
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'business_leads_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True) 