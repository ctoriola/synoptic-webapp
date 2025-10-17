# 🚀 Deep Pitch Pipeline - Investor-Grade Pitch Decks

## Overview
The Deep Pitch Pipeline is a multi-step AI system that generates detailed, investor-grade pitch decks using contextual search and dual Hugging Face models (Mistral & Zephyr).

---

## ✨ What's New

### Multi-Step Generation Process
Instead of generating everything at once, the pipeline creates pitch decks in **4 strategic steps**:

1. **Problem Statement** - Identifies market pain points with context
2. **Solution Overview** - Explains the innovation and differentiation
3. **Market Opportunity** - Analyzes TAM, trends, and competition
4. **Business Model** - Details revenue, GTM strategy, and traction

### Contextual Search Integration
- Uses **DuckDuckGo search** to gather real market intelligence
- Searches for industry trends, market data, and competitive landscape
- Enriches AI generation with current, relevant information

### Dual-Model Architecture
- **Mistral-7B** - Problem analysis and market research
- **Zephyr-7b** - Solution articulation and business strategy
- Each model specializes in different aspects of the pitch

---

## 🎯 Key Features

### Investor-Grade Content
- **No vague suggestions** - Only finished, confident paragraphs
- **Data-backed assertions** - Includes specific statistics and projections
- **Professional tone** - Written for actual investor presentations
- **Comprehensive sections** - 3-4 detailed paragraphs per section

### Smart Context Gathering
- Automatically searches for relevant industry information
- Incorporates market trends and competitive insights
- Uses real-world data to support claims
- Adapts to different industries and sectors

### Robust Fallbacks
- If search fails, continues with AI knowledge
- If one model fails, uses the other
- Always produces complete output
- Never returns empty or generic content

---

## 📡 API Endpoint

### `/api/generate-deep-pitch`

**Method:** `POST`

**Authentication:** Required (login_required)

**Request Body:**
```json
{
  "name": "PitchPerfectAI",
  "description": "AI-powered pitch deck generator that helps founders create investor-grade presentations"
}
```

**Response:**
```json
{
  "success": true,
  "pitch": "# PitchPerfectAI Pitch Deck\n\n## Problem\n...\n\n## Solution\n...",
  "project_id": "abc123",
  "tokens_remaining": 95
}
```

**Error Response:**
```json
{
  "error": "Both startup name and description are required"
}
```

---

## 💻 Usage Examples

### Using cURL
```bash
curl -X POST http://localhost:5000/api/generate-deep-pitch \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_cookie" \
  -d '{
    "name": "TechStartup",
    "description": "Revolutionary SaaS platform for small businesses"
  }'
```

### Using JavaScript (Fetch)
```javascript
fetch('/api/generate-deep-pitch', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    name: 'TechStartup',
    description: 'Revolutionary SaaS platform for small businesses'
  })
})
.then(response => response.json())
.then(data => {
  console.log('Pitch generated:', data.pitch);
  console.log('Project ID:', data.project_id);
})
.catch(error => console.error('Error:', error));
```

### Using Python (requests)
```python
import requests

response = requests.post(
    'http://localhost:5000/api/generate-deep-pitch',
    json={
        'name': 'TechStartup',
        'description': 'Revolutionary SaaS platform for small businesses'
    },
    cookies={'session': 'your_session_cookie'}
)

data = response.json()
print(f"Pitch: {data['pitch']}")
print(f"Project ID: {data['project_id']}")
```

---

## 🔧 Technical Details

### Pipeline Architecture

```
Input (Name + Description)
    ↓
Context Search (DuckDuckGo)
    ↓
Step 1: Problem (Mistral) ← Context
    ↓
Step 2: Solution (Zephyr) ← Problem
    ↓
Step 3: Market (Mistral) ← Solution + Context
    ↓
Step 4: Business (Zephyr) ← Problem + Solution + Market
    ↓
Final Assembly (Markdown)
    ↓
Output (Complete Pitch Deck)
```

### Model Parameters
```python
{
    'max_new_tokens': 1000,
    'temperature': 0.7,
    'top_p': 0.95,
    'return_full_text': False
}
```

### Prompt Engineering
Each step uses the **DEPTH_PROMPT** system message:
```
You are PitchPerfectAI, an expert investor and pitch consultant. 
You create detailed, data-backed, assertive pitch deck content. 
You never give vague suggestions; instead, you write finished, 
confident paragraphs that can go directly into an investor pitch deck.
```

---

## 📊 Performance

### Response Times
- **Context Search**: 1-3 seconds
- **Problem Generation**: 3-8 seconds
- **Solution Generation**: 3-8 seconds
- **Market Analysis**: 3-8 seconds
- **Business Model**: 3-8 seconds
- **Total**: ~15-35 seconds

### Quality Metrics
- **Specificity**: High - Includes concrete examples and data
- **Completeness**: 100% - All sections always generated
- **Professionalism**: Investor-grade language and structure
- **Relevance**: Context-aware with real market intelligence

---

## 🎨 Output Format

### Markdown Structure
```markdown
# {Startup Name} Pitch Deck

## Problem
{3-4 detailed paragraphs about market pain points, 
inefficiencies, and urgency. Includes specific statistics 
and market insights.}

## Solution
{3-4 detailed paragraphs explaining how the solution works, 
what makes it unique, and why it's superior to alternatives. 
Specific and confident.}

## Market Opportunity
{3-4 detailed paragraphs with TAM/SAM/SOM numbers, market 
trends, growth projections, competitive landscape, and 
target customer segments.}

## Business Model & Traction
{3-4 detailed paragraphs covering revenue model, pricing 
strategy, go-to-market approach, key partnerships, traction 
metrics, and growth projections.}

---

*Generated by PitchPerfectAI - Investor-Grade Pitch Deck Generator*
```

