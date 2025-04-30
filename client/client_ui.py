from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import requests
import os
import pickle
from werkzeug.utils import secure_filename

# API base URL - Get from environment variable or use default
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8081')

# Upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Create the Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'twitter_sentiment_secret_key'  # Needed for flashing messages

# Store the current model_id
current_model_id = None

@app.route('/')
def index():
    """Home page with options to upload, analyze, and retrieve models."""
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
            print(f"Model uploaded with ID: {current_model_id}")
        else:
            flash(f'Error uploading model: {response.text}', 'error')
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze a tweet using the current model."""
    global current_model_id
    
    tweet_text = request.form.get('tweet_text', '')
    
    if not tweet_text:
        flash('No tweet text provided', 'error')
        return redirect(url_for('index'))
    
    try:
        data = {
            'tweet': tweet_text
        }
        
        # Include model_id if available
        if current_model_id:
            data['model_id'] = current_model_id
        
        response = requests.post(f"{API_BASE_URL}/analyze", json=data)
        
        if response.status_code == 200:
            result = response.json()
            
            # Display the result
            sentiment = result.get('sentiment', 'unknown')
            model_used = "Custom model" if result.get('using_model', False) else "TextBlob"
            
            flash(f'Sentiment: {sentiment.upper()} (using {model_used})', 'success')
            
            # If there are additional metrics, display them
            if 'polarity' in result:
                flash(f'Polarity: {result["polarity"]:.2f}', 'info')
            if 'subjectivity' in result:
                flash(f'Subjectivity: {result["subjectivity"]:.2f}', 'info')
        else:
            flash(f'Error analyzing tweet: {response.text}', 'error')
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/analyze/batch', methods=['POST'])
def analyze_batch():
    """Analyze multiple tweets at once."""
    global current_model_id
    
    tweets_text = request.form.get('tweets_text', '')
    
    if not tweets_text:
        flash('No tweets provided', 'error')
        return redirect(url_for('index'))
    
    # Split text into individual tweets
    tweets = [tweet.strip() for tweet in tweets_text.split('\n') if tweet.strip()]
    
    try:
        data = {
            'tweets': tweets
        }
        
        # Include model_id if available
        if current_model_id:
            data['model_id'] = current_model_id
        
        response = requests.post(f"{API_BASE_URL}/analyze/batch", json=data)
        
        if response.status_code == 200:
            result = response.json()
            
            # Flash a summary
            count = result.get('count', 0)
            model_used = "Custom model" if result.get('using_model', False) else "TextBlob"
            flash(f'Analyzed {count} tweets using {model_used}', 'success')
            
            # Return to a results page instead of index
            return render_template('results.html', 
                                  results=result.get('results', []), 
                                  model_id=current_model_id)
        else:
            flash(f'Error analyzing tweets: {response.text}', 'error')
    
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
        print(f"Model ID manually set to: {current_model_id}")
    else:
        flash('No model ID provided', 'error')
    
    return redirect(url_for('index'))

@app.route('/list_models', methods=['GET'])
def list_models():
    """List all available models from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/models")
        
        if response.status_code == 200:
            result = response.json()
            models = result.get('models', [])
            return render_template('models.html', models=models)
        else:
            flash(f'Error retrieving models: {response.text}', 'error')
            return redirect(url_for('index'))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/clear_model', methods=['POST'])
def clear_model():
    """Clear the current model selection."""
    global current_model_id
    
    current_model_id = None
    flash('Model selection cleared. Using TextBlob for analysis.', 'info')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)