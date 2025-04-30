from flask import Flask, request, jsonify, send_file
import os
import json
import uuid
from datetime import datetime
import pickle
import io
from google.cloud import storage

app = Flask(__name__)

# Model storage dictionary to keep track of models in memory
model_registry = {}

# Configure Google Cloud Storage
# Make sure to set GOOGLE_APPLICATION_CREDENTIALS environment variable 
# or use service account key file
storage_client = storage.Client()
BUCKET_NAME = "email-spam-models"  # Replace with your actual bucket name

# Create bucket if it doesn't exist (with private access)
def ensure_bucket_exists():
    try:
        bucket = storage_client.get_bucket(BUCKET_NAME)
    except Exception:
        # Create a new bucket with private access (no public access)
        bucket = storage_client.create_bucket(BUCKET_NAME)
        # Ensure the bucket is private
        bucket.iam_configuration.public_access_prevention = "enforced"
        bucket.patch()
    return bucket

@app.route('/model', methods=['POST'])
def upload_model():
    """
    API Call 1: Upload a model
    Input: Model data
    Output: OK response with model identifier
    """
    if 'model' not in request.files:
        return jsonify({"error": "No model file provided"}), 400
    
    model_file = request.files['model']
    
    # Generate a unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_id = f"model_{timestamp}_{uuid.uuid4()}"
    filename = f"{model_id}.pkl"
    
    # Ensure the bucket exists
    bucket = ensure_bucket_exists()
    
    # Upload to GCP bucket
    blob = bucket.blob(filename)
    blob.upload_from_file(model_file)
    
    # Load model into memory
    model_file.seek(0)  # Reset file pointer to beginning
    model = pickle.load(model_file)
    
    # Store reference in memory
    model_registry[model_id] = {
        "model": model,
        "filename": filename,
        "uploaded_at": timestamp
    }
    
    return jsonify({
        "status": "OK",
        "message": "Model uploaded successfully",
        "model_id": model_id
    })

@app.route('/predict', methods=['POST'])
def predict():
    """
    API Call 2: Make prediction using a model
    Input: JSON with sample data and model_id
    Output: Classification result
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        if 'model_id' not in data:
            return jsonify({"error": "No model_id specified"}), 400
            
        if 'sample' not in data:
            return jsonify({"error": "No sample data provided"}), 400
        
        model_id = data['model_id']
        sample = data['sample']
        
        # Check if model is in memory
        if model_id not in model_registry:
            return jsonify({"error": f"Model {model_id} not found"}), 404
        
        # Use the model to make prediction
        model = model_registry[model_id]["model"]
        
        # For email spam detection model (assumes TF-IDF + classifier pipeline)
        result = model.predict([sample])[0]
        
        return jsonify({
            "model_id": model_id,
            "prediction": int(result)  # Convert numpy type to int for JSON serialization
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/model/<model_id>', methods=['GET'])
def get_model(model_id):
    """
    API Call 3: Get model
    Fetches model from GCP storage bucket and returns it
    """
    try:
        # Check if model_id exists
        if model_id not in model_registry:
            return jsonify({"error": f"Model {model_id} not found"}), 404
        
        # Get model metadata
        model_metadata = model_registry[model_id]
        filename = model_metadata["filename"]
        
        # Get from GCP bucket
        bucket = storage_client.get_bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        
        # Download to memory
        model_bytes = io.BytesIO()
        blob.download_to_file(model_bytes)
        model_bytes.seek(0)  # Reset to beginning of file
        
        # Return the model file
        return send_file(
            model_bytes,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))