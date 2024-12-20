import os
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, SpeechRecognizer, AudioConfig, ResultReason
import openai
import time


# Flask App Setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "static"  # Set static folder for TTS files

# Azure Cognitive Search Configuration
SEARCH_ENDPOINT = "https://law-search-service.search.windows.net"
SEARCH_API_KEY = "pQQFie7dfDSFotL3v1YKzaG3hbghz09QWCBtUUnOzAAzSeBeJNbq"
SEARCH_INDEX_NAME = "vector"

search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=SEARCH_INDEX_NAME,
    credential=AzureKeyCredential(SEARCH_API_KEY)
)

# Azure OpenAI Configuration
openai.api_type = "azure"
openai.api_base = os.getenv("OPENAI_API_BASE", "https://kanik-m4pm6cwu-eastus2.openai.azure.com/")
openai.api_key = os.getenv("OPENAI_API_KEY", "2LAkM3faiNPwL1rfuKB6M1aW7kaCxyDUfJZSTfwqOW0x6akQMYR1JQQJ99ALACHYHv6XJ3w3AAAAACOGVZrJ")
openai.api_version = "2023-03-15-preview"
OPENAI_ENGINE = "gpt-4-2"

# Azure Speech Configuration
SPEECH_KEY = "BQW0S1ayh3huusZU1mUK938jlHYXOVOOy2xfRa2jx4rztftbXpm6JQQJ99ALACYeBjFXJ3w3AAAYACOGi3oZ"
SPEECH_REGION = "eastus"
speech_config = SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)

# Query Cognitive Search
def query_search(query, retries=3):
    attempt = 0
    while attempt < retries:
        try:
            results = search_client.search(
                search_text=query,
                include_total_count=True,
                query_type="simple",
                top=10
            )

            if results.get_count() == 0:
                return []

            sections = []
            for doc in results:
                section_text = doc.get('section', 'N/A')
                chunk = doc.get('chunk', 'N/A')
                title = doc.get('title', 'N/A')

                sections.append({
                    "title": title,
                    "section": section_text,
                    "content": chunk
                })

            return sections

        except Exception as e:
            print(f"Search error: {str(e)}")
            attempt += 1
            time.sleep(2)  # Wait for 2 seconds before retrying

    return f"Error querying search index after {retries} retries: {str(e)}"


# Generate answers using Azure OpenAI
def generate_openai_response(question, search_results=None, retries=3):
    attempt = 0
    while attempt < retries:
        try:
            if search_results:
                formatted_content = "\n".join(
                    f"Title: {res['title']}\nSection: {res['section']}\nContent: {res['content']}"
                    for res in search_results
                )
                messages = [
                    {"role": "system", "content": "You are a legal assistant AI. Use the following content to answer the question concisely and in an organized manner."},
                    {"role": "user", "content": f"Question: {question}\nRelevant Sections:\n{formatted_content}\nProvide a detailed answer with references to the relevant sections and content."}
                ]
            else:
                messages = [
                    {"role": "system", "content": "You are a legal assistant AI."},
                    {"role": "user", "content": f"Question: {question}\nProvide a detailed, relevant, and concise answer."}
                ]

            response = openai.ChatCompletion.create(
                engine=OPENAI_ENGINE,
                messages=messages,
                max_tokens=500
            )

            if not response or 'choices' not in response or not isinstance(response['choices'], list):
                return "OpenAI response format is invalid."

            return response['choices'][0]['message']['content'].strip()

        except Exception as e:
            print(f"OpenAI error: {str(e)}")
            attempt += 1
            time.sleep(2)  # Wait for 2 seconds before retrying

    return f"Error querying OpenAI after {retries} retries: {str(e)}"

# Text-to-Speech Function
def text_to_speech(text, language="en-US", output_file="static/output.wav"):
    try:
        # Set the language for speech synthesis
        speech_config.speech_synthesis_language = language

        # Set up the audio output to a file
        audio_config = AudioConfig(filename=output_file)

        # Initialize the speech synthesizer
        synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

        # Perform text-to-speech synthesis
        result = synthesizer.speak_text_async(text).get()

        # Check if the result is successful
        if result.reason == ResultReason.SynthesizingAudioCompleted:
            return output_file  # Return the file path for the generated audio
        else:
            return f"Error in TTS: {result.reason}"

    except Exception as e:
        print(f"TTS error: {str(e)}")
        return f"Error in TTS: {str(e)}"

# Speech-to-Text Function
def speech_to_text(language="en-US"):
    try:
        speech_config.speech_recognition_language = language
        recognizer = SpeechRecognizer(speech_config=speech_config)
        print("Speak into your microphone...")
        result = recognizer.recognize_once_async().get()

        if result.reason == ResultReason.RecognizedSpeech:
            return result.text
        elif result.reason == ResultReason.NoMatch:
            return "No speech recognized."
        else:
            return f"Error in STT: {result.reason.name}"  # Use .name to get the reason as a string
    except Exception as e:
        print(f"STT error: {str(e)}")
        return f"Error in STT: {str(e)}"


# Routes
@app.route("/",endpoint="home")
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask_question():
    try:
        data = request.json
        question = data.get("question", "").strip()
        language = data.get("language", "en-US")

        if not question:
            return jsonify({"message": "Question cannot be empty!"}), 400

        search_results = query_search(question)
        if not search_results:
            answer = generate_openai_response(question)
        else:
            answer = generate_openai_response(question, search_results)

        if "Error" in answer:
            return jsonify({"message": "Error generating answer from OpenAI!"}), 500

        # Convert answer to speech
        audio_path = text_to_speech(answer, language)
        if "Error" in audio_path:
            return jsonify({"message": audio_path}), 500

        return jsonify({"answer": answer, "audio_url": f"/{audio_path}"}), 200

    except Exception as e:
        print(f"Internal Server Error: {str(e)}")
        return jsonify({"message": f"Internal Server Error: {str(e)}"}), 500

@app.route("/stt", methods=["POST"])
def stt():
    try:
        language = request.json.get("language", "en-US")
        recognized_text = speech_to_text(language)
        return jsonify({"text": recognized_text}), 200
    except Exception as e:
        print(f"STT error: {str(e)}")
        return jsonify({"message": f"Error in Speech-to-Text: {str(e)}"}), 500
        
@app.route("/tts", methods=["POST"])
def tts():
    try:
        data = request.json
        text = data.get("text", "").strip()
        language = data.get("language", "en-US")
        
        if not text:
            return jsonify({"message": "Text cannot be empty!"}), 400

        # Convert text to speech and return the audio file path
        audio_path = text_to_speech(text, language)
        if "Error" in audio_path:
            return jsonify({"message": audio_path}), 500
        
        # Send back the audio file as a response
        return send_file(audio_path, mimetype="audio/wav")
    
    except Exception as e:
        print(f"Error in TTS route: {str(e)}")
        return jsonify({"message": f"Error in TTS: {str(e)}"}), 500

@app.route("/back", methods=["GET"])
def back():
    return redirect("http://127.0.0.1:5000/")

@app.route("/Project2", methods=["GET"])
def second_project():
    return render_template("index.html")



if __name__ == "__main__":
    app.run(debug=True,port=5001)