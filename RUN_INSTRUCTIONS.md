# Moka AI - Quick Start Guide

## 🚀 **To Run Moka AI:**

### **Development Mode (with console output):**
```bash
cd d:\Ave\Documents\PROJECTS\moka-ai
python moka.py
```

### **Production Mode (minimized to system tray):**
```bash
cd d:\Ave\Documents\PROJECTS\moka-ai
python -m moka
```

## ✅ **What to Expect on Successful Startup:**

### **Console Output Should Show:**
1. Environment validation: `Environment validation passed`
2. Configuration loading: `MOKA AI starting up...`
3. Plugin initialization: `PluginManager initialized`
4. Service startup: Multiple `[ServiceName] started` messages
5. Health monitoring: `Health monitoring started`
6. Final confirmation: `MOKA AI initialized successfully`

### **System Indicators:**
- Development mode: Console remains active with logging output
- Production mode: System tray icon appears (Moka AI logo)
- Log files: Created in `logs/` directory (format: `moka_YYYYMMDD.log`)

## 🔍 **Quick Verification Tests (After Startup):**

### **Test 1: Context Retention (Verifies our Logger Fixes)**
Try this in the console/web interface:
```
Remember that test word is "sunflower"
What is the test word?
```
✅ **Expected Response:** Should recall "sunflower" or acknowledge your test word

### **Test 2: Simple Conversation Flow**
```
Hello Moka
How are you functioning today?
```
✅ **Expected Response:** Should maintain context and respond appropriately to both

### **Test 3: Web Interface (if applicable)**
- Access `http://localhost:5000` in your browser
- Or run installer UI: `cd installer_wizard && python main.py`
- Should load without errors

## 📋 **Important Notes:**

### **⚠️ Safety Feature Reminder:**
The Hermes Learning System has a built-in safety checkpoint:
- **Stage 5 (Approve)** requires **explicit human consent** before any behavior activates
- If you try to get Moka to "learn and activate" new behaviors automatically, it will stop at approval waiting for you
- This is **by design** - not a bug - to prevent autonomous behavior activation

### **📁 First Run Behavior:**
- On initial startup, AI models may download automatically (this takes time)
- Configuration files are created in appropriate directories
- Database tables are initialized as needed

### **🐛 Troubleshooting:**
If you see errors:
1. **Check logs:** `logs/moka_YYYYMMDD.log` for detailed error messages
2. **Dependencies:** Ensure `pip install -r requirements.txt` is complete
3. **Ports:** If web interface fails, check if required ports (typically 5000) are available
4. **Audio:** Voice service requires microphone/speaker access permissions

## 📊 **What We Fixed (Background Info):**

Prior to today's updates, Moka AI had logger initialization issues causing:
- **Context loss** between interactions (forgetting what you said)
- **Phase progression failures** in the Hermes learning system
- **Silent failures** that prevented proper state retention

**These issues have been resolved** by updating logger initialization in 26+ components to properly handle:
- Logger objects (with `.info` method)
- Callable functions
- None values

You should now observe:
- ✅ Better context retention between messages
- ✅ More reliable progression through system phases
- ✅ Consistent logging output showing system activity
- ✅ Improved state awareness and memory recall

## 🆘 **Need Help?**

If you encounter issues or unexpected behavior:
1. **Copy any error messages** from the console or log files
2. **Note exactly what you tried** when the issue occurred
3. **Describe what you expected vs. what happened**
4. **I'll help you diagnose and resolve it!**

The system is now ready to run with the context retention fixes in place. Try the quick verification tests above to confirm everything is working as expected.