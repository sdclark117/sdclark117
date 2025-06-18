const axios = require('axios');

const API_KEY = "YOUR_API_KEY_HERE";

async function findLeads() {
    try {
        // First, get the coordinates for New York
        console.log("Getting coordinates for New York...");
        const geocodeResponse = await axios.get(
            `https://maps.googleapis.com/maps/api/geocode/json?address=New%20York&key=${API_KEY}`
        );

        console.log("API Response:", geocodeResponse.data);

        if (geocodeResponse.data.status !== 'OK') {
            throw new Error(`Geocoding failed: ${geocodeResponse.data.status}`);
        }

        const location = geocodeResponse.data.results[0].geometry.location;
        console.log("Found coordinates:", location);

        // Now search for plumbers
        console.log("\nSearching for plumbers...");
        const placesResponse = await axios.get(
            `https://maps.googleapis.com/maps/api/place/nearbysearch/json?location=${location.lat},${location.lng}&radius=5000&type=plumber&key=${API_KEY}`
        );

        console.log("Places API Response:", placesResponse.data);

        if (placesResponse.data.status !== 'OK') {
            throw new Error(`Places search failed: ${placesResponse.data.status}`);
        }

        const places = placesResponse.data.results;
        console.log(`Found ${places.length} businesses`);

        // Process each place
        const leads = [];
        for (const place of places) {
            // Get detailed information
            const detailsResponse = await axios.get(
                `https://maps.googleapis.com/maps/api/place/details/json?place_id=${place.place_id}&fields=name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,business_status,url&key=${API_KEY}`
            );

            if (detailsResponse.data.status !== 'OK') {
                console.log(`Failed to get details for ${place.name}`);
                continue;
            }

            const details = detailsResponse.data.result;

            // Check if it's a potential lead
            if (details.user_ratings_total < 15 && 
                !details.website && 
                details.business_status === 'OPERATIONAL') {
                
                leads.push({
                    name: details.name,
                    address: details.formatted_address,
                    phone: details.formatted_phone_number,
                    rating: details.rating,
                    reviews_count: details.user_ratings_total,
                    place_id: details.place_id,
                    google_maps_url: details.url
                });
            }
        }

        // Save results
        if (leads.length > 0) {
            console.log(`\nFound ${leads.length} potential leads!`);
            console.log(JSON.stringify(leads, null, 2));
        } else {
            console.log("\nNo potential leads found.");
        }

    } catch (error) {
        console.error("Error:", error.message);
        if (error.response) {
            console.error("Response data:", error.response.data);
        }
    }
}

findLeads(); 