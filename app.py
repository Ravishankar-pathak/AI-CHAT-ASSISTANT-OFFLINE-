import threading
import requests
from flask import Flask, request, jsonify
import ollama
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import time
import logging
import json
from datetime import datetime
import pytz
from functools import lru_cache
import webbrowser
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ai_assistant.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(_name_)

# Function to get current date and time in IST
def get_current_datetime():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

# Flask Server (AI Backend)
app = Flask(_name_)

# Model configuration for Ollama
MODEL_CONFIG = {
    "mistral": {
        "name": "mistral:latest",
        "temperature": 0.7,
        "num_predict": 1024
    },
    "llama3.2": {
        "name": "llama3.2:latest",
        "temperature": 0.7,
        "num_predict": 4096
    },
    "dolphin3": {
        "name": "dolphin3:latest",
        "temperature": 0.7,
        "num_predict": 2048
    },
    "codestral": {
        "name": "codestral:latest",
        "temperature": 0.7,
        "num_predict": 2048
    }
}

# Cache for model responses to improve performance
@lru_cache(maxsize=100)
def cached_generate(model_name, prompt, temperature, num_predict):
    try:
        output = ollama.generate(
            model=model_name,
            prompt=prompt,
            options={
                "temperature": temperature,
                "num_predict": num_predict,
                "stop": ["<|eot_id|>", "</s>", "###"]
            }
        )
        return output['response'].strip(), output.get('eval_count', 0)
    except Exception as e:
        logger.error(f"Error in cached_generate for {model_name}: {e}")
        raise

