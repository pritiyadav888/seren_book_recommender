function fetchRecommendations(e, title, author) {
    if (e) e.preventDefault();

    // Removed promptUser()

    title = title || document.getElementById('rec_title').value;
    author = author || document.getElementById('rec_author').value;

    // Display loading message
    let div = document.getElementById('recommendations');
    div.innerHTML = '';
    let loadingElement = document.createElement('div');
    loadingElement.classList.add('loading');
    loadingElement.textContent = 'Loading...';
    div.appendChild(loadingElement);

    setTimeout(() => {
        fetch('/chatbot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ book_title: title, author_name: author }),
        })
        .then(response => response.json())
        .then(data => {
            div.innerHTML = ''; // Clear loading message

            data.recommendations.forEach(rec => {
                let card = document.createElement('div');
                card.classList.add('card');

                card.innerHTML = `
                <img src="${rec.image}" alt="Book cover">
                <div>
                    <h3>${rec.book_title}</h3>
                    <h3>Author: ${rec.author_name}</h3>
                    <p>${rec.description}</p>
                    <div class="button-group">
                        ${rec.borrow_link ? `<a href="${rec.borrow_link}" target="_blank" class="recommendation-button">Borrow</a>` : ''}
                        <a href="${rec.buy_link}" target="_blank" class="recommendation-button">View Book Details</a>
                    </div>
                    <button class="get-recommendation-button">Want recommendations?</button>
                </div>
                `;

                card.querySelector(".get-recommendation-button").addEventListener("click", () => {
                    fetchRecommendations(null, rec.book_title, rec.author_name);
                });

                div.appendChild(card);
            });

            // Reset input values
            document.getElementById('rec_title').value = '';
            document.getElementById('rec_author').value = '';
        })
        .catch(error => {
            console.error('There has been a problem with your fetch operation:', error);
            // Add additional information
            console.error('Error message:', error.message);
        });
        
    }, 2000); // delay of 2 seconds
}

function fetchBookDetails(e) {
    e.preventDefault();

    let title = document.getElementById('book').value;
    let author = document.getElementById('author').value;

    // Display loading message
    let div = document.getElementById('search_results');
    div.innerHTML = '';
    let loadingElement = document.createElement('div');
    loadingElement.classList.add('loading');
    loadingElement.textContent = 'Loading...';
    div.appendChild(loadingElement);

    fetch('/book_details', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title: title, author: author }),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('No book details found for the given title or author.');
        }
        return response.json();
    })
    .then(data => {
        div.innerHTML = ''; // Clear loading message

        data.forEach(book => {
            let card = document.createElement('div');
            card.classList.add('card');

            card.innerHTML = `
                <img src="${book.image}" alt="Book cover">
                <div>
                    <h3>${book.title}</h3>
                    <h3>Author: ${book.authors[0]}</h3>
                    <p>${book.description}</p>
                    <div class="button-group">
                        ${book.borrow_link ? `<a href="${book.borrow_link}" target="_blank" class="recommendation-button">Borrow</a>` : ''}
                        <a href="${book.buy_link}" target="_blank" class="recommendation-button">View Book Details</a>
                    </div>
                    <button class="get-recommendation-button">Want recommendations?</button>
                </div>
            `;

            let recommendationButton = card.querySelector(".get-recommendation-button");
            recommendationButton.addEventListener("click", () => {
                fetchRecommendations(null, book.title, book.authors[0]);
                // Scroll to the recommendation section
                let recommendationSection = document.getElementById('recommendation_section');
                recommendationSection.scrollIntoView({ behavior: 'smooth' });
            });

            div.appendChild(card);
        });

        // Reset input values
        document.getElementById('book').value = '';
        document.getElementById('author').value = '';
        // Scroll to the recommendation section
        let recommendationSection = document.getElementById('recommendation_section');
        recommendationSection.scrollIntoView({ behavior: 'smooth' });
    })
    .catch(error => {
        console.error('There has been a problem with your fetch operation:', error);
        loadingElement.style.display = 'none';
        let errorMessage = document.createElement('div');
        errorMessage.classList.add('error-message');
        errorMessage.textContent = error.message;
        div.appendChild(errorMessage);
    });
}

