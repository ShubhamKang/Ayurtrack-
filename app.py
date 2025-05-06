import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
from datetime import datetime
import sys # Import sys to allow exiting if files aren't found

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# --- Configuration ---
# Assumes CSV files are in the SAME directory as this script (app.py)
# If they are in a subdirectory (e.g., 'data'), change path like 'data/data.csv'
# If you MUST use absolute paths, verify them carefully and replace below.
DATA_CSV_PATH = 'data.csv'
REMEDY_CSV_PATH = 'remedies.csv'
DATE_FORMAT = '%d-%m-%Y' # Adjust if your date format is different (e.g., '%d/%m/%Y')

# --- Load Data ---
try:
    # Load outbreak data CSV
    data = pd.read_csv(DATA_CSV_PATH)
    # Convert date columns to datetime using the specified format
    data["Date of Start of Outbreak"] = pd.to_datetime(data["Date of Start of Outbreak"], format=DATE_FORMAT, errors='coerce')
    data["Date of Reporting"] = pd.to_datetime(data["Date of Reporting"], format=DATE_FORMAT, errors='coerce')
except FileNotFoundError:
    print(f"FATAL ERROR: Outbreak data file not found at '{DATA_CSV_PATH}'")
    print("Please ensure the file exists and the path is correct.")
    sys.exit(1) # Exit if essential data is missing
except Exception as e:
    print(f"FATAL ERROR: Could not process outbreak data file '{DATA_CSV_PATH}'. Error: {e}")
    sys.exit(1)

try:
    # Load remedy data
    remedy_data = pd.read_csv(REMEDY_CSV_PATH)
except FileNotFoundError:
    print(f"FATAL ERROR: Remedy data file not found at '{REMEDY_CSV_PATH}'")
    print("Please ensure the file exists and the path is correct.")
    sys.exit(1) # Exit if essential data is missing
except Exception as e:
    print(f"FATAL ERROR: Could not process remedy data file '{REMEDY_CSV_PATH}'. Error: {e}")
    sys.exit(1)


# --- Flask Routes ---

@app.route("/")
def home():
    return "✅ Backend is running! Use POST /check-outbreak, GET /test-check?state=&district=, or POST/GET /get-remedy"

@app.route("/check-outbreak", methods=["POST"])
def check_outbreak():
    content = request.get_json()
    if not content:
        return "Error: No JSON data received.", 400
    state = content.get("state", "").strip().lower()
    district = content.get("district", "").strip().lower()

    if not state or not district:
        return "Error: Both 'state' and 'district' are required.", 400

    return get_outbreak_response(state, district)

@app.route("/test-check", methods=["GET"])
def test_check():
    state = request.args.get("state", "").strip().lower()
    district = request.args.get("district", "").strip().lower()

    if not state or not district:
        return "Error: Both 'state' and 'district' query parameters are required.", 400

    return get_outbreak_response(state, district)

def get_outbreak_response(state, district):
    """Helper function to check for outbreaks and generate response."""
    try:
        filtered = data[
            (data["Name of State/UT"].str.lower() == state) &
            (data["Name of District"].str.lower() == district)
        ]

        if not filtered.empty:
            # Drop NaN, strip whitespace, title case, get unique, sort
            unique_diseases = sorted(
                filtered["Disease/Illness"].dropna().str.strip().str.title().unique()
            )
            outbreak_str = ", ".join(unique_diseases) if unique_diseases else "unspecified diseases"

            message = (
                f"⚠️ Alert! Your area {district.title()} in {state.title()} has reported disease outbreak(s): "
                f"{outbreak_str}."
            )
        else:
            message = (
                f"✅ Good news! Your area {district.title()}, {state.title()} currently shows no reported disease outbreaks in our records. "
                f"However, if you're experiencing symptoms, you can check our remedies section."
            )
        return message # plain text response
    except Exception as e:
        print(f"Error during outbreak check for {state}, {district}: {e}")
        # Provide a generic error response to the user
        return f"An error occurred while checking for outbreaks in {district.title()}, {state.title()}. Please try again later.", 500


@app.route("/get-remedy", methods=["POST", "GET"])
def get_remedy():
    disease_input = ""
    if request.method == "POST":
        content = request.get_json()
        if not content:
            return jsonify({"error": "No JSON data received."}), 400
        disease_input = content.get("disease", "").strip().lower()
    else: # GET request
        disease_input = request.args.get("disease", "").strip().lower()

    if not disease_input:
        return jsonify({"error": "Disease parameter is required."}), 400

    try:
        # Ensure 'Disease' column exists and handle potential NaN values before comparison
        if 'Disease' not in remedy_data.columns:
             return jsonify({
                "disease": disease_input.title(),
                "remedies": ["⚠️ Error: Remedy data format issue (Missing 'Disease' column)."]
            }), 500

        remedies = remedy_data[remedy_data["Disease"].str.lower().fillna('') == disease_input]

        if not remedies.empty:
            # Get unique, non-null remedies
            remedy_list = remedies["Remedy"].dropna().unique().tolist()
            if not remedy_list: # Check if list is empty after dropna/unique
                 return jsonify({
                    "disease": disease_input.title(),
                    "remedies": ["⚠️ No specific remedies listed for this disease, although it was found."]
                 })
            else:
                return jsonify({
                    "disease": disease_input.title(),
                    "remedies": remedy_list
                })
        else:
            return jsonify({
                "disease": disease_input.title(),
                "remedies": ["✅ No Ayurvedic remedy found for this specific disease in our database."]
            })
    except Exception as e:
        print(f"Error during remedy lookup for {disease_input}: {e}")
         # Provide a generic error response to the user
        return jsonify({
            "disease": disease_input.title(),
            "remedies": ["⚠️ An error occurred while searching for remedies. Please try again later."]
        }), 500

if __name__ == "__main__":
    # Set host='0.0.0.0' to make it accessible on your network (optional)
    app.run(debug=True) # debug=True is helpful for development, turn off for production