---

## 🔄 Comparison with Standard Pipeline

| Feature | Standard Pipeline | Deep Pipeline |
|---------|------------------|---------------|
| **Steps** | 1 (single generation) | 4 (multi-step) |
| **Context** | README only | README + Web search |
| **Models** | 1 (Mixtral or Mistral) | 2 (Mistral + Zephyr) |
| **Detail Level** | Good | Excellent |
| **Specificity** | Moderate | High |
| **Time** | 5-10 seconds | 15-35 seconds |
| **Use Case** | GitHub repos | Startup ideas |

---

## 🚀 Getting Started

### 1. Ensure Dependencies
```bash
pip install duckduckgo-search requests python-dotenv
```

### 2. Set HF Token
```bash
# In .env file
HF_API_TOKEN=hf_your_token_here
```

### 3. Test the Endpoint
```bash
# Start Flask server
python app.py

# In another terminal
curl -X POST http://localhost:5000/api/generate-deep-pitch \
  -H "Content-Type: application/json" \
  -H "Cookie: session=$(cat .session_cookie)" \
  -d '{"name": "TestStartup", "description": "AI-powered solution"}'
```

---

## 🎯 Best Practices

### Input Guidelines
- **Name**: Keep it concise (2-4 words)
- **Description**: Be specific about what the startup does (1-2 sentences)
- **Clarity**: Avoid jargon in the description
- **Focus**: Mention the core value proposition

### Example Good Inputs
```json
{
  "name": "HealthTrack AI",
  "description": "AI-powered health monitoring platform that helps doctors detect diseases early through continuous patient data analysis"
}
```

```json
{
  "name": "EduLearn",
  "description": "Personalized learning platform that adapts to each student's pace and learning style using machine learning"
}
```

### Example Poor Inputs
```json
{
  "name": "My Awesome Startup",
  "description": "We do stuff"
}
```

---

## 🔧 Customization

### Adjust Token Limits
In `huggingface_client.py`, modify `max_new_tokens`:
```python
payload = {
    'inputs': prompt,
    'parameters': {
        'max_new_tokens': 600,  # Reduce for faster response
        # or
        'max_new_tokens': 1500,  # Increase for more detail
    }
}
```

### Disable Context Search
To skip web search (faster but less contextual):
```python
# In deep_pitch_generation function
context_snippet = ""  # Comment out get_context() call
```

### Change Model Order
To use Zephyr for problem and Mistral for solution:
```python
# Step 1: Problem
problem = query_model(problem_prompt, ZEPHYR_URL)  # Changed

# Step 2: Solution
solution = query_model(solution_prompt, MISTRAL_URL)  # Changed
```

---

## 📈 Monitoring & Debugging

### Debug Output
The pipeline logs each step:
```
DEBUG: Starting deep pitch generation for TechStartup
DEBUG: Searching for context: TechStartup industry trends 2025
DEBUG: Context found: 1250 chars
DEBUG: Generating problem statement...
DEBUG: Querying Mistral (attempt 1/3)
DEBUG: Model response length: 850 chars
DEBUG: Generating solution overview...
DEBUG: Querying Zephyr (attempt 1/3)
DEBUG: Model response length: 920 chars
...
DEBUG: Deep pitch generation complete - 3500 chars
```

### Common Issues

**Issue**: Context search fails
```
DEBUG: Context search failed: [error]
```
**Solution**: Pipeline continues with AI knowledge only. No action needed.

**Issue**: Model timeout
```
DEBUG: Query error on attempt 1: timeout
```
**Solution**: Automatic retry with exponential backoff. Wait for completion.

**Issue**: All models fail
```
DEBUG: All Hugging Face models failed
```
**Solution**: Returns fallback content. Check HF_API_TOKEN and network.

---

## 🎓 Advanced Usage

### Batch Generation
```python
startups = [
    {"name": "Startup1", "description": "Description 1"},
    {"name": "Startup2", "description": "Description 2"},
]

for startup in startups:
    response = requests.post(
        '/api/generate-deep-pitch',
        json=startup
    )
    print(f"Generated pitch for {startup['name']}")
```

### Integration with Frontend
```javascript
// Add to your pitch generator form
document.getElementById('pitchForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const name = document.getElementById('startupName').value;
  const description = document.getElementById('description').value;
  
  const response = await fetch('/api/generate-deep-pitch', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ name, description })
  });
  
  const data = await response.json();
  
  if (data.success) {
    displayPitch(data.pitch);
    saveProjectId(data.project_id);
  }
});
```

---

## 📝 Notes

- **Context search is optional** - Pipeline works without it
- **Models can be swapped** - Use any HuggingFace model
- **Prompts are customizable** - Adjust for your use case
- **Output is markdown** - Easy to convert to other formats
- **Saved as project** - Accessible via project ID

---

## 🎉 Summary

The Deep Pitch Pipeline transforms simple startup ideas into comprehensive, investor-grade pitch decks through:

✅ **Multi-step generation** for depth and coherence  
✅ **Contextual search** for real market intelligence  
✅ **Dual models** for specialized content creation  
✅ **Professional output** ready for investor presentations  
✅ **Robust fallbacks** ensuring reliable operation  

**Ready to generate investor-grade pitches!** 🚀
