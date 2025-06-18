import googlemaps
import pandas as pd
from tqdm import tqdm
import time

# Your API key
API_KEY = "AIzaSyC1Nc1H7nBh9-vAFxeadGOB-laiChwBKSk"

def main():
    try:
        # Initialize the Google Maps client
        print("Initializing Google Maps client...")
        gmaps = googlemaps.Client(key=API_KEY)
        
        # Test geocoding
        print("\nTesting geocoding...")
        location = gmaps.geocode("New York, NY")[0]['geometry']['location']
        print(f"Found coordinates: {location}")
        
        # Test places search
        print("\nSearching for plumbers...")
        places_result = gmaps.places_nearby(
            location=location,
            radius=5000,
            type='plumber'
        )
        
        # Process results
        leads = []
        for place in tqdm(places_result.get('results', []), desc="Processing businesses"):
            # Get detailed information
            details = gmaps.place(place['place_id'], fields=[
                'name', 'formatted_address', 'formatted_phone_number',
                'website', 'rating', 'user_ratings_total', 'place_id',
                'business_status', 'url'
            ])['result']
            
            # Check if it's a potential lead
            if (details.get('user_ratings_total', 0) < 15 and 
                not details.get('website') and 
                details.get('business_status') == 'OPERATIONAL'):
                
                leads.append({
                    'name': details.get('name'),
                    'address': details.get('formatted_address'),
                    'phone': details.get('formatted_phone_number'),
                    'rating': details.get('rating'),
                    'reviews_count': details.get('user_ratings_total'),
                    'place_id': details.get('place_id'),
                    'google_maps_url': details.get('url')
                })
        
        # Save results
        if leads:
            df = pd.DataFrame(leads)
            df.to_csv('test_leads.csv', index=False)
            print(f"\nFound {len(leads)} potential leads! Saved to test_leads.csv")
        else:
            print("\nNo potential leads found.")
            
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main() 