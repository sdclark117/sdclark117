let map;
let marker;
let allMarkers = [];
let infoWindow;

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
}

async function performSearch(event) {
    event.preventDefault();
    
    document.getElementById('alert').style.display = 'none';
    const resultsTableBody = document.querySelector("#resultsTable tbody");
    resultsTableBody.innerHTML = ''; // Clear previous results
    clearAllMarkers();

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
            displayResults(data.results);
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

function displayResults(results) {
    const resultsTableBody = document.querySelector("#resultsTable tbody");
    const bounds = new google.maps.LatLngBounds();

    results.forEach(place => {
        const row = resultsTableBody.insertRow();
        row.innerHTML = `
            <td>${place.name || 'N/A'}</td>
            <td>${place.address || 'N/A'}</td>
            <td>${place.phone || 'N/A'}</td>
            <td>${place.website ? `<a href="${place.website}" target="_blank">View</a>` : 'N/A'}</td>
            <td>${place.rating || 'N/A'}</td>
            <td>${place.reviews || 'N/A'}</td>
            <td>${place.opening_hours || 'N/A'}</td>
        `;

        if (place.location) {
            const position = { lat: place.location.lat, lng: place.location.lng };
            const placeMarker = new google.maps.Marker({
                position,
                map,
                title: place.name
            });

            placeMarker.addListener('click', () => {
                const content = `
                    <h5>${place.name}</h5>
                    <p>${place.address}</p>
                    <p>Rating: ${place.rating} (${place.reviews} reviews)</p>
                    ${place.website ? `<a href="${place.website}" target="_blank">Website</a>` : ''}
                `;
                infoWindow.setContent(content);
                infoWindow.open(map, placeMarker);
            });

            allMarkers.push(placeMarker);
            bounds.extend(position);
        }
    });

    if (allMarkers.length > 0) {
        map.fitBounds(bounds);
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