document.addEventListener("DOMContentLoaded", function () {
    console.log("✅ Chatbot script loaded!");

    // Get UI elements
    const sendButton = document.getElementById("chatbot-send");
    const userInput = document.getElementById("chatbot-input");
    const chatbox = document.getElementById("chatbot-messages");
    const fileUpload = document.getElementById("chatbot-upload");

    // Validate UI elements
    if (!sendButton || !userInput || !chatbox || !fileUpload) {
        console.error("❌ Error: Missing UI elements!");
        return;
    }

    console.log("✅ UI elements initialized successfully!");

    // Function to append messages to the chatbox
    function appendMessage(sender, message, isError = false) {
        const messageClass = sender === "You" ? "text-blue-600" : isError ? "text-red-500" : "text-gray-700";
        chatbox.innerHTML += `
            <div class="mb-2">
                <p class="${messageClass}"><strong>${sender}:</strong> ${message}</p>
            </div>
        `;
        chatbox.scrollTop = chatbox.scrollHeight; // Auto-scroll
    }

    // Function to send a message
    async function sendMessage() {
        const userMessage = userInput.value.trim();
        if (!userMessage) {
            console.warn("⚠️ Warning: Empty message!");
            return;
        }

        appendMessage("You", userMessage);
        userInput.value = ""; // Clear input

        let apiUrl = "http://127.0.0.1:8000/chatbot";
        let options = {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: userMessage }),
        };

        // ✅ If the query is about PDF, use `/ask` (GET request)
        if (userMessage.toLowerCase().includes("pdf") || userMessage.toLowerCase().includes("summarize")) {
            apiUrl = `http://127.0.0.1:8000/ask?query=${encodeURIComponent(userMessage)}`;
            options = { method: "GET" }; // GET request doesn't need a body
        }

        try {
            console.log(`📨 Sending request to ${apiUrl}...`);
            const response = await fetch(apiUrl, options);
            const data = await response.json();
            console.log("✅ Response received:", data);

            appendMessage("Bot", data.response || data.reply || "❌ No response received.", !data.response && !data.reply);
        } catch (error) {
            console.error("❌ Error fetching response:", error);
            appendMessage("Bot", "❌ Error connecting to chatbot.", true);
        }
    }

    // Event listeners
    sendButton.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {  // Prevents duplicate sending
            event.preventDefault();
            sendMessage();
        }
    });

    console.log("✅ Chatbot event listeners attached!");

    // Event listeners
    sendButton.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {  // Prevents duplicate sending
            event.preventDefault();
            sendMessage();
        }
    });

    console.log("✅ Chatbot event listeners attached!");

    // Function to handle file upload
    function handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        console.log(`📂 File selected: ${file.name}`);

        const formData = new FormData();
        formData.append("file", file);

        fetch("/upload-pdf", {  // Change to your actual upload API endpoint
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log("✅ File uploaded successfully:", data);
            appendMessage("Bot", `📂 File "${file.name}" uploaded successfully!`);
        })
        .catch(error => {
            console.error("❌ File upload error:", error);
            appendMessage("Bot", "❌ Error uploading file.", true);
        });
    }

    // Attach event listener for file uploads
    fileUpload.addEventListener("change", handleFileUpload);
});

async function sendMessage() {
    const userMessage = document.getElementById("user-input").value.trim();
    const chatDisplay = document.getElementById("chatbot-response");

    if (!userMessage) {
        chatDisplay.innerText = "Please enter a message!";
        return;
    }

    let apiUrl = "http://127.0.0.1:8000/chatbot";
    let options = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
    };

    // ✅ If the query is about PDF, use `/ask` (GET request)
    if (userMessage.toLowerCase().includes("pdf") || userMessage.toLowerCase().includes("summarize")) {
        apiUrl = `http://127.0.0.1:8000/ask?query=${encodeURIComponent(userMessage)}`;
        options = { method: "GET" };  // GET request doesn't need a body
    }

    try {
        const response = await fetch(apiUrl, options);
        const data = await response.json();

        // ✅ Display the chatbot response
        chatDisplay.innerText = data.response || data.reply || "No response received.";
    } catch (error) {
        console.error("Error fetching response:", error);
        chatDisplay.innerText = "Error connecting to chatbot.";
    }
}
