import base64
from openai import OpenAI
import streamlit as st
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv
from db_connection import DBCONNECTION
from streamlit_lottie import st_lottie
import json
import os
import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet

load_dotenv()

# Page config
st.set_page_config(
    page_title="Alexa AI",
    page_icon="🤖",
    layout="wide"
)

def load_lottieurl(path):
    with open(path, "r") as f:
        return json.load(f)
    
lottie = load_lottieurl("alexa_ai.json")

secrets_client = boto3.client(
    'secretsmanager',
    region_name='us-east-1',
    aws_access_key_id=os.getenv("aws_access_key_id"),
    aws_secret_access_key=os.getenv("aws_secret_access_key")
)
KEY_ID = os.getenv("ENCRYPTION_KEY")
fernet_client = Fernet(KEY_ID)

def get_secret(secret_name):
    """Retrieve secret from AWS Secrets Manager with caching."""
    try:
        response = secrets_client.get_secret_value(SecretId="alexa-ai-secrets")
        secret = json.loads(response['SecretString'])[secret_name]
        st.write(secret)
        return secret
    except ClientError as e:
        st.error(f"Error retrieving secret {secret_name}:\n\n{e}")
        st.stop()

def encrypt_data(data: str) -> str:
    response = fernet_client.encrypt(
        data.encode("utf-8")
    )
    return response.decode("utf-8")
    
@st.cache_resource(show_spinner=False)
def create_connection():
    try:
        db_connection = DBCONNECTION()
        return db_connection
    except Exception as e:
        st.error(f"Failed to connect to the database: {e}\n\n Please check your credentials or try again later.")
        st.stop()

