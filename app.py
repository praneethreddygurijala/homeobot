from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import requests
import os
import traceback
import json
import re
import bleach

load_dotenv()

app = Flask(__name__)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"  # Updated model

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/consult', methods=['POST'])
def consult():
    try:
        app.logger.info("Received /api/consult request")
        data = request.get_json()

        if not data:
            app.logger.error("No JSON data received")
            return jsonify({"error": "No data received"}), 400

        age = data.get('age')
        gender = data.get('gender')
        symptoms = data.get('symptoms')

        if not all([age, gender, symptoms]):
            app.logger.error(f"Missing parameters: age={age}, gender={gender}, symptoms={symptoms}")
            return jsonify({"error": "Missing parameters: age, gender, and symptoms are required"}), 400

        try:
            age = int(age)
        except ValueError:
            app.logger.error(f"Invalid age: {age}")
            return jsonify({"error": "Invalid age: Age must be an integer"}), 400

        symptoms = symptoms.replace('\n', ' ').replace('\r', ' ')
        symptoms = symptoms[:500]
        app.logger.info(f"Sanitized symptoms: {symptoms}")

        prompt = f"""Act as an expert homeopathy doctor, basing your recommendations STRICTLY on the teachings of James Tyler Kent's Repertory and other classic homeopathic texts (e.g., Boericke's Materia Medica). Given a {age}-year-old {gender} patient's symptoms, provide a brief repertorization table and remedy selection.

Symptoms: {symptoms}

Format your response as follows:
[instruction: Output MUST be clean Markdown with no HTML, inline CSS, colors, or excessive formatting (e.g., *** or ****). Use exactly two asterisks (**) for bold text (section titles, remedy names, and 'Total' in table). Ensure table columns are aligned with consistent spacing (pad each column to 12 characters). Use only the structure below, with no extra text or deviations. Replace placeholders with actual data.]
## Repertorization Table
| Symptom            |  Remedy 1  | Remedy 2   | Remedy 3   | Remedy 4   | Remedy 5   |sooo on....|
|--------------------|------------|------------|------------|------------|------------|
| [Symptom 1]        | [score]    | [score]    | [score]    | [score]    | [score]    |
| [Symptom 2]        | [score]    | [score]    | [score]    | [score]    | [score]    |
| [Symptom 3]        | [score]    | [score]    | [score]    | [score]    | [score]    |
| [Symptom 4]        | [score]    | [score]    | [score]    | [score]    | [score]    |
| [.]                | [score]    | [score]    | [score]    | [score]    | [score]    |
| [.]                | [score]    | [score]    | [score]    | [score]    | [score]    |
| [.]  soo on ...... | [score]    | [score]    | [score]    | [score]    | [score]    |
| **Total**          | **[score]**| **[score]**| **[score]**| **[score]**| **[score]**|

## Rubrics
- **[Rubric 1]** ([Source], [Section], [Subsection], [page number]): [Remedy] ([score])
- **[Rubric 2]** ([Source], [Section], [Subsection], [page number]): [Remedy] ([score])
- **[Rubric 3]** ([Source], [Section], [Subsection], [page number]): [Remedy] ([score])
- **[Rubric 4]** ([Source], [Section], [Subsection], [page number]): [Remedy] ([score])
- ...

## Remedy Selection
**Best Remedy**: **[REMEDY_NAME]**
- Justification: [Brief justification based on table scores, 1-2 sentences. If no clear remedy, state 'No clear remedy selection possible'.]

## Dosage Instructions
- [Brief dosage instructions, 1 sentence.]

## Precautions
- [Symptom 1]: [Brief precaution, 1 sentence.]
- [Symptom 2]: [Brief precaution, 1 sentence.]
- [Symptom 3]: [Brief precaution, 1 sentence.]
- [Symptom 4]: [Brief precaution, 1 sentence.]
    so on......
## Alternative Remedies
- *[Remedy 1]*
- *[Remedy 2]*
- *[Remedy 3]*
  soo on......
"""

        app.logger.info(f"GEMINI_API_KEY: {'set' if GEMINI_API_KEY else 'not set'}")
        if not GEMINI_API_KEY:
            app.logger.error("GEMINI_API_KEY is not set in environment variables")
            return jsonify({"error": "Oops! Something went wrong on our end. Please try again later."}), 500

        payload = {
            "contents": [{
                "role": "user",
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.0,
                "topK": 1,
                "topP": 1.0
            }
        }
        app.logger.info(f"Payload to Gemini API: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(
                f"{API_URL}?key={GEMINI_API_KEY}",
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=10  # Add timeout
            )
            response.raise_for_status()
            app.logger.info(f"Gemini API Response Status: {response.status_code}")
            app.logger.debug(f"Gemini API Response Headers: {response.headers}")
            app.logger.debug(f"Gemini API Raw Response Text: {response.text}")

            try:
                result = response.json()
                app.logger.debug(f"Gemini API Parsed JSON: {json.dumps(result, indent=2)}")
            except json.JSONDecodeError as e:
                app.logger.error(f"Failed to decode JSON from API response: {str(e)}")
                return jsonify({"error": f"Oops! Something went wrong on our end. Please try again later."}), 500

            if 'candidates' in result and len(result['candidates']) > 0 and 'content' in result['candidates'][0] and 'parts' in result['candidates'][0]['content'] and len(result['candidates'][0]['content']['parts']) > 0:
                generated_text = result['candidates'][0]['content']['parts'][0]['text']
                # Sanitize with bleach and regex
                generated_text = bleach.clean(generated_text, tags=[], attributes={}, strip=True)
                generated_text = re.sub(r'\*{3,}', '**', generated_text)  # Normalize excessive bolding
                generated_text = re.sub(r'!\[.*?\]\(.*?\)', '', generated_text)  # Remove images
                generated_text = re.sub(r'```[\s\S]*?```', '', generated_text)  # Remove code blocks
                app.logger.info(f"Sanitized generated text: {generated_text}")
                return jsonify({"response": generated_text})
            else:
                app.logger.error(f"Unexpected structure in Gemini API response: {json.dumps(result, indent=2)}")
                return jsonify({"error": "Oops! Something went wrong on our end. Please try again later."}), 500

        except requests.exceptions.Timeout:
            app.logger.error("API request timed out")
            return jsonify({"error": "Oops! Something went wrong on our end. Please try again later."}), 500
        except requests.exceptions.HTTPError as e:
            app.logger.error(f"API request failed with HTTP error: {str(e)}")
            return jsonify({"error": f"Oops! Something went wrong on our end. Please try again later."}), 500
        except requests.exceptions.RequestException as e:
            app.logger.error(f"API request failed: {str(e)}")
            return jsonify({"error": f"Oops! Something went wrong on our end. Please try again later."}), 500

    except Exception as e:
        app.logger.error(f"Unexpected error in /api/consult: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": f"Oops! Something went wrong on our end. Please try again later."}), 500
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)