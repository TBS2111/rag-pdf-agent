const QUESTION_INPUT_ID = "question";
const RESULT_DIV_ID = "result";
const FILE_INPUT_ID = "pdfFile";
const UPLOAD_STATUS_ID = "uploadStatus";

const ASK_ENDPOINT = "/ask";
const UPLOAD_ENDPOINT = "/upload-pdf";

async function uploadPDF() {
    const fileInput = document.getElementById(FILE_INPUT_ID);
    const statusDiv = document.getElementById(UPLOAD_STATUS_ID);
    const uploadBtn = document.getElementById("uploadBtn");

    if (!fileInput.files || fileInput.files.length === 0) {
        statusDiv.className = "status-msg status-error";
        statusDiv.innerHTML = "Please select a PDF file first.";
        return;
    }

    const file = fileInput.files[0];
    if (!file.name.endsWith(".pdf")) {
        statusDiv.className = "status-msg status-error";
        statusDiv.innerHTML = "Only PDF files are supported.";
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    statusDiv.className = "status-msg";
    statusDiv.innerHTML = "Uploading and parsing PDF chunks...";
    uploadBtn.disabled = true;

    try {
        const response = await fetch(UPLOAD_ENDPOINT, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.status === "success") {
            statusDiv.className = "status-msg status-success";
            statusDiv.innerHTML = `✅ Successfully indexed <b>${data.filename}</b> into <b>${data.chunks_indexed}</b> chunks!`;
            fileInput.value = ""; // Reset file picker
        } else {
            statusDiv.className = "status-msg status-error";
            statusDiv.innerHTML = `❌ Failed: ${data.error || "Could not process PDF."}`;
        }
    } catch (error) {
        statusDiv.className = "status-msg status-error";
        statusDiv.innerHTML = "❌ Error uploading PDF file.";
        console.error(error);
    } finally {
        uploadBtn.disabled = false;
    }
}

async function askQuestion() {
    const questionInput = document.getElementById(QUESTION_INPUT_ID);
    const resultDiv = document.getElementById(RESULT_DIV_ID);
    const askBtn = document.getElementById("askBtn");

    const question = questionInput.value.trim();

    if (!question) {
        resultDiv.style.display = "block";
        resultDiv.innerHTML = "Please enter a question.";
        return;
    }

    resultDiv.style.display = "block";
    resultDiv.innerHTML = "Thinking...";
    askBtn.disabled = true;

    try {
        const response = await fetch(ASK_ENDPOINT, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question
            })
        });

        const data = await response.json();

        resultDiv.innerHTML = `
<b>Answer:</b><br>${data.answer}

<br><br>
<span class="meta-tag">Source: ${data.source}</span>
<span class="meta-tag">Latency: ${data.response_time_ms} ms</span>
${data.matched_question ? `<br><small><b>Matched Cache Q:</b> ${data.matched_question}</small>` : ''}
`;
    } catch (error) {
        resultDiv.innerHTML = "Something went wrong sending the query.";
        console.error(error);
    } finally {
        askBtn.disabled = false;
    }
}