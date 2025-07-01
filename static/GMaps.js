let map;
let marker;
let allMarkers = [];
let infoWindow;
let radiusCircle;

function initMap() {
    const initialLocation = { lat: 40.7128, lng: -74.0060 }; // Default to New York City

    map = new google.maps.Map(document.getElementById("map"), {
        zoom: 12,
        center: initialLocation,
    });

    infoWindow = new google.maps.InfoWindow();

    map.addListener("click", (mapsMouseEvent) => {
        placeMarker(mapsMouseEvent.latLng);
    });

    document.getElementById('searchForm').addEventListener('submit', performSearch);
    document.getElementById('clearPin').addEventListener('click', clearPin);
}

function placeMarker(position) {
    if (marker) {
        marker.setPosition(position);
    } else {
        marker = new google.maps.Marker({
            position: position,
            map: map,
        });
    }
    map.panTo(position);
}

function clearPin() {
    if (marker) {
        marker.setMap(null);
        marker = null;
    }
    clearRadiusCircle();
}

function clearRadiusCircle() {
    if (radiusCircle) {
        radiusCircle.setMap(null);
        radiusCircle = null;
    }
}

async function performSearch(event) {
    event.preventDefault();
    
    document.getElementById('alert').style.display = 'none';
    const resultsTableBody = document.querySelector("#resultsTable tbody");
    resultsTableBody.innerHTML = ''; // Clear previous results
    clearAllMarkers();
    clearRadiusCircle();

    const city = document.getElementById('city').value;
    const state = document.getElementById('state').value;
    const businessType = document.getElementById('businessType').value;
    const radius = document.getElementById('radius').value;
    const maxReviews = document.getElementById('maxReviews').value;
    const usePin = document.getElementById('usePin').checked;

    let locationQuery = '';
    if (city && state) {
        locationQuery = `${city}, ${state}`;
    }

    if (!businessType) {
        showAlert('Business Type is required.');
        return;
    }

    let lat, lng;
    if (usePin && marker) {
        lat = marker.getPosition().lat();
        lng = marker.getPosition().lng();
    }
    
    showLoading(true);

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                city,
                state,
                business_type: businessType,
                radius,
                max_reviews: maxReviews,
                lat,
                lng
            }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            showAlert(data.error);
        } else if (data.results && data.results.length > 0) {
            displayResults(data.results, data.center, radius);
            document.getElementById('exportBtn').disabled = false;
        } else {
            showAlert('No results found.');
            document.getElementById('exportBtn').disabled = true;
        }

    } catch (error) {
        console.error('Search error:', error);
        showAlert(error.message || 'An unexpected error occurred.');
    } finally {
        showLoading(false);
    }
}

function displayResults(results, center, radius) {
    const resultsTableBody = document.querySelector("#resultsTable tbody");
    const bounds = new google.maps.LatLngBounds();
    
    // Center map on search area and show radius
    if (center && center.lat && center.lng) {
        const centerPosition = { lat: center.lat, lng: center.lng };
        
        // Center the map on the search area
        map.setCenter(centerPosition);
        
        // Draw radius circle
        if (radius && !isNaN(radius)) {
            const radiusMeters = parseFloat(radius) * 1609.34; // Convert miles to meters
            radiusCircle = new google.maps.Circle({
                strokeColor: '#FF0000',
                strokeOpacity: 0.8,
                strokeWeight: 2,
                fillColor: '#FF0000',
                fillOpacity: 0.1,
                map: map,
                center: centerPosition,
                radius: radiusMeters,
            });
            
            // Extend bounds to include the radius circle
            bounds.extend(centerPosition);
        }
    }

    results.forEach(place => {
        const row = resultsTableBody.insertRow();
        row.innerHTML = `
            <td>${place.name || 'N/A'}</td>
            <td>${place.address || 'N/A'}</td>
            <td>${place.phone || 'N/A'}</td>
            <td>${place.website ? `<a href="${place.website}" target="_blank">${place.website}</a>` : 'N/A'}</td>
            <td>${place.rating || 'N/A'}</td>
            <td>${place.reviews || 'N/A'}</td>
            <td>${place.opening_hours || 'N/A'}</td>
        `;

        // Create marker for each business
        if (place.lat && place.lng) {
            const position = { lat: place.lat, lng: place.lng };
            const placeMarker = new google.maps.Marker({
                position,
                map,
                title: place.name,
                icon: {
                    url: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
                    scaledSize: new google.maps.Size(32, 32)
                }
            });

            placeMarker.addListener('click', () => {
                const content = `
                    <div style="max-width: 300px;">
                        <h5 style="margin: 0 0 10px 0; color: #333;">${place.name}</h5>
                        <p style="margin: 5px 0; color: #666;"><strong>Address:</strong> ${place.address}</p>
                        <p style="margin: 5px 0; color: #666;"><strong>Phone:</strong> ${place.phone || 'N/A'}</p>
                        <p style="margin: 5px 0; color: #666;"><strong>Rating:</strong> ${place.rating || 'N/A'} (${place.reviews || '0'} reviews)</p>
                        ${place.website ? `<p style="margin: 5px 0;"><a href="${place.website}" target="_blank" style="color: #007bff;">Visit Website</a></p>` : ''}
                    </div>
                `;
                infoWindow.setContent(content);
                infoWindow.open(map, placeMarker);
            });

            allMarkers.push(placeMarker);
            bounds.extend(position);
        }
    });

    // Fit map to show all markers and radius
    if (allMarkers.length > 0 || radiusCircle) {
        map.fitBounds(bounds);
        
        // Add some padding to the bounds
        const listener = google.maps.event.addListenerOnce(map, 'bounds_changed', function() {
            map.setZoom(Math.min(map.getZoom(), 15)); // Don't zoom in too much
        });
    }
}

function clearAllMarkers() {
    allMarkers.forEach(m => m.setMap(null));
    allMarkers = [];
}

function showAlert(message) {
    const alertDiv = document.getElementById('alert');
    alertDiv.textContent = message;
    alertDiv.style.display = 'block';
}

function showLoading(isLoading) {
    // Implement or connect to a loading spinner element if you have one
    // For example: document.getElementById('loadingSpinner').style.display = isLoading ? 'block' : 'none';
} 