function fetchSurpriseBook() {
    // Display loading message
    let div = document.getElementById('recommendations');
    div.innerHTML = '';
    let loadingElement = document.createElement('div');
    loadingElement.classList.add('loading');
    loadingElement.textContent = 'Loading...';
    div.appendChild(loadingElement);
    
    // Retrieve the book title and author name from the input fields
    let book_title = document.getElementById('rec_title').value;
    let author_name = document.getElementById('rec_author').value;
    
    fetch('/surprise_me', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        // Include the book title and author name in the request body
        body: JSON.stringify({
            book_title: book_title,
            author_name: author_name
        })
    })
    .then(response => response.json())
    .then(data => {
        div.innerHTML = ''; // Clear loading message
    
        let book = data.recommendation; // Access the recommendation object directly
    
        let card = document.createElement('div');
        card.classList.add('card');
    
        card.innerHTML = `
            <img src="${book.image}" alt="Book cover">
            <div>
                <h3>${book.book_title}</h3>
                <h3>Author: ${book.author_name}</h3>
                <p>${book.description}</p>
                <div class="button-group">
                    ${book.canonicalVolumeLink ? `<a href="${book.canonicalVolumeLink}" target="_blank" class="recommendation-button">Buy</a>` : ''}
                    <a href="${book.buy_link}" target="_blank" class="recommendation-button">View Book Details</a>
                </div>
                <button class="get-recommendation-button">Want recommendations?</button>
            </div>
        `;
    
        let recommendationButton = card.querySelector(".get-recommendation-button");
        recommendationButton.addEventListener("click", () => {
            fetchRecommendations(null, book.book_title, book.author_name);
            // Scroll to the recommendation section
            let recommendationSection = document.getElementById('recommendation_section');
            recommendationSection.scrollIntoView({ behavior: 'smooth' });
        });
    
        div.appendChild(card);
    
        // Reset input values
        document.getElementById('rec_title').value = '';
        document.getElementById('rec_author').value = '';
        // Scroll to the recommendation section
        let recommendationSection = document.getElementById('recommendation_section');
        recommendationSection.scrollIntoView({ behavior: 'smooth' });
    })
    .catch(error => {
        console.error('There has been a problem with your fetch operation:', error);
        loadingElement.style.display = 'none';
        let errorMessage = document.createElement('div');
        errorMessage.classList.add('error-message');
        errorMessage.textContent = 'Something went wrong, please refresh the page and try again later.';
        div.appendChild(errorMessage);
    });
}

function promptUser() {
    // Check if the favorite author and genre have already been entered during this session
    if (!sessionStorage.getItem('favoriteAuthor') && !sessionStorage.getItem('favoriteGenre')) {
        const favoriteAuthor = prompt("Please enter your favorite author:");
        const favoriteGenre = prompt("Please enter your favorite genre:");

        // Save the information in the user's session storage
        sessionStorage.setItem('favoriteAuthor', favoriteAuthor);
        sessionStorage.setItem('favoriteGenre', favoriteGenre);
        
        // Print favorite author and genre in the console (or terminal if it's a Node.js app)
        console.log(`Favorite Author: ${favoriteAuthor}`);
        console.log(`Favorite Genre: ${favoriteGenre}`);

        // Make an AJAX request to the Flask app with the favorite author and genre
        fetch('/set_favorites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ favorite_author: favoriteAuthor, favorite_genre: favoriteGenre }),
        });
    }
}

// Prompt the user for their favorite author and genre when the page loads
window.onload = promptUser;


document.getElementById('surprise_me').addEventListener('click', fetchSurpriseBook);
