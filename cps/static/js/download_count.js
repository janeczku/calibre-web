document.addEventListener("DOMContentLoaded", function () {
    console.log("download_count.js is running...");

    let countElement = document.getElementById("download-count");

    if (!countElement) {
        console.error(" No element with id 'download-count' found.");
        return;
    }

    let bookId = countElement.dataset.bookId;
    console.log("Book ID:", bookId); // Debugging Log

    if (!bookId || bookId === "undefined") {
        console.error(" Book ID is missing or undefined.");
        countElement.innerText = "Error: Book ID Missing";
        return;
    }

    fetch(`http://localhost:5000/download_count/${bookId}`)
        .then(response => response.json())
        .then(data => {
            console.log("API Response:", data);
            if (data.download_count !== undefined) {
                countElement.innerText = data.download_count;
            } else {
                countElement.innerText = "Not Available";
            }
        })
        .catch(error => {
            console.error(" Failed to load download count:", error);
            countElement.innerText = "Error";
        });
});
