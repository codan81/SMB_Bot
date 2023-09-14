document.addEventListener("DOMContentLoaded", function () {
    const chatMessages = document.getElementById("chat-messages");
    const userInput = document.getElementById("user-input");
    const sendButton = document.getElementById("send-button");

    // Function to smoothly scroll to the bottom of the chat container
function scrollToBottomSmoothly() {
    const scrollContainer = document.getElementById("chat-messages");
    const scrollHeight = scrollContainer.scrollHeight;
    const scrollTop = scrollContainer.scrollTop;
    const duration = 2000; // Slower scrolling duration in milliseconds
    const startTime = Date.now();

    function animateScroll() {
        const currentTime = Date.now();
        const elapsedTime = currentTime - startTime;

        if (elapsedTime < duration) {
            const scrollProgress = Math.min(elapsedTime / duration, 1);
            scrollContainer.scrollTop = scrollTop + scrollProgress * (scrollHeight - scrollTop);
            requestAnimationFrame(animateScroll);
        } else {
            scrollContainer.scrollTop = scrollHeight;
        }
    }

    requestAnimationFrame(animateScroll);
}



    // Event listener for sending user input on Enter key press
    userInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault(); // Prevent Enter from creating newlines
            sendButton.click(); // Trigger the "Send" button click
        }
    });

    // Function to display messages in the chat interface
    function displayMessages(messages, isUserMessage) {
        messages.forEach(function (message) {
            const messageElement = document.createElement("div");
            messageElement.className = isUserMessage ? "user-message" : "bot-message";
            messageElement.innerHTML = message; // Use innerHTML to render HTML content
            chatMessages.appendChild(messageElement);
            
            // Scroll to the bottom smoothly when a message is added
            scrollToBottomSmoothly();
        });
    }

    // Function to send the user's message to the server
    function sendUserMessage(message) {
        // Make an AJAX request to your Flask server
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/chat", true);
        xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4 && xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                // Split the response by "<br><br>" to handle separate messages
                const botMessages = response.response.split("<br><br>");
                // Display the bot's messages in the chat
                displayMessages(botMessages, false); // Not a user message
            }
        };
        xhr.send("user_input=" + encodeURIComponent(message));
    }

    // Event listener for sending user input
    sendButton.addEventListener("click", function () {
        console.log("Send button clicked."); // Debugging statement
        const userMessage = userInput.value.trim(); // Get the user's message
        console.log("User message:", userMessage); // Debugging statement
        if (userMessage !== "") {
            // Display the user's message in the chat
            displayMessages([customer_name + ": " + userMessage], true); // User message
            // Send the user's message to the server
            sendUserMessage(userMessage);
            // Clear the input field
            userInput.value = "";
        }
    });
});
