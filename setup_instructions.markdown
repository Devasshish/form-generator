# Setup Instructions for Google Form Generator

## Prerequisites
- Python 3.8 or higher
- Google Cloud account with Forms API enabled
- `credentials.json` file from Google Cloud Console

## Setup Steps
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Google API Setup**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a new project or select an existing one.
   - Enable the Google Forms API.
   - Create OAuth 2.0 credentials (select "Desktop app" as the application type).
   - Download the `credentials.json` file and place it in the same directory as `google_form_generator.py`.

3. **Run the Application**:
   ```bash
   python google_form_generator.py
   ```

4. **Access the App**:
   - Open a browser and navigate to `http://localhost:5000`.
   - Upload a PDF file with questions in the specified format.
   - The app will parse the PDF, create a Google Form, and redirect you to the form's edit page.

5. **PDF Format**:
   Ensure the PDF follows this format for each question:
   ```
   Q1: What is the capital of France?
   A) Florida
   B) Paris
   C) Texas
   D) Berlin
   Correct: B
   ```

## Notes
- The first time you run the app, it will prompt you to authenticate with Google via a browser window.
- Ensure the PDF is text-based (not scanned) for accurate parsing.
- If you encounter errors, check the console for details or verify the PDF format.

## Troubleshooting
- **Invalid PDF format**: Ensure the PDF matches the required structure.
- **API authentication failed**: Verify `credentials.json` is correct and the Forms API is enabled.
- **No questions found**: Check that the PDF contains text and follows the specified format.