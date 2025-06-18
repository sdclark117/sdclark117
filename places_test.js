const axios = require('axios');

const API_KEY = "AIzaSyC1Nc1H7nBh9-vAFxeadGOB-laiChwBKSk";

async function testPlaces() {
    try {
        console.log("Testing Places API...");
        
        const response = await axios.get(
            `https://maps.googleapis.com/maps/api/place/nearbysearch/json?location=40.7128,-74.0060&radius=5000&type=plumber&key=${API_KEY}`
        );

        console.log("\nFull API Response:");
        console.log(JSON.stringify(response.data, null, 2));

    } catch (error) {
        console.error("\nError occurred:");
        console.error("Message:", error.message);
        if (error.response) {
            console.error("\nResponse data:", error.response.data);
            console.error("\nResponse status:", error.response.status);
        }
    }
}

testPlaces(); 