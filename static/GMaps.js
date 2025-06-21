# Google Maps Lead Finder

This tool helps you find potential business leads from Google Maps based on specific criteria:
- Businesses with less than 15 reviews
- Businesses without a website
- Businesses that haven't claimed their Google Business Profile

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root and add your Google Maps API key:
```
GOOGLE_MAPS_API_KEY=your_api_key_here
```

To get a Google Maps API key:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Places API
   - Maps JavaScript API
4. Create credentials (API key) for your project

## Usage

1. Modify the `main()` function in `lead_finder.py` to set your desired:
   - Location (latitude and longitude)
   - Search radius (in meters)
   - Business type (optional)

2. Run the script:
```bash
python lead_finder.py
```

The script will:
- Search for businesses in the specified area
- Filter them based on the criteria
- Save the results to a CSV file named `potential_leads.csv`

## Output

The generated CSV file will contain the following information for each potential lead:
- Business name
- Address
- Phone number
- Rating
- Number of reviews
- Place ID
- Google Maps URL

## Notes

- The script includes rate limiting to respect Google Maps API quotas
- Make sure to comply with Google Maps API terms of service
- The API has usage limits and may incur costs depending on your usage 