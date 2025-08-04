import os
import re
import pdfplumber
from flask import Flask, request, redirect, render_template_string, flash
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import tempfile
import uuid
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure key

SCOPES = ['https://www.googleapis.com/auth/forms.body']
creds = None

def get_google_credentials():
    global creds
    try:
        if not creds:
            logger.info("Initializing Google API credentials")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            logger.info("Credentials obtained successfully")
        return creds
    except FileNotFoundError:
        logger.error("credentials.json not found")
        raise Exception("Missing credentials.json file.")
    except Exception as e:
        logger.error(f"Google credentials error: {str(e)}")
        if "access_denied" in str(e).lower():
            raise Exception("Google API access denied. Add your email to Test Users in OAuth consent screen.")
        raise

def parse_pdf(pdf_path):
    logger.info(f"Parsing PDF: {pdf_path}")
    questions = []
    pdf = None
    try:
        pdf = pdfplumber.open(pdf_path)
        text = ''
        for page in pdf.pages:
            page_text = page.extract_text()
            if not page_text:
                logger.warning("No text found on page")
                continue
            text += page_text + '\n'
        logger.debug(f"Extracted text:\n{text[:1000]}...")

        # Regex supports "Answer:" and "Correct:" prefixes
        pattern = r'(?:Q?\d+[.:]?\s*(.*?))\n\s*A\)\s*(.*?)\n\s*B\)\s*(.*?)\n\s*C\)\s*(.*?)\n\s*D\)\s*(.*?)\n\s*(?:Answer|Correct):\s*([ABCDabcd])'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

        if not matches:
            raise ValueError("No valid questions found. Ensure PDF follows required format.")

        for match in matches:
            question = {
                'text': re.sub(r'\s+', ' ', match[0]).strip(),
                'options': [match[1].strip(), match[2].strip(), match[3].strip(), match[4].strip()],
                'correct': match[5].upper()
            }
            questions.append(question)
        logger.info(f"Found {len(questions)} questions.")
        return questions
    finally:
        if pdf:
            pdf.close()

def create_google_form(questions):
    logger.info("Creating Google Form...")
    try:
        service = build('forms', 'v1', credentials=get_google_credentials())

        # Create the form
        form = {
            'info': {
                'title': f'Quiz Form {uuid.uuid4()}',
                'documentTitle': 'Generated Quiz'
            }
        }
        result = service.forms().create(body=form).execute()
        form_id = result['formId']
        logger.info(f"Form created with ID: {form_id}")

        # Batch update to enable quiz mode
        enable_quiz = {
            "updateSettings": {
                "settings": {
                    "quizSettings": {
                        "isQuiz": True
                    }
                },
                "updateMask": "quizSettings.isQuiz"
            }
        }

        service.forms().batchUpdate(
            formId=form_id,
            body={"requests": [enable_quiz]}
        ).execute()
        logger.info("Quiz mode enabled.")

        # Add questions
        requests = []
        for idx, q in enumerate(questions):
            correct_idx = ord(q['correct']) - ord('A')
            requests.append({
                'createItem': {
                    'item': {
                        'title': q['text'],
                        'questionItem': {
                            'question': {
                                'required': True,
                                'choiceQuestion': {
                                    'type': 'RADIO',
                                    'options': [{'value': opt} for opt in q['options']],
                                },
                                'grading': {
                                    'pointValue': 1,
                                    'correctAnswers': {
                                        'answers': [{'value': q['options'][correct_idx]}]
                                    }
                                }
                            }
                        }
                    },
                    'location': {'index': idx}
                }
            })

        service.forms().batchUpdate(
            formId=form_id,
            body={'requests': requests}
        ).execute()
        logger.info("Questions added.")

        return f'https://docs.google.com/forms/d/{form_id}/edit'
    except HttpError as e:
        logger.error(f"Google API error: {e}")
        raise Exception(f"Failed to create Google Form: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

@app.route('/', methods=['GET', 'POST'])
def upload_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded')
            return redirect(request.url)

        file = request.files['file']
        if not file.filename.endswith('.pdf'):
            flash('Only PDF files allowed')
            return redirect(request.url)

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file_path = temp_file.name
        try:
            file.save(temp_file_path)
            questions = parse_pdf(temp_file_path)
            if not questions:
                flash('No valid questions found')
                return redirect(request.url)

            form_url = create_google_form(questions)
            return redirect(form_url)

        except Exception as e:
            extracted_text = ""
            try:
                with pdfplumber.open(temp_file_path) as pdf:
                    for page in pdf.pages:
                        if page.extract_text():
                            extracted_text += page.extract_text() + '\n'
            except:
                pass

            error_msg = f"Error processing PDF: {str(e)}"
            if extracted_text:
                error_msg += f"\nExtracted text was:\n{extracted_text[:1000]}..."
            flash(error_msg)
            return redirect(request.url)
        finally:
            temp_file.close()
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Could not delete temporary file: {e}")
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google Form Generator</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
            .error { color: red; white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <h1>Google Form Generator</h1>
        <p>Upload a PDF with questions in this format:</p>
        <pre>
1. Question text
A) Option 1
B) Option 2
C) Option 3
D) Option 4
Answer: B
        </pre>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" required>
            <button type="submit">Generate Form</button>
        </form>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                <p class="error">{{ messages[0] }}</p>
            {% endif %}
        {% endwith %}
    </body>
    </html>
    ''')

if __name__ == '__main__':
    logger.info("Starting Flask app")
    app.run(debug=True)
