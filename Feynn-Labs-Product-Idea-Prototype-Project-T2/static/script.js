// To make sure shares count won't go below 0 in buy and sell
function validateSharesInput(input) {
    // Ensure the input value is a non-negative integer
    var currentShares = parseInt(input.value, 10) || 0;
    input.value = Math.max(currentShares, 0);
}

// To make sure shares count won't go below 0 in cash
function validateCash(cashInput) {
    var currentCash = parseFloat(cashInput.value, 10) || 0;
    cashInput.value = Math.max(currentCash, 0.00);
}

// Function to fetch cities based on the selected state
function fetchCities() {
    const state = document.getElementById('state').value;

    fetch(`/get-cities?state=${state}`)
        .then(response => response.json())
        .then(data => {
            const cityDropdown = document.getElementById('city');
            cityDropdown.innerHTML = '';

            data.cities.forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                option.text = city;
                cityDropdown.appendChild(option);
            });
        });
}

// Function to show autocomplete suggestions
function showSuggestions(value) {
    const suggestionsContainer = document.getElementById('suggestions');
    suggestionsContainer.innerHTML = '';

    if (!value) {
        suggestionsContainer.classList.remove('active');
        return;
    }

    const filteredCities = cities.filter(city =>
        city.toLowerCase().includes(value.toLowerCase())
    );

    if (filteredCities.length > 0) {
        suggestionsContainer.classList.add('active');

        filteredCities.forEach(city => {
            const suggestionElement = document.createElement('div');
            suggestionElement.className = 'autocomplete-suggestion';
            suggestionElement.textContent = city;

            suggestionElement.addEventListener('click', () => {
                locationInput.value = city;
                suggestionsContainer.innerHTML = '';
                suggestionsContainer.classList.remove('active');
            });

            suggestionsContainer.appendChild(suggestionElement);
        });
    } else {
        suggestionsContainer.classList.remove('active');
    }
}

// Event listener for input field
document.getElementById('locationInput').addEventListener('input', () => {
    const value = locationInput.value;
    showSuggestions(value);
});

// Form submit listener to validate input before submitting
document.getElementById('locationForm').addEventListener('submit', (event) => {
    const userInput = locationInput.value.trim();

    if (!cities.includes(userInput)) {
        alert('Please enter a valid city from the suggestions.');
        event.preventDefault();
    }
});
