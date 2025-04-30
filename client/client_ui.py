from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import requests
import os
import pickle
from werkzeug.utils import secure_filename

# API base URL - Get from environment variable or use default
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:5001')

# Upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Create the Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'spam_detection_secret_key'  # Needed for flashing messages

# Store the current model_id
current_model_id = None

@app.route('/')
def index():
    """Home page with options to upload, predict, and retrieve models."""
    return render_template('index.html', model_id=current_model_id, api_url=API_BASE_URL)

@app.route('/upload', methods=['POST'])
def upload_model():
    """Upload a model to the API service."""
    global current_model_id
    
    if 'model_file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    model_file = request.files['model_file']
    
    if model_file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    try:
        # Save the uploaded file
        filename = secure_filename(model_file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        model_file.save(file_path)
        
        # Upload to API
        with open(file_path, 'rb') as f:
            response = requests.post(f"{API_BASE_URL}/model", files={'model': f})
        
        if response.status_code == 200:
            result = response.json()
            current_model_id = result['model_id']
            flash(f'Model uploaded successfully. Model ID: {current_model_id}', 'success')
        else:
            flash(f'Error uploading model: {response.text}', 'error')
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/predict', methods=['POST'])
def predict():
    """Make a prediction using the current model."""
    global current_model_id
    
    if not current_model_id:
        flash('No model uploaded yet', 'error')
        return redirect(url_for('index'))
    
    email_content = request.form.get('email_content', '')
    
    if not email_content:
        flash('No email content provided', 'error')
        return redirect(url_for('index'))
    
    try:
        data = {
            'model_id': current_model_id,
            'sample': email_content
        }
        
        response = requests.post(f"{API_BASE_URL}/predict", json=data)
        
        if response.status_code == 200:
            result = response.json()
            prediction = "SPAM" if result['prediction'] == 1 else "NOT SPAM"
            flash(f'Prediction: {prediction}', 'success')
        else:
            flash(f'Error making prediction: {response.text}', 'error')
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/retrieve', methods=['POST'])
def retrieve_model():
    """Retrieve the current model."""
    global current_model_id
    
    if not current_model_id:
        flash('No model uploaded yet', 'error')
        return redirect(url_for('index'))
    
    try:
        response = requests.get(f"{API_BASE_URL}/model/{current_model_id}")
        
        if response.status_code == 200:
            # Save the model
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"retrieved_model_{current_model_id}.pkl")
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            # Send the file to the user
            return send_file(output_path, as_attachment=True)
        else:
            flash(f'Error retrieving model: {response.text}', 'error')
            return redirect(url_for('index'))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/set_model_id', methods=['POST'])
def set_model_id():
    """Manually set a model ID."""
    global current_model_id
    
    model_id = request.form.get('model_id', '')
    
    if model_id:
        current_model_id = model_id
        flash(f'Model ID set to: {current_model_id}', 'success')
    else:
        flash('No model ID provided', 'error')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)