with st.spinner('Connecting to database...'):
    db_connection = create_connection()
    KMS_KEY_ID = get_secret("KMS_KEY_ID")

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {
        font-family: 'Inter', system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
    }
            
    .gradient-text {
        background-image: linear-gradient(135deg, #667eea 0%, #603091ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 4em; /* Adjust font size as needed */
        font-weight: bold;
        text-align: center;
        margin: 0px;
        padding-top: 0px;
        }
  
    .stForm{
            border: 1px solid #6a63e3;
        }
    
    .stTextInput > div > div > input:focus {
        border-color: #6a63e3;
        box-shadow: 0 0 0 4px rgba(106, 99, 227, 0.25);
    }
    
    .button-row {
        display: flex;
        gap: 12px;
        margin-top: 8px;
    }
    
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        font-size: 16px;
        padding: 14px;
        width: 100%;
    }
            
    .primary-btn {
        background: #6a63e3 !important;
        color: white !important;
        border: 1px solid #6a63e3 !important;
    }
    
    .secondary-btn {
        background: white !important;
        color: #6a63e3 !important;
        border: 1px solid #dee2e6 !important;
    }
    
    .footer-box {
        border: 1px solid #6a63e3;
        border-radius: 12px;
        padding: 16px;
        margin: 32px auto;
        # max-width: 900px;
        font-size: 13px;
        color: #86909c;
        text-align: center;
        line-height: 1.5;
    }
            
    .msg-box {
        border-radius: 12px;
        padding: 16px;
        margin: 32px auto;
        max-width: 900px;
        font-size: 15px;
        color: white;
        text-align: center;
    }
    
    .success-msg {
        color: #28a745;
        font-weight: 500;
        font-size: 15px;
        text-align: center;
        margin-top: 20px;
    }
    
    .error-msg {
        color: #dc3545;
        font-weight: 500;
        font-size: 15px;
        text-align: center;
        margin-top: 20px;
    }
    
    .info-msg {
        color: #6c757d;
        font-weight: 500;
        font-size: 15px;
        text-align: center;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """, unsafe_allow_html=True)

# Initialize session state
if 'message' not in st.session_state:
    st.session_state.message = ""
if 'message_type' not in st.session_state:
    st.session_state.message_type = ""

def is_valid_https_url(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme == 'https'
    except:
        return False
    
user_id = st.query_params.get("user_id")

def test_connection(endpoint = None, api_key = None):
    """Test connection with user's credentials."""
    try:

        model_name = None
        
        # Check if model name is specified in the URL
        if '/model_name=' in endpoint:
            parts = endpoint.split('/model_name=')
            api_endpoint = parts[0].strip()
            model_name = parts[1].strip() if len(parts) > 1 else None
        
        client = OpenAI(
            api_key=api_key,
            base_url=api_endpoint,
            timeout=10.0
        )
        
        payload = {
            "messages": [
                {"role": "user", "content": "Hi"}
            ],
            "max_tokens": 100,
            "temperature": 0.1,
            "top_p": 1.0
        }
        
        # Add model name if specified
        if model_name and model_name != "":
            payload["model"] = model_name
        
        result = client.chat.completions.create(**payload)
        
        if hasattr(result, 'choices') and len(result.choices) > 0:
            return True, result.choices[0].message.content.strip()
        elif hasattr(result, 'response'):
            return True, result.response.strip()
        else:
            return False, "Sorry, I couldn't get a response from your LLM service. Pls check your credentials or try again later."
            
    except Exception as e:
        return False, "Sorry, I encountered an error while processing your request. Pls check your credentials or try again later."

def save_configuration(user_id = None, endpoint = None, api_key = None):
    try:
        user_id = "test" if user_id is None else user_id
        data_saved = db_connection.insert_data(user_id, endpoint, api_key)
        if data_saved is True:
            return True, "Configuration saved successfully!"
        else:
            return False, "Failed to save configuration."
    except Exception as e:
        return False, f"Save Error: {str(e)}"

# Main layout
col1, col2, col3, col4 = st.columns([0.1,1,1,0.3],vertical_alignment='center')

with col2:
    st_lottie(lottie, key="ai", speed=1, loop=True, width=500)

with col3:
    with st.form("my_form"):
        st.markdown("""
        <h1 align=center class='gradient-text'>ALEXA AI</h1>
        """, unsafe_allow_html=True)
        
        endpoint = st.text_input(
            "LLM endpoint :red[*] _(append model name at url end if needed)_",
            placeholder="https://api.openai.com/v1/chat/completions/model_name=gpt-5",
            key="endpoint",
            help="Enter the HTTPS endpoint for your LLM API.",
        )
    
        api_key = st.text_input(
            "LLM API key (optional)",
            placeholder="sk-xxxx (leave blank if not needed)",
            type="password",
            key="api_key"
        )

        # encrypted_url = fernet.encrypt(endpoint.encode()).decode()
        # encrypted_key = fernet.encrypt(api_key.encode()).decode()
        
        # Every form must have a submit button.
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            test_btn = st.form_submit_button("Test Connection", use_container_width=True, type='secondary')
        with col_btn2:
            save_btn = st.form_submit_button("Save & Link", use_container_width=True, type='primary')

        msg_placeholder = st.empty()

        # Handle button clicks
        if test_btn:
            if not endpoint.strip():
                st.session_state.message = "Please enter an endpoint URL."
                st.session_state.message_type = "error"
            elif not is_valid_https_url(endpoint.strip()):
                st.session_state.message = "Endpoint must be a valid HTTPS url."
                st.session_state.message_type = "error"
            else:
                st.session_state.message = "Testing connection..."
                st.session_state.message_type = "info"
                with st.spinner('Testing connection...'):
                    success, msg = test_connection(endpoint.strip(), api_key.strip())
                if success:
                    st.session_state.message = "✅ Connection successful!"
                    st.session_state.message_type = "success"
                else:
                    st.session_state.message = f"Test failed: {msg}"
                    st.session_state.message_type = "error"
        
        if save_btn:
            
            if not endpoint.strip():
                st.session_state.message = "Please enter a valid HTTPS endpoint."
                st.session_state.message_type = "error"
            elif not is_valid_https_url(endpoint.strip()):
                st.session_state.message = "Please enter a valid HTTPS endpoint."
                st.session_state.message_type = "error"
            else:
                encrypted_url = encrypt_data(endpoint)
                encrypted_key = encrypt_data(api_key)
                st.session_state.message = "Saving configuration..."
                st.session_state.message_type = "info"
                with st.spinner('Saving configuration...'):
                    success, msg = save_configuration(user_id, encrypted_url, encrypted_key)
                if success:
                    st.session_state.message = f"✅ Saved! You can now close this window."
                    st.session_state.message_type = "success"
                else:
                    st.session_state.message = f"Save failed: {msg}"
                    st.session_state.message_type = "error"
        
        # Display message
        if st.session_state.message:
            message_class = f"{st.session_state.message_type}-msg"
            msg_placeholder.markdown(f'<div class="msg-box">{st.session_state.message}</div>', unsafe_allow_html=True)
        else:
            msg_placeholder.text("\n")

st.markdown("<center><small>Made with ❤️ by <a href='https://linkedin.com/in/aaryanverma'>Aaryan Verma</a></small></center>", unsafe_allow_html=True)
st.markdown("""
<div class="footer-box">
    <strong>Disclaimer:</strong><br>
    Your endpoint & API key are sent to our backend over TLS and stored encrypted. 
    This page should be opened from the Alexa app's skill linking card, which provides a secure authorization code needed for saving credentials.
    <br>This app is not affiliated with Amazon in any way.
</div>
""", unsafe_allow_html=True)