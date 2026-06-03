# Moka AI - Quick Start Checklist

## ✅ **Before You Start:**

### **1. Verify You're in the Right Place:**
```bash
cd /d/Ave/Documents/PROJECTS/moka-ai
```
Then run: `dir` and confirm you see `moka.py`, `README.md`, and folders like `core/`, `memory/`, `learning/`

### **2. Check Python Version:**
```bash
python --version
```
Should be 3.9+ (you have 3.11.0 - perfect!)

### **3. Create Missing Config (Common Issue):**
```bash
# If config folder doesn't exist:
mkdir config

# Create default config.json:
echo {
  "log_level": "INFO",
  "max_workers": 4,
  "voice_enabled": true,
  "memory_backend": "sqlite",
  "storage_path": "data/",
  "plugins_path": "plugins/",
  "models_path": "models/",
  "temp_path": "temp/"
} > config/config.json
```

### **4. Create Required Directories:**
```bash
mkdir -p data logs models plugins temp
```

### **5. Install Key Dependencies (if first time):**
```bash
pip install pyaudio flask-socketio textblob
```

## ▶️ **To Start:**

### **Development Mode** (see logs in real-time):
```bash
python moka.py
```

### **Production Mode** (to system tray):
```bash
python -m moka
```

## 🔍 **What Success Looks Like:**

### **Console Should Show:**
- `Environment validation passed`
- `MOKA AI starting up...`
- Multiple lines like `[ServiceName] started` for each service
- `Health monitoring started`
- Final line: `MOKA AI initialized successfully`

### **If Production Mode:**
- Moka AI icon appears in Windows system tray (bottom-right)
- Right-click the icon for options

## 🧪 **Quick Verification Tests (After Startup):**

### **Test 1: Simple Memory**
```
Remember that my favorite color is green
What is my favorite color?
```
Should acknowledge "green"

### **Test 2: Basic Conversation:**
```
Hello
How can you help me today?
```
Should maintain context

## 📁 **If You Need to Check Logs:**
- Location: `logs/` folder
- File: `moka_YYYYMMDD.log` (today's date)
- Open with Notepad to see detailed startup info

## 🚨 **Common Issues & Quick Fixes:**

### **"Command not found" or Python errors:**
- Ensure you ran `cd /d/Ave/Documents/PROJECTS/moka-ai` first
- Verify Python is installed and in PATH

### **"Missing module" errors:**
- Run: `pip install pyaudio flask-socketio textblob` (most common missing ones)
- For persistent issues: `pip install -r requirements.txt`

### **Permission errors:**
- Close any antivirus that might be blocking
- Try running command prompt as Administrator

### **Appears to hang/freeze:**
- On first run, may be downloading AI models (wait 5-10 minutes)
- Check Task Manager for Python network/CPU activity
- Make sure you have internet connection for model downloads

### **No system tray icon (production mode):**
- Try development mode first: `python moka.py`
- Check if another Moka instance is already running

## 📞 **Still Not Working? Tell Me Exactly:**

1. **What command did you run?**
2. **What exact output/error did you see?** (copy-paste if possible)
3. **Did you see any output at all, or just nothing?**
4. **What's in your logs folder?** (if it exists)
5. **Anything unusual about your setup?** (corporate PC, restricted permissions, etc.)

With that information, I can give you precisenext steps!

**Remember:** Our logger fixes are already in place - once it runs, you should see improved context retention!