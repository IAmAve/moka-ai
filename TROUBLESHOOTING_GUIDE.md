# Moka AI Troubleshooting Guide

## 🔍 **Step-by-Step Diagnostic Process**

Follow these steps in order to identify why Moka AI isn't running.

### **Step 1: Verify Location**
First, confirm you're in the correct directory:
```bash
cd /d/Ave/Documents/PROJECTS/moka-ai
```
Then check: `dir` (Windows) or `ls -la` (Linux/Mac)

You should see files like: `moka.py`, `README.md`, `requirements.txt`, `CLAUDE.md`, and directories like `core/`, `memory/`, `learning/`, etc.

### **Step 2: Check Python Environment**
```bash
python --version
```
Should show Python 3.9 or higher (you have 3.11.0 which is good).

```bash
where python  # Windows
# or
which python  # Linux/Mac
```

### **Step 3: Test Basic Import Capability**
Try importing each component individually to isolate where the failure occurs:

**Test 1 - Config Module:**
```bash
python -c "import sys; sys.path.insert(0, '.'); from config import Config; print('✓ Config imports OK')"
```

**Test 2 - Logger Module:**
```bash
python -c "import sys; sys.path.insert(0, '.'); from logger import Logger; print('✓ Logger imports OK')"
```

**Test 3 - Event Bus:**
```bash
python -c "import sys; sys.path.insert(0, '.'); from core.event_bus import EventBus; print('✓ EventBus imports OK')"
```

**Test 4 - Memory System (Short Term):**
```bash
python -c "import sys; sys.path.insert(0, '.'); from memory.short_term_memory import ShortTermMemory; print('✓ ShortTermMemory imports OK')"
```

**Test 5 - Learning System:**
```bash
python -c "import sys; sys.path.insert(0, '.'); from learning.hermes_learning_system import HermesAdaptiveLearningSystem; print('✓ Hermes imports OK')"
```

**Test 6 - Voice Service:**
```bash
python -c "import sys; sys.path.insert(0, '.'); from voice_service import VoiceService; print('✓ VoiceService imports OK')"
```

**Test 7 - Main Moka Module:**
```bash
python -c "import sys; sys.path.insert(0, '.'); import moka; print('✓ Moka main module imports OK')"
```

### **Step 4: Check for Missing Dependencies**
If any import fails with `ModuleNotFoundError`, install the missing package:
```bash
pip install <missing-package-name>
```

Common problematic packages:
- `pyaudio` (often needs Visual Studio Build Tools on Windows)
- `flask-socketio`
- `textblob` (for sentiment analysis)
- `speechrecognition`
- `pyttsx3`

### **Step 5: Check Config File Existence**
The `Config` class looks for `config/config.json`. Verify this exists:
```bash
dir config\  # Windows
# or
ls -la config/  # Linux/Mac
```

If missing, create it:
```bash
mkdir config
echo '{
    "log_level": "INFO",
    "max_workers": 4,
    "voice_enabled": true,
    "memory_backend": "sqlite",
    "storage_path": "data/",
    "plugins_path": "plugins/",
    "models_path": "models/",
    "temp_path": "temp/"
}' > config\config.json
```

### **Step 6: Check Required Directories Exist**
Some components expect certain directories:
```bash
mkdir -p data logs models plugins temp
```

### **Step 7: Try Running with Error Output Visible**
Instead of just `python moka.py`, try to see all output:
```bash
python moka.py 2>&1
```
This redirects stderr to stdout so you can see error messages.

### **Step 8: Check for Port Conflicts**
If the system starts but web components fail, check if ports are available:
- Flask/SocketIO typically uses port 5000
- You can test with: `netstat -ano | findstr :5000` (Windows)
- Or: `lsof -i :5000` (Linux/Mac)

## 📋 **Most Common Issues and Solutions:**

### **Issue 1: Missing config/config.json**
**Symptom:** May fall back to defaults but fail later in initialization
**Fix:** Create the config directory and file as shown in Step 5 above

### **Issue 2: pyaudio Installation Problems**
**Symptom:** `ModuleNotFoundError: No module named 'pyaudio'` or import errors
**Fix:** 
- Option 1: `pip install pipwin` then `pipwin install pyaudio`
- Option 2: Download pre-built wheel from [www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio](http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio)
- Option 3: Install Visual Studio Build Tools and then `pip install pyaudio`

### **Issue 3: Missing Directory Permissions**
**Symptom:** Permission errors when trying to create log files or data files
**Fix:** Run command prompt as Administrator, or ensure you have write permissions to the project directory

### **Issue 4: First-Time Model Download Delay**
**Symptom:** Appears to hang or not respond for several minutes
**Fix:** Wait longer - on first run, AI models may be downloaded automatically. Check Task Manager for Python/python.exe network activity.

### **Issue 5: Import Errors Due to Missing Dependencies**
**Symptom:** `ModuleNotFoundError` for specific packages
**Fix:** Install missing packages with `pip install <package-name>`

## 🚨 **What to Do Next:**

1. **Run the import tests** (Step 3 above) and note which ones fail
2. **Fix any missing dependencies** 
3. **Ensure config file and directories exist**
4. **Try running again with visible error output**
5. **Report back:**
   - Which import tests failed (if any)
   - The exact error messages you see
   - Whether you see any output at all when trying to run
   - Any relevant details from your environment

Once you've gone through these steps, I'll be able to give you specific guidance based on the actual error messages you encounter.

**Remember:** The fixes we made to the logger initialization should resolve the context retention issues once the system is actually running. Let's get it running first!