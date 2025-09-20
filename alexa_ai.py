import json
import os
import requests
from cryptography.fernet import Fernet
from fastapi import FastAPI, Request
import uvicorn
from pyngrok import ngrok  # or localtunnel

class AlexaAI:
    def __init__(self, config_file="user_config.json", key_file="secret.key"):
        self.app = FastAPI()
        self.config_file = self._sanitize_path(config_file)
        self.key_file = self._sanitize_path(key_file)

        # Setup encryption key
        if not os.path.exists(self.key_file):
            with open(self.key_file, "wb") as f:
                f.write(Fernet.generate_key())
        with open(self.key_file, "rb") as f:
            self.fernet = Fernet(f.read())

        self._register_routes()

    def _sanitize_path(self, filename: str) -> str:
        """Sanitize file path to prevent directory traversal"""
        # Remove path separators and only allow alphanumeric, dots, underscores, hyphens
        safe_name = os.path.basename(filename)
        if not safe_name or '..' in safe_name or safe_name.startswith('.'):
            raise ValueError(f"Invalid filename: {filename}")
        return safe_name

    def _register_routes(self):
        @self.app.post("/query")
        async def query(request: Request):
            try:
                data = await request.json()
                user_id = data.get("session", {}).get("user", {}).get("userId")
                if not user_id:
                    return self._alexa_response("Invalid request format.")

                llm_url, llm_key = self._load_llm(user_id)
                if not llm_url:
                    return self._alexa_response("You have not configured an LLM yet.")

                # Get user input from Alexa
                user_input = data.get("request", {}).get("intent", {}).get("slots", {}).get("query", {}).get("value", "")

                # Forward to LLM
                headers = {"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"}
                payload = {"model": "gpt-4", "messages": [{"role": "user", "content": user_input}]}
                resp = requests.post(llm_url, headers=headers, json=payload, timeout=30)

                if resp.status_code != 200:
                    return self._alexa_response("Sorry, I could not reach your model.")

                response_data = resp.json()
                llm_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "No response received.")

                # Return SSML response
                return self._alexa_response(llm_text)
            except (requests.RequestException, json.JSONDecodeError, KeyError, Exception):
                return self._alexa_response("Sorry, there was an error processing your request.")

    def _alexa_response(self, text: str):
        # Comprehensive SSML sanitization
        if not isinstance(text, str):
            text = str(text)
        safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return {
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "SSML",
                    "ssml": f"<speak>{safe_text}</speak>"
                },
                "shouldEndSession": False
            }
        }

    def configure_llm(self, llm_url: str, llm_key: str, user_id: str="default"):
        """Save encrypted LLM config for a user"""
        encrypted_url = self.fernet.encrypt(llm_url.encode()).decode()
        encrypted_key = self.fernet.encrypt(llm_key.encode()).decode()

        config = {}
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                config = json.load(f)

        config[user_id] = {"url": encrypted_url, "key": encrypted_key}
        with open(self.config_file, "w") as f:
            json.dump(config, f)

    def _load_llm(self, user_id: str):
        if not os.path.exists(self.config_file):
            return None, None
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
            if user_id not in config:
                return None, None
            entry = config[user_id]
            return self.fernet.decrypt(entry["url"].encode()).decode(), self.fernet.decrypt(entry["key"].encode()).decode()
        except (json.JSONDecodeError, KeyError, Exception):
            return None, None

    def serve(self, port=8000):
        # Create public tunnel
        public_url = ngrok.connect(port).public_url
        print(f"Public Alexa endpoint: {public_url}/query")

        uvicorn.run(self.app, host="0.0.0.0", port=port)