# Test Ollama connection with retry
def test_ollama_connection(model_name, max_retries=3):
    for attempt in range(max_retries):
        try:
            logger.info(f"Testing Ollama connection for {model_name} (Attempt {attempt+1}/{max_retries})")
            test_response = ollama.generate(
                model=model_name,
                prompt="Return 'Connection successful!'",
                options={"num_predict": 50}
            )
            response = test_response['response'].strip()
            logger.info(f"Test response: {response}")
            return True
        except Exception as e:
            logger.error(f"Ollama connection failed for {model_name} (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                logger.info("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                logger.error(f"Max retries reached for {model_name}")
                return False

# Fetch available models with error handling
def get_available_models():
    try:
        response = ollama.list()
        if 'models' not in response:
            logger.error("No 'models' key in Ollama response")
            return []
        models = response['models']
        available_models = []
        for model in models:
            model_name = model.get('name') or model.get('model') or model.get('id')
            if model_name and any(model_name == config['name'] for config in MODEL_CONFIG.values()):
                available_models.append(
                    next(key for key, config in MODEL_CONFIG.items() if config['name'] == model_name)
                )
        logger.info(f"Available models: {available_models}")
        return available_models
    except Exception as e:
        logger.error(f"Error fetching Ollama models: {e}")
        return []

# Root endpoint for chat interface
@app.route('/', methods=['GET'])
def index():
    return """
    <html>
        <head>
            <title>AI Chat Assistant</title>
            <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
            <style>
                body {{
                    font-family: 'Poppins', sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #1e3c72, #2a5298);
                    color: #fff;
                    min-height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                h1 {{
                    text-align: center;
                    color: #fff;
                    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                    margin-bottom: 20px;
                }}
                #chat-container {{
                    width: 90%;
                    max-width: 700px;
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 15px;
                    padding: 20px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }}
                #chat-history {{
                    height: 500px;
                    overflow-y: auto;
                    padding: 15px;
                    margin-bottom: 20px;
                    border-radius: 10px;
                    background: rgba(0, 0, 0, 0.2);
                }}
                .message {{
                    margin: 10px 0;
                    padding: 12px 18px;
                    border-radius: 20px;
                    max-width: 70%;
                    word-wrap: break-word;
                }}
                .user {{
                    background: #ff6f61;
                    color: #fff;
                    align-self: flex-end;
                    margin-left: auto;
                    border-bottom-right-radius: 5px;
                }}
                .bot {{
                    background: #4facfe;
                    color: #fff;
                    align-self: flex-start;
                    margin-right: auto;
                    border-bottom-left-radius: 5px;
                    white-space: pre-line;
                }}
                .code-block {{
                    background: rgba(0, 0, 0, 0.3);
                    border-radius: 8px;
                    padding: 12px;
                    margin: 10px 0;
                    overflow-x: auto;
                    font-family: 'Courier New', monospace;
                    white-space: pre;
                    text-align: left;
                }}
                .email-block {{
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    padding: 15px;
                    margin: 10px 0;
                    font-family: 'Poppins', sans-serif;
                    text-align: left;
                    border-left: 3px solid #4facfe;
                }}
                .email-subject {{
                    font-weight: 600;
                    margin-bottom: 10px;
                    color: #fff;
                }}
                .email-body {{
                    line-height: 1.6;
                }}
                .email-signature {{
                    margin-top: 15px;
                    font-style: italic;
                }}
                #chat-form {{
                    display: flex;
                    gap: 15px;
                    align-items: center;
                }}
                #prompt-input {{
                    flex: 1;
                    padding: 12px;
                    border: none;
                    border-radius: 25px;
                    font-size: 16px;
                    background: rgba(255, 255, 255, 0.9);
                    color: #333;
                    outline: none;
                    transition: box-shadow 0.3s ease;
                }}
                #prompt-input:focus {{
                    box-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
                }}
                #model-select {{
                    padding: 12px;
                    border: none;
                    border-radius: 25px;
                    font-size: 16px;
                    background: rgba(255, 255, 255, 0.9);
                    color: #333;
                    cursor: pointer;
                    transition: background 0.3s ease;
                }}
                #model-select:hover {{
                    background: rgba(255, 255, 255, 1);
                }}
                #send-button {{
                    padding: 12px 25px;
                    background: #ff6f61;
                    color: #fff;
                    border: none;
                    border-radius: 25px;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background 0.3s ease;
                }}
                #send-button:hover {{
                    background: #e65b50;
                }}
            </style>
        </head>
        <body>
            <div id="chat-container">
                <h1>AI Chat Assistant</h1>
                <div id="chat-history">
                    <div class="message bot">Hello! I'm your offline AI assistant. Select a model and start chatting!</div>
                </div>
                <form id="chat-form">
                    <select id="model-select" name="model">
                        {}
                    </select>
                    <input type="text" id="prompt-input" name="prompt" placeholder="Type your message..." required>
                    <button type="submit" id="send-button">Send</button>
                </form>
            </div>
            <script>
                const chatForm = document.getElementById('chat-form');
                const chatHistory = document.getElementById('chat-history');
                const promptInput = document.getElementById('prompt-input');

                chatForm.addEventListener('submit', async (e) => {{
                    e.preventDefault();
                    const model = document.getElementById('model-select').value;
                    const prompt = promptInput.value.trim();
                    if (!prompt) return;

                    // Add user message to chat history
                    const userMessage = document.createElement('div');
                    userMessage.className = 'message user';
                    userMessage.textContent = prompt;
                    chatHistory.appendChild(userMessage);
                    chatHistory.scrollTop = chatHistory.scrollHeight;

                    // Clear input
                    promptInput.value = '';

                    // Send request to server
                    try {{
                        const response = await fetch('/generate', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ model: model, prompt: prompt, structured: false }})
                        }});
                        const data = await response.json();

                        // Add bot response to chat history
                        const botMessage = document.createElement('div');
                        botMessage.className = 'message bot';
                        
                        const responseText = data.response.result || 'Error: No response';
                        
                        // Check if response is email and format accordingly
                        if (responseText.includes('Subject:')) {{
                            const emailParts = responseText.split('\\n\\n');
                            const subjectLine = emailParts[0].replace('Subject:', '').trim();
                            const emailBody = emailParts.slice(1).join('\\n\\n');
                            
                            const emailContainer = document.createElement('div');
                            emailContainer.className = 'email-block';
                            
                            const subject = document.createElement('div');
                            subject.className = 'email-subject';
                            subject.textContent = 'Subject: ' + subjectLine;
                            emailContainer.appendChild(subject);
                            
                            const body = document.createElement('div');
                            body.className = 'email-body';
                            body.textContent = emailBody;
                            emailContainer.appendChild(body);
                            
                            botMessage.appendChild(emailContainer);
                        }} 
                        // Check if response contains code blocks
                        else if (responseText.includes('')) {{
                            const parts = responseText.split('');
                            parts.forEach((part, index) => {{
                                if (index % 2 === 0) {{
                                    // Regular text
                                    if (part.trim() !== '') {{
                                        const textPart = document.createElement('div');
                                        textPart.textContent = part;
                                        botMessage.appendChild(textPart);
                                    }}
                                }} else {{
                                    // Code block
                                    const codeBlock = document.createElement('div');
                                    codeBlock.className = 'code-block';
                                    codeBlock.textContent = part;
                                    botMessage.appendChild(codeBlock);
                                }}
                            }});
                        }} 
                        // Regular text response
                        else {{
                            botMessage.textContent = responseText;
                        }}
                        
                        chatHistory.appendChild(botMessage);
                        chatHistory.scrollTop = chatHistory.scrollHeight;
                    }} catch (error) {{
                        const botMessage = document.createElement('div');
                        botMessage.className = 'message bot';
                        botMessage.textContent = 'Error: Failed to get response';
                        chatHistory.appendChild(botMessage);
                        chatHistory.scrollTop = chatHistory.scrollHeight;
                    }}
                }});
            </script>
        </body>
    </html>
    """.format(''.join(f'<option value="{m}">{m}</option>' for m in get_available_models()))

@app.route('/generate', methods=['POST'])
def generate_text():
    data = request.json
    model_name = data.get('model')
    prompt = data.get('prompt')
    structured_output = data.get('structured', False)
    
    if not model_name or model_name not in MODEL_CONFIG:
        return jsonify({'error': 'Invalid model name'}), 400
    
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    
    config = MODEL_CONFIG[model_name]
    
    if not test_ollama_connection(config["name"]):
        return jsonify({'error': f'Failed to connect to Ollama for model {model_name}'}), 500
    
    try:
        start_time = time.time()
        
        # Enhanced content detection
        content_type = "general"
        programming_keywords = ['code', 'program', 'write a', 'function', 'def ', 'class ', '#include', 
                              'algorithm', 'implement', 'in python', 'in c', 'in java', 'in c++', 
                              'in javascript', 'syntax', 'example', 'language', 'swap', 'reverse', 
                              'sort', 'algorithm', 'data structure', 'linked list', 'binary tree']
        email_keywords = ['email', 'mail', 'letter', 'draft', 'compose', 'write an email', 
                         'leave application', 'application for leave', 'formal letter']
        
        # Determine content type based on prompt
        if any(kw in prompt.lower() for kw in programming_keywords):
            content_type = "code"
        elif any(kw in prompt.lower() for kw in email_keywords):
            content_type = "email"
        
        # Add specific instructions based on content type
        if not structured_output:
            if content_type == "code":
                prompt = (
                    "You are an expert programmer. For coding questions, follow these rules STRICTLY:\n"
                    "1. Provide a brief explanation first if needed (1-2 sentences max)\n"
                    "2. Format ALL code in markdown code blocks with the correct language specification\n"
                    "3. Ensure code is complete, syntactically correct, and ready to copy-paste\n"
                    "4. Use proper indentation and syntax\n"
                    "5. Do NOT include any text after the code block\n"
                    "6. Do NOT include examples of how to run the code unless explicitly asked\n\n"
                    "User request: " + prompt
                )
            elif content_type == "email":
                prompt = (
                    "You are to write a professional email. Follow these rules:\n"
                    "1. Start with a clear subject line (prefix with 'Subject: ')\n"
                    "2. Use a proper salutation (e.g., 'Dear [Recipient's Name],')\n"
                    "3. In the body, clearly state the purpose of the email\n"
                    "4. Be concise and professional\n"
                    "5. End with a proper closing (e.g., 'Best regards,' followed by your name)\n"
                    "6. Format the entire email with clear line breaks\n"
                    "7. Do NOT include any markdown or code blocks\n\n"
                    "User request: " + prompt
                )
        
        if structured_output:
            structured_prompt = (
                "Generate a valid JSON response based on the user prompt. Ensure the output is a parseable JSON object with a 'result' key containing the response. "
                "If the prompt requests, structure the JSON accordingly. "
                "Rules:\n"
                "1. Return only a valid JSON string.\n"
                "2. If no specific structure is requested, use {'result': '<response>'}.\n"
                "3. Handle errors gracefully with an 'error' key if needed.\n"
                f"Prompt: {prompt}"
            )
            response, tokens_used = cached_generate(
                config["name"], structured_prompt, config["temperature"], config["num_predict"]
            )
            try:
                json_response = json.loads(response)
            except json.JSONDecodeError:
                json_response = {"error": "Invalid JSON generated", "raw_response": response}
        else:
            # Special formatting for llama3
            if "llama3" in model_name:
                prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
            
            # Generate the raw response
            raw_response, tokens_used = cached_generate(
                config["name"], prompt, config["temperature"], config["num_predict"]
            )
            
            # Post-processing based on content type
            if content_type == "code":
                # Enhanced code detection and formatting
                code_pattern = r'(#include\s*<.>|def\s+\w+|function\s+\w+|public\s+class|\bint\s+main\b|print\(|cout\s<<|\bimport\s+\w+|\bpackage\s+\w+|\bfunc\s+\w+|\binterface\s+\w+|\bstruct\s+\w+|\btypedef\s+\w+)'
                code_match = re.search(code_pattern, raw_response)
                
                if code_match:
                    # Determine language based on code patterns
                    lang = 'python' if 'def ' in raw_response or 'import ' in raw_response else \
                           'c' if '#include' in raw_response or 'int main' in raw_response else \
                           'cpp' if 'cout' in raw_response or 'using namespace' in raw_response else \
                           'java' if 'public class' in raw_response or 'import java.' in raw_response else \
                           'javascript' if 'function ' in raw_response or 'console.log' in raw_response else \
                           'html' if '<html>' in raw_response or '<div>' in raw_response else \
                           'sql' if 'SELECT' in raw_response or 'INSERT' in raw_response else \
                           'bash' if '#!/bin/' in raw_response or 'sudo ' in raw_response else \
                           'text'
                    
                    # Extract the main code block
                    code_block = raw_response
                    
                    # If there's explanation before code, separate it
                    if '' not in raw_response:
                        # Find the first occurrence of code-like pattern
                        code_start = code_match.start()
                        if code_start > 0:
                            explanation = raw_response[:code_start].strip()
                            code_block = raw_response[code_start:]
                        else:
                            explanation = "Here's the complete code:"
                        
                        # Format with markdown code block
                        response = f"{explanation}\n{lang}\n{code_block}\n```"
                    else:
                        response = raw_response
                else:
                    response = raw_response
            
            elif content_type == "email":
                # Ensure email has proper structure
                if not raw_response.startswith("Subject:"):
                    response = "Subject: [Your Subject Here]\n\n" + raw_response
                else:
                    response = raw_response
                
                # Ensure proper line breaks
                response = response.replace("\\n\\n", "\n\n")
            
            else:
                response = raw_response
                
            json_response = {"result": response}
        
        generation_time = time.time() - start_time
        logger.info(f"Generated {tokens_used} tokens in {generation_time:.2f}s using {model_name}")
        
        return jsonify({
            'response': json_response,
            'tokens': tokens_used,
            'time': round(generation_time, 2)
        })
    except Exception as e:
        logger.error(f"Error generating text with {model_name}: {e}")
        return jsonify({'error': str(e)}), 500

def run_flask():
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)

