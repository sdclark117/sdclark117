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
   - Geocoding API
4. Create credentials (API key) for your project

## Environment Variables

Create a `.env` file in the project root with the following content:

```
GOOGLE_MAPS_API_KEY=your_api_key_here
```

Replace `your_api_key_here` with your actual Google Maps API key. This file is ignored by git and should not be committed.

The application will automatically load this variable using `python-dotenv`.

## Usage

Run the script with the following command:

```bash
python lead_finder.py "City Name" [options]
```

### Arguments:
- `city`: Required. The city name to search in (e.g., "New York, NY" or "Los Angeles, CA")

### Options:
- `--radius`: Search radius in meters (default: 5000)
- `--business-type`: Type of business to search for (use --list-types to see available options)
- `--output`: Output CSV filename (default: potential_leads.csv)
- `--list-types`: List all available business types

### Available Business Types

To see all available business types, run:
```bash
python lead_finder.py --list-types
```

The script includes many common business types such as:
- Professional Services (plumber, electrician, lawyer, etc.)
- Personal Care (barber, salon, spa, etc.)
- Food & Drink (restaurant, cafe, bar, etc.)
- Retail (clothing store, shoe store, etc.)
- Automotive (auto repair, car wash, etc.)
- Home Services (contractor, roofer, painter, etc.)
- Health & Fitness (gym, yoga, pharmacy, etc.)
- Education (school, tutor, daycare)
- Other Services (dry cleaner, laundry, pet groomer, etc.)

### Examples:

1. Search for plumbers in New York within 5km:
```bash
python lead_finder.py "New York, NY" --business-type plumber
```

2. Search for hair salons in Los Angeles within 10km:
```bash
python lead_finder.py "Los Angeles, CA" --radius 10000 --business-type salon
```

3. Search for restaurants in Chicago and save to a custom file:
```bash
python lead_finder.py "Chicago, IL" --business-type restaurant --output chicago_restaurants.csv
```

## Output

The generated CSV file will contain the following information for each potential lead:
- Business name
- Address
- Phone number
- Rating
- Number of reviews
- Place ID
- Google Maps URL
- Business types (categories the business belongs to)

## Notes

- The script includes rate limiting to respect Google Maps API quotas
- Make sure to comply with Google Maps API terms of service
- The API has usage limits and may incur costs depending on your usage
- City names should be specific enough to get accurate results (e.g., "New York, NY" instead of just "New York")
- If you specify a business type that's not in the predefined list, the script will use it directly but will show a warning 