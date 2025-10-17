# 🔑 Hugging Face Model License Setup

## ⚠️ IMPORTANT: License Acceptance Required

To use Mistral-7B and Zephyr-7B models via the Hugging Face Inference API, you **must accept their licenses** first.

---

## 📋 **Step-by-Step License Acceptance**

### **Step 1: Login to Hugging Face**
1. Go to https://huggingface.co/
2. Click "Sign In" (top right)
3. Login with your account (the one linked to your `HF_API_TOKEN`)

---

### **Step 2: Accept Mistral-7B License**
1. Go to: **https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3**
2. Scroll down to the model card
3. Look for the **"Agree and access repository"** button
4. Click it and accept the terms
5. You should see: ✅ "You have been granted access to this model"

---

### **Step 3: Accept Zephyr-7B License**
1. Go to: **https://huggingface.co/HuggingFaceH4/zephyr-7b-beta**
2. Scroll down to the model card
3. Look for the **"Agree and access repository"** button
4. Click it and accept the terms
5. You should see: ✅ "You have been granted access to this model"

---

### **Step 4: Verify Your Token**
Make sure your `HF_API_TOKEN` is from the **same account** you just used to accept licenses.

**To get your token:**
1. Go to https://huggingface.co/settings/tokens
2. Copy your token (starts with `hf_...`)
3. Add to Vercel environment variables:
   ```
   HF_API_TOKEN=hf_your_token_here
   ```

---

## 🧪 **Testing After License Acceptance**

### **Expected Behavior:**

**Before License Acceptance:**
```
DEBUG: Using HF token: Yes
DEBUG: Model not found (404). Response: Not Found
```

**After License Acceptance:**
```
DEBUG: Using HF token: Yes
DEBUG: Querying Mistral...
DEBUG: Model response length: 850 chars  ← SUCCESS!
```

---

## 🚀 **New Intelligent Pipeline Architecture**

After accepting licenses, your app will use this **5-stage pipeline**:

### **Stage 0: FLAN-T5 (Local)**
- Runs on your server (no API calls)
- Extracts structural elements from description
- Creates organized summary for next stages

### **Stage 1: Mistral-7B (API)**
- Deep problem analysis
- Uses FLAN-T5 structured summary
- Generates 3-4 detailed paragraphs

### **Stage 2: Zephyr-7B (API)**
- Solution articulation
- Emphasizes innovation and differentiation
- Generates 3-4 detailed paragraphs

### **Stage 3: Mistral-7B (API)**
- Market opportunity analysis
- TAM/SAM/SOM with projections
- Competitive landscape

### **Stage 4: Zephyr-7B (API)**
- Business model and traction
- Revenue strategy and GTM
- Growth projections

---

## 📊 **Performance Comparison**

| Metric | Old Pipeline | New Intelligent Pipeline |
|--------|--------------|--------------------------|
| **Stages** | 4 | 5 (with FLAN pre-processing) |
| **Models** | 2 (Mistral + Zephyr) | 3 (FLAN + Mistral + Zephyr) |
| **Structural Analysis** | None | FLAN-T5 local extraction |
| **Context Awareness** | Basic | Enhanced with structure |
| **Quality** | Good | Excellent |
| **Time** | 15-35 sec | 20-40 sec |

---

## 🔧 **Troubleshooting**

### **Issue: Still Getting 404 After Accepting License**

**Solutions:**
1. **Wait 5 minutes** - License propagation takes time
2. **Regenerate token** - Create a new token at https://huggingface.co/settings/tokens
3. **Update Vercel** - Add new token to environment variables
4. **Redeploy** - Trigger a new deployment on Vercel

---

### **Issue: FLAN-T5 Not Loading**

**Expected Behavior:**
```
DEBUG: Loading FLAN-T5 model for pre-processing...
DEBUG: FLAN-T5 model loaded successfully
```

**If you see:**
```
DEBUG: Failed to load FLAN-T5: No module named 'transformers'
DEBUG: Will skip pre-processing stage
```

**Solution:**
The pipeline will still work! It just skips Stage 0 and goes directly to Mistral/Zephyr.

To fix:
```bash
pip install transformers sentencepiece torch
```

---

### **Issue: Vercel Deployment Fails**

**If torch is too large for Vercel:**

Option 1: Use CPU-only torch
```
# In requirements.txt
torch==2.1.0+cpu
```

Option 2: Skip FLAN-T5 on Vercel
```python
# The code automatically skips if transformers not available
# Pipeline still works without Stage 0
```

---

## ✅ **Verification Checklist**

Before deploying, verify:

- [ ] Logged into Hugging Face
- [ ] Accepted Mistral-7B-Instruct-v0.3 license
- [ ] Accepted zephyr-7b-beta license
- [ ] `HF_API_TOKEN` in Vercel environment variables
- [ ] Token is from the same account that accepted licenses
- [ ] Redeployed Vercel after adding token
- [ ] Tested generation and checked logs

---

## 🎯 **Expected Debug Output**

### **Full Successful Run:**
```
DEBUG: Starting intelligent pitch generation for TestStartup
DEBUG: Loading FLAN-T5 model for pre-processing...
DEBUG: FLAN-T5 model loaded successfully
DEBUG: Running FLAN-T5 pre-processing...
DEBUG: FLAN-T5 structured summary: 250 chars
DEBUG: Searching for context: TestStartup industry trends 2025
DEBUG: Context found: 1200 chars
DEBUG: Stage 1 - Generating problem statement with Mistral...
DEBUG: Using HF token: Yes
DEBUG: Model response length: 850 chars
DEBUG: Stage 2 - Generating solution overview with Zephyr...
DEBUG: Using HF token: Yes
DEBUG: Model response length: 920 chars
DEBUG: Stage 3 - Generating market analysis with Mistral...
DEBUG: Using HF token: Yes
DEBUG: Model response length: 780 chars
DEBUG: Stage 4 - Generating business model with Zephyr...
DEBUG: Using HF token: Yes
DEBUG: Model response length: 810 chars
DEBUG: Assembling final pitch deck...
DEBUG: Intelligent pitch generation complete - 3500 chars
```

---

## 📚 **Additional Resources**

- **Mistral Model Card**: https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3
- **Zephyr Model Card**: https://huggingface.co/HuggingFaceH4/zephyr-7b-beta
- **FLAN-T5 Model Card**: https://huggingface.co/google/flan-t5-base
- **HF Token Management**: https://huggingface.co/settings/tokens
- **HF Inference API Docs**: https://huggingface.co/docs/api-inference/index

---

## 🎊 **Summary**

1. ✅ Accept licenses for Mistral-7B and Zephyr-7B
2. ✅ Add `HF_API_TOKEN` to Vercel
3. ✅ Deploy and test
4. ✅ Enjoy intelligent 5-stage pitch generation!

**Your pitch decks will now be powered by:**
- 🧠 FLAN-T5 for structural analysis
- 🚀 Mistral-7B for deep problem/market insights
- 💡 Zephyr-7B for solution/business articulation

---

*Last updated: 2025-10-17*
