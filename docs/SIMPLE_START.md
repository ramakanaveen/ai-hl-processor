# ⚡ Simple 3-Step Start Guide

**Use this if `start_ticker.py` is confusing!**

---

## 🎯 Start Services in 3 Terminals

### Terminal 1: API Service

```bash
cd /Users/naveenramaka/naveen/ai-hl-processor
python3 api_service.py
```

**Wait for:** `Application startup complete.`

**Keep this terminal open!**

---

### Terminal 2: Streamlit UI

```bash
cd /Users/naveenramaka/naveen/ai-hl-processor
streamlit run streamlit_ticker_app.py --server.port=8501
```

**It will open your browser automatically** to http://localhost:8501

**Keep this terminal open!**

---

### Terminal 3: Test It!

```bash
cd /Users/naveenramaka/naveen/ai-hl-processor
python3 test_ticker_now.py
```

**This sends 5 test headlines** and you'll see them appear in the UI!

---

## 📺 What You'll See

### In Terminal 3 (test script):
```
📰 Sending headline #1:
   Federal Reserve raises interest rates...
   ✅ Broadcast successful!
   📡 1 clients notified
   💱 1 currencies impacted
      #1 EURUSD: HIGH (0.84)
   👀 Check your browser - headline should appear NOW!
```

### In Your Browser:
```
┌─────────────────────────────────────────┐
│  📰 Federal Reserve raises interest...  │
│  ⏰ 17:45:23 | ⚡ 215ms                 │
│                                         │
│  💱 EURUSD: 🟢 HIGH (0.84)             │
└─────────────────────────────────────────┘
```

**Headlines appear automatically in the browser!**

---

## 🐛 Troubleshooting

### "UI shows 'API Not Available'"

**Fix:**
- Check Terminal 1 - is API running?
- Try: `curl http://localhost:8000/health`
- Restart: Press Ctrl+C in Terminal 1, then run `python3 api_service.py` again

### "WebSocket 404 error"

**Fix:**
```bash
python3 -m pip install websockets wsproto
```

Then restart Terminal 1 (API service)

### "Nothing appears when I run test_ticker_now.py"

**Check:**
1. Is Terminal 1 (API) still running? ✓
2. Is Terminal 2 (UI) still running? ✓
3. Is your browser open to http://localhost:8501? ✓
4. Do you see "🔴 LIVE" in the UI? ✓

If not, restart from Terminal 1.

---

## 🎮 After Testing

### Want Real News? (Optional)

**Terminal 3:**
```bash
python3 news_ticker_service.py
```

This will:
- Monitor Reuters, Yahoo Finance, Bloomberg (every 60 seconds)
- Automatically send headlines to the UI
- Show continuous updates

**But it takes 60 seconds** for first headlines!

That's why the test script is better for **immediate results**.

---

## 🔄 Quick Reference

| Terminal | Command | Purpose |
|----------|---------|---------|
| 1 | `python3 api_service.py` | Analysis engine + WebSocket |
| 2 | `streamlit run streamlit_ticker_app.py` | UI display |
| 3 | `python3 test_ticker_now.py` | Send test headlines (instant!) |
| 3 alt | `python3 news_ticker_service.py` | Real news (slower, every 60s) |

---

## 💡 Understanding the Flow

```
Terminal 3 (test_ticker_now.py)
       ↓
    POST /broadcast
       ↓
Terminal 1 (api_service.py)
       ↓ analyzes headline
       ↓ broadcasts to WebSocket
       ↓
Terminal 2 (streamlit UI)
       ↓ receives WebSocket message
       ↓ auto-refreshes every 2s
       ↓
YOUR BROWSER - Headline appears! ✨
```

---

## ✅ Success Checklist

- [ ] Terminal 1: API running (see "Application startup complete")
- [ ] Terminal 2: Streamlit running (browser opens automatically)
- [ ] Browser: Shows ticker UI with "🔴 LIVE" indicator
- [ ] Terminal 3: Run test script
- [ ] Browser: Headlines appear in ticker!

---

## 🚀 Once It's Working

**Experiment:**
1. Open http://localhost:8501 in **multiple browsers**
2. Run `python3 test_ticker_now.py`
3. Watch **all browsers** update simultaneously!

**This is the Bloomberg-style broadcast feature!** 📺

---

**Next:** See `BLOOMBERG_TICKER_GUIDE.md` for advanced features