# Tkinter GUI (Frontend)
class AIAssistantApp:
    def _init_(self, root):
        self.root = root
        self.root.title("Offline AI Assistant (Ollama)")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        self.history = []
        self.history_file = "ai_assistant_history.json"
        
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TButton', font=('Arial', 10), padding=5)
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        self.style.configure('Header.TLabel', font=('Arial', 14, 'bold'))
        self.style.configure('Status.TLabel', background='#e0e0e0')
        
        self.create_widgets()
        self.load_history()
        self.start_flask_server()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        header = ttk.Label(
            main_frame, 
            text="Offline AI Assistant - Ollama Models", 
            style='Header.TLabel'
        )
        header.pack(pady=10)
        
        model_frame = ttk.Frame(main_frame)
        model_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(model_frame, text="Select AI Model:").pack(side=tk.LEFT, padx=5)
        
        available_models = get_available_models()
        if not available_models:
            logger.warning("No models detected via Ollama API. Using all configured models as fallback.")
            available_models = list(MODEL_CONFIG.keys())
        
        self.model_var = tk.StringVar(value=available_models[0] if available_models else "")
        model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            values=available_models,
            state="readonly" if available_models else "disabled",
            width=20
        )
        model_combo.pack(side=tk.LEFT, padx=10)
        
        self.structured_var = tk.BooleanVar(value=False)
        structured_check = ttk.Checkbutton(
            model_frame,
            text="Structured JSON Output",
            variable=self.structured_var
        )
        structured_check.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            model_frame,
            text="Model Info",
            command=self.show_model_info
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(
            model_frame,
            text="Show History",
            command=self.show_history
        ).pack(side=tk.RIGHT, padx=5)
        
        prompt_frame = ttk.Frame(main_frame)
        prompt_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(prompt_frame, text="Your Prompt:").pack(anchor=tk.W)
        self.prompt_entry = scrolledtext.ScrolledText(
            prompt_frame, 
            height=5,
            font=('Arial', 10),
            wrap=tk.WORD
        )
        self.prompt_entry.pack(fill=tk.X, pady=5)
        self.prompt_entry.focus_set()
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.generate_btn = ttk.Button(
            btn_frame,
            text="Generate Response",
            command=self.generate_response,
            state="normal" if available_models else "disabled"
        )
        self.generate_btn.pack(pady=10)
        
        response_frame = ttk.Frame(main_frame)
        response_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(response_frame, text="AI Response:").pack(anchor=tk.W)
        self.response_text = scrolledtext.ScrolledText(
            response_frame, 
            height=15,
            font=('Arial', 10),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.response_text.pack(fill=tk.BOTH, expand=True)
        
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            style='Status.TLabel'
        )
        status_bar.pack(fill=tk.X)
        
        if not available_models:
            self.status_var.set("No Ollama models found. Please ensure Ollama server is running and models are pulled.")
            messagebox.showwarning(
                "No Models Found",
                "No Ollama models detected. Run 'ollama pull mistral' or check Ollama server logs. Using fallback UI."
            )

    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                logger.info(f"Loaded history from {self.history_file}")
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            self.history = []

    def save_history(self, prompt, model, response, tokens, time_taken):
        entry = {
            "timestamp": get_current_datetime(),
            "model": model,
            "prompt": prompt,
            "response": response,
            "tokens": tokens,
            "time": time_taken
        }
        self.history.append(entry)
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved history to {self.history_file}")
        except Exception as e:
            logger.error(f"Error saving history: {e}")

    def show_history(self):
        history_window = tk.Toplevel(self.root)
        history_window.title("Prompt History")
        history_window.geometry("800x600")
        
        history_text = scrolledtext.ScrolledText(
            history_window,
            height=20,
            font=('Arial', 10),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        history_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        history_text.config(state=tk.NORMAL)
        for entry in self.history:
            history_text.insert(tk.END, f"Timestamp: {entry['timestamp']}\n")
            history_text.insert(tk.END, f"Model: {entry['model']}\n")
            history_text.insert(tk.END, f"Prompt: {entry['prompt']}\n")
            history_text.insert(tk.END, f"Response: {entry['response']}\n")
            history_text.insert(tk.END, f"Tokens: {entry['tokens']} | Time: {entry['time']}s\n")
            history_text.insert(tk.END, "-" * 50 + "\n")
        history_text.config(state=tk.DISABLED)

    def start_flask_server(self):
        self.status_var.set("Starting AI server...")
        threading.Thread(target=run_flask, daemon=True).start()
        # Open the browser automatically after the server starts
        time.sleep(2)  # Wait for the server to start
        webbrowser.open('http://127.0.0.1:5000')
        self.root.after(2000, lambda: self.status_var.set("Ready | Server running on http://0.0.0.0:5000"))
    
    def show_model_info(self):
        model_name = self.model_var.get()
        config = MODEL_CONFIG.get(model_name, {})
        
        info = f"Model: {model_name}\n"
        info += f"Temperature: {config.get('temperature', 'N/A')}\n"
        info += f"Max Tokens: {config.get('num_predict', 'N/A')}\n"
        try:
            model_info = ollama.show(config.get('name', model_name))
            info += f"Details: {model_info.get('details', 'N/A')}\n"
        except Exception:
            info += "Details: Not available\n"
        
        messagebox.showinfo("Model Information", info)
    
    def generate_response(self):
        prompt = self.prompt_entry.get("1.0", tk.END).strip()
        model = self.model_var.get()
        structured = self.structured_var.get()
        
        if not prompt:
            messagebox.showwarning("Input Error", "Please enter a prompt")
            return
        
        if not model:
            messagebox.showwarning("Model Error", "No model selected")
            return
        
        self.generate_btn.config(state=tk.DISABLED)
        self.status_var.set("Generating response...")
        self.response_text.config(state=tk.NORMAL)
        self.response_text.delete(1.0, tk.END)
        self.response_text.insert(tk.END, "Thinking...")
        self.response_text.config(state=tk.DISABLED)
        self.root.update()
        
        threading.Thread(target=self._call_api, args=(model, prompt, structured)).start()
    
    def _call_api(self, model, prompt, structured):
        try:
            response = requests.post(
                'http://127.0.0.1:5000/generate',
                json={'model': model, 'prompt': prompt, 'structured': structured},
                timeout=600
            )
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result:
                raise Exception(result['error'])
            
            response_text = json.dumps(result['response'], indent=2) if structured else result['response']['result']
            self.response_text.config(state=tk.NORMAL)
            self.response_text.delete(1.0, tk.END)
            self.response_text.insert(tk.END, response_text)
            self.response_text.config(state=tk.DISABLED)
            
            tokens = result.get('tokens', 0)
            time_taken = result.get('time', 0)
            self.status_var.set(f"Generated {tokens} tokens in {time_taken}s using {model}")
            
            self.save_history(prompt, model, response_text, tokens, time_taken)
        
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("API Error", str(e))
        
        finally:
            self.generate_btn.config(state=tk.NORMAL)

# Main Execution
if _name_ == "_main_":
    try:
        import ollama
    except ImportError:
        logger.info("Installing required packages...")
        os.system("pip install ollama requests flask")
        import ollama
    
    available_models = get_available_models()
    if available_models:
        logger.info("Available Ollama models: " + ", ".join(available_models))
    else:
        logger.error("No Ollama models detected. Please ensure models are pulled.")
    
    root = tk.Tk()
    app = AIAssistantApp(root)
    root.mainloop()
