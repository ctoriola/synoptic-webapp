# 🚀 Quick Start - Hugging Face Setup

## ⚡ 3-Minute Setup

### Step 1: Get Your Token (1 min)
1. Visit: https://huggingface.co/settings/tokens
2. Click "New token"
3. Name it: `synoptic-api`
4. Permission: **Read** (that's all you need!)
5. Click "Generate"
6. Copy the token (starts with `hf_...`)

### Step 2: Add to .env (30 seconds)
```bash
# Open your .env file and add:
HF_API_TOKEN=hf_your_actual_token_here
```

### Step 3: Test It! (1 min)
```bash
# Start your Flask app
python app.py

# Open browser: http://localhost:5000
# Go to Dashboard → Generate Pitch Deck
# Enter a GitHub repo URL
# Click Generate!
```

---

## 🎯 What to Expect

### First Generation
- **Time**: 15-20 seconds (model wakes up)
- **Debug output**: You'll see "Trying Mixtral..." messages
- **Result**: Complete pitch deck JSON

### Subsequent Generations
- **Time**: 3-8 seconds (model is warm)
- **Quality**: High-quality, specific content
- **Reliability**: Multiple fallbacks ensure success

---

## ✅ Success Indicators

You'll know it's working when you see:
```
DEBUG: Using Hugging Face for pitch generation
DEBUG: Trying Mixtral for pitch generation...
DEBUG: Mixtral success! Response length: 850
DEBUG: Successfully parsed JSON from Hugging Face
```

---

## 🔧 Deployment

### Vercel
```bash
# In Vercel dashboard:
Project Settings → Environment Variables → Add
Name: HF_API_TOKEN
Value: hf_your_token_here
```

### Heroku
```bash
heroku config:set HF_API_TOKEN=hf_your_token_here
```

### Railway
```bash
# In Railway dashboard:
Variables tab → Add Variable
HF_API_TOKEN = hf_your_token_here
```

### Render
```bash
# In Render dashboard:
Environment → Environment Variables → Add
HF_API_TOKEN = hf_your_token_here
```

---

## 📊 What Changed

| Feature | Before (Gemini) | After (Hugging Face) |
|---------|----------------|---------------------|
| **Cost** | Quota limits | 100% Free |
| **Models** | 1 model | 3 models + template |
| **Reliability** | Good | Excellent |
| **Setup** | Google API key | HF token |
| **Quality** | High | High |

---

## 🆘 Troubleshooting

### "Model is loading" errors
✅ **Normal!** First request wakes the model. Retry logic handles it automatically.

### Slow first request
✅ **Expected!** Models sleep when idle. They wake up in ~20 seconds.

### Empty responses
✅ **Handled!** Falls back to basic template automatically.

### Token not working
❌ Check:
- Token starts with `hf_`
- Token has **Read** permission
- Token is in `.env` file
- `.env` file is in project root
- Restart Flask app after adding token

---

## 📚 Full Documentation

- **Migration Guide**: `HUGGINGFACE_MIGRATION.md`
- **Complete Summary**: `MIGRATION_COMPLETE.md`
- **This File**: `QUICK_START.md`

---

## 🎉 You're All Set!

Your Synoptic app now runs on **100% free AI** with:
- ✅ No quota limits
- ✅ Multiple fallback models
- ✅ Excellent reliability
- ✅ Same great quality

**Ready to generate pitch decks? Add your token and go!** 🚀
