from flask import Flask, request, render_template, send_file
from urllib.parse import quote
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import openai
import os
import json
from fpdf import FPDF

app = Flask(__name__)

# Azure Document Intelligence configuration
document_intelligence_endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT", "https://law-doc-intelligence.cognitiveservices.azure.com/")
document_intelligence_key = os.getenv("DOCUMENT_INTELLIGENCE_KEY", "8sfzONN4gcMzT6znk9kGuJLJC61NufQmOHRagi4BP7dRcN9HdthVJQQJ99ALACYeBjFXJ3w3AAALACOGM855")
custom_model_id = "OCR"

# Create a Document Analysis client
document_analysis_client = DocumentAnalysisClient(
    endpoint=document_intelligence_endpoint,
    credential=AzureKeyCredential(document_intelligence_key)
)

# Azure OpenAI configuration
openai.api_type = "azure"
openai.api_base = os.getenv("OPENAI_API_BASE", "https://lawai3.openai.azure.com/")
openai.api_key = os.getenv("OPENAI_API_KEY", "Di5LSmZ9ZYZMHuVA0sslKacvxhb63W92r6jI1WuYykLUOhnDy51nJQQJ99ALACfhMk5XJ3w3AAABACOGgRG2")
openai.api_version = "2023-03-15-preview"

# Extract text from the custom model
def extract_text_from_custom_model(document_path):
    with open(document_path, "rb") as document_file:
        poller = document_analysis_client.begin_analyze_document(custom_model_id, document_file)
        result = poller.result()

    extracted_text = ""
    if result.pages:
        for page in result.pages:
            if page.lines:
                for line in page.lines:
                    extracted_text += f"{line.content}\n"

    return extracted_text.strip()  # Trim whitespace

def summarize_text(text):
    prompt = f"Summarize the following content:\n{text}"
    try:
        response = openai.ChatCompletion.create(
            engine="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        summary = response['choices'][0]['message']['content'].strip()
        return summary
    except Exception as e:
        print("Error during OpenAI API call for summarization:", e)
        return "Error processing text."

def answer_question(text, question):
    prompt = f"Given the following extracted content:\n{text}\n\nAnswer this question: {question}\n\nIf the answer is not present, say 'There is no information.'"
    try:
        response = openai.ChatCompletion.create(
            engine="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        answer = response['choices'][0]['message']['content'].strip()
        return answer
    except Exception as e:
        print("Error during OpenAI API call for answering question:", e)
        return "Error processing text."


# Generate PDF
def generate_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text)
    
    pdf_file_path = "extracted_text.pdf"
    pdf.output(pdf_file_path)
    return pdf_file_path

# Generate JSON
def generate_json(text):
    json_file_path = "extracted_text.json"
    with open(json_file_path, 'w') as json_file:
        json.dump({"extracted_text": text}, json_file)
    return json_file_path

# Routes
@app.route('/')
def index():
    return render_template('index.html')  # Render the upload form

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    document_path = f"./uploads/{file.filename}"
    file.save(document_path)

    extracted_text = extract_text_from_custom_model(document_path)
    summarized_text = summarize_text(extracted_text)

    return render_template('result.html', extracted_text=extracted_text, summarized_text=summarized_text)

@app.route('/answer', methods=['POST'])
def answer():
    question = request.form.get('question')
    extracted_text = request.form.get('extracted_text')

    if not question or not extracted_text:
        return "Question or extracted text not found", 400

    answer = answer_question(extracted_text, question)

    return render_template('result.html', extracted_text=extracted_text, summarized_text=None, answer=answer)

@app.route('/download/pdf', methods=['GET'])
def download_pdf():
    extracted_text = request.args.get('extracted_text')
    pdf_file_path = generate_pdf(extracted_text)
    return send_file(pdf_file_path, as_attachment=True)

@app.route('/download/json', methods=['GET'])
def download_json():
    extracted_text = request.args.get('extracted_text')
    json_file_path = generate_json(extracted_text)
    return send_file(json_file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5002)
