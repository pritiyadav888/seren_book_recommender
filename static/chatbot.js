// Get elements
const recommendationForm = document.getElementById("recommendationForm");
const loginBox = document.getElementById("login-box");
const cardBox = document.querySelector(".cardBox");
const backButton = document.getElementById("backButton");
const bookNameInput = document.getElementById("book_name");
const bookSuggestionsList = document.getElementById("book_suggestions");
const progressBar = document.getElementById("progressBar");

const consentBanner = document.getElementById("cookieConsentBanner");
const consentYes = document.getElementById("cookieConsentYes");
const consentNo = document.getElementById("cookieConsentNo");

// Initially set consent to null
let consent = null;

// Yes button event
consentYes.onclick = function () {
  consent = true;
  consentBanner.style.display = "none";
  // Save consent to localStorage
  localStorage.setItem("consent", JSON.stringify(true));
};

// No button event
consentNo.onclick = function () {
  consent = false;
  consentBanner.style.display = "none";
  // Save consent to localStorage
  localStorage.setItem("consent", JSON.stringify(false));
};

// Check if user has given consent before
if (localStorage.getItem("consent")) {
  // User has given consent before
  consent = JSON.parse(localStorage.getItem("consent"));
} else {
  // User hasn't given consent before, show consent banner
  consentBanner.style.display = "block";
}

// Back button click event
backButton.onclick = showLoginForm;

// Show card
function showCard() {
  loginBox.style.display = "none";
  cardBox.style.display = "block";
}

// Show login form
function showLoginForm() {
  loginBox.style.display = "block";
  cardBox.style.display = "none";
}

// Fetch data from the server
async function fetchData(url, body) {
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`Fetch Error: ${error}`);
    throw error;
  }
}

// Form submit event
recommendationForm.addEventListener("submit", async function (e) {
  e.preventDefault();
  progressBar.style.display = "block";

  const bookName = bookNameInput.value;
  const mood = document.getElementById("mood").value;

  let recommendations = [];
  if (consent) {
    recommendations = getCookie("recommendations");
  } else {
    recommendations = localStorage.getItem("recommendations");
  }

  try {
    if (recommendations) {
      console.log(recommendations); // Print the recommendations before parsing
      recommendations = JSON.parse(recommendations);
    } else {
      recommendations = [];
    }
  } catch (error) {
    console.error("Error parsing recommendations: ", error);
  }

  try {
    const data = await fetchData("/", {
      book_name: bookName,
      mood: mood,
      recommendations: recommendations,
    });
    progressBar.style.display = "none";
    handleRecommendationResponse(data);
  } catch (error) {
    progressBar.style.display = "none";
    console.error(`Fetch Error: ${error}`);
  }
});

// Handle recommendation response
function handleRecommendationResponse(data) {
  const recommendedBookImage = document.getElementById("recommendedBookImage");
  const recommendedBookTitle = document.getElementById("recommendedBookTitle");
  const recommendedBookAuthor = document.getElementById(
    "recommendedBookAuthor"
  );
  const recommendedBookBuyLink = document.getElementById(
    "recommendedBookBuyLink"
  );
  const chatbotRecommendation = document.getElementById("chatbotResponse");

  if (data.recommended_book_details) {
    recommendedBookImage.src = data.recommended_book_details.image;
    recommendedBookTitle.textContent = data.recommended_book_details.title;
    recommendedBookAuthor.textContent = data.recommended_book_details.authors
      ? data.recommended_book_details.authors.join(", ")
      : "";
    recommendedBookBuyLink.href = data.recommended_book_details.buy_link;
    chatbotRecommendation.textContent = data.chatbot_response;
    console.log(
      "recommendations",
      JSON.stringify(data.recommended_book_details)
    );
    // If the user consents, use cookies
    if (consent) {
      setCookie(
        "recommendations",
        JSON.stringify(data.recommended_book_details),
        7
      );
    }
    // If the user does not consent, use localStorage
    else {
      localStorage.setItem(
        "recommendations",
        JSON.stringify(data.recommended_book_details)
      );
    }
  } else {
    recommendedBookImage.src = "";
    recommendedBookTitle.textContent = "No recommendation found";
    recommendedBookAuthor.textContent = "";
    recommendedBookBuyLink.href = "";
    chatbotRecommendation.textContent = "No recommendation found.";
  }

  showCard();
}

// Book name input event
bookNameInput.addEventListener("input", async function (e) {
  const partialName = e.target.value;

  if (!consent) {
    const recommendations = localStorage.getItem("recommendations");
    if (recommendations) {
      console.log(JSON.parse(recommendations));
    }
  }

  try {
    const data = await fetchData("/get_suggestions", {
      partial_name: partialName,
    });
    console.log(data);
    updateBookSuggestions(data.suggestion);
  } catch (error) {
    console.error(`Fetch Error: ${error}`);
  }
});

// Function to set cookie
function setCookie(name, value, days) {
  var expires = "";
  if (days) {
    var date = new Date();
    date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
    expires = "; expires=" + date.toUTCString();
  }
  document.cookie = name + "=" + (value || "") + expires + "; path=/";
}

// Function to get cookie
function getCookie(name) {
  var nameEQ = name + "=";
  var ca = document.cookie.split(";");
  for (var i = 0; i < ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0) == " ") c = c.substring(1, c.length);
    if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
  }
  return null;
}

function updateBookSuggestions(suggestion) {
  if (suggestion) {
    let suggestions = suggestion.replace(":\n\n", "").split("\n");

    if (Array.isArray(suggestions)) {
      bookSuggestionsList.innerHTML = "";

      suggestions.forEach((suggestion) => {
        let option = document.createElement("option");
        let formattedSuggestion = suggestion.trim().replace(/^\d+\.\s*/, "");
        option.value = formattedSuggestion;
        bookSuggestionsList.appendChild(option);
      });

      bookNameInput.setAttribute("list", "book_suggestions");
    }
  }
}

document.addEventListener("DOMContentLoaded", function() {
    const shareIcons = document.querySelectorAll(".share-icon");
  
    shareIcons.forEach(function(icon) {
      icon.addEventListener("click", function(event) {
        event.preventDefault();
  
        const platform = icon.getAttribute("data-platform");
        const bookTitle = document.getElementById("recommendedBookTitle").textContent;
        const bookAuthor = document.getElementById("recommendedBookAuthor").textContent;
        const bookBuyLink = document.getElementById("recommendedBookBuyLink").getAttribute("href");
  
        let shareUrl;
  
        // Define the share URL based on the chosen platform
        switch (platform) {
          case "telegram":
            shareUrl = `https://t.me/share/url?url=${bookBuyLink}&text=${bookTitle} by ${bookAuthor}`;
            break;
          case "instagram":
            shareUrl = `https://www.instagram.com/?url=${bookBuyLink}`;
            break;
          case "whatsapp":
            shareUrl = `https://api.whatsapp.com/send?text=${bookTitle} by ${bookAuthor}%0A${bookBuyLink}`;
            break;
          case "twitter":
            shareUrl = `https://twitter.com/intent/tweet?text=${bookTitle} by ${bookAuthor}&url=${bookBuyLink}`;
            break;
          default:
            break;
        }
  
        if (shareUrl) {
          window.open(shareUrl);
        }
      });
    });
  });
  
