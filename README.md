
# 🤖 Offline AI Assistant (Flask + GUI with Ollama LLMs)

This is a desktop + web-based AI assistant built with Python, using:

- **Tkinter GUI frontend**
- **Flask** backend server
- **Ollama** local LLM inference
- Runs offline on models like Mistral, LLaMA3.2, Dolphin3, Codestral

---

## 🌟 Features

- GUI chat window with model selection, structured JSON output toggle, and response history
- Background Flask server serving a web-based chat interface with styled HTML frontend
- Caching, logging, error handling, retry logic, and performance monitoring
- Saves chat history in `ai_assistant_history.json`
- Logs runtime events to `ai_assistant.log`

---

## 📸 Screenshots

### GUI Frontend:
![image](https://github.com/user-attachments/assets/19bf796a-7976-4214-8da9-1c51e990625a)


---

## 🚀 Setup & Run

1. **Clone** or download this repo  
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. **Download Ollama models** (if you haven't):

```bash
ollama pull mistral
ollama pull llama3.2
ollama pull dolphin3
ollama pull codestral
```

4. **Run the assistant**:

```bash
python assistant.py
```

5. The GUI will open and start the Flask server. A browser window will also launch for the chat interface.

---

## 📂 Files

- `assistant.py`: main application
- `ai_assistant.log`: runtime logs
- `ai_assistant_history.json`: stores chat history
- `images/`: UI screenshots
- `requirements.txt`: Python libraries
- `README.md`: documentation

---

## 🤝 Author

**Ravishankar Pathak**  
🔗 [GitHub](https://github.com/Ravishankar-pathak)  
📍 Gurgaon, Haryana
