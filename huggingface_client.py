"""
AI generation client (Google Gemini).
Module name kept for import compatibility; all generation goes through
query_with_fallback(), which calls Gemini with model fallback.
"""
import os
import requests
import json
import re
import time
from datetime import datetime

# Google Gemini (generateContent REST API). Model IDs can be overridden via env.
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
GEMINI_API_BASE = 'https://generativelanguage.googleapis.com/v1beta/models'

# Keys are kept for backward compatibility with the stage fallback lists below.
FREE_MODELS = {
    'mistral': os.getenv('GEMINI_MODEL_PRIMARY', 'gemini-flash-latest'),
    'zephyr': os.getenv('GEMINI_MODEL_SECONDARY', 'gemini-flash-lite-latest'),
}
# Optional third fallback (e.g. a Pro model on a paid key). Pro has no free-tier quota.
if os.getenv('GEMINI_MODEL_TERTIARY'):
    FREE_MODELS['phi'] = os.getenv('GEMINI_MODEL_TERTIARY')

# Wall-clock budget for one generation request (Vercel maxDuration is 60s)
REQUEST_BUDGET_SECONDS = int(os.getenv('GEMINI_REQUEST_BUDGET', '50'))
_deadline = None


def _time_left():
    return float('inf') if _deadline is None else _deadline - time.monotonic()

# Model fallback priority for each stage
MODEL_PRIORITY = [k for k in ('mistral', 'zephyr', 'phi') if k in FREE_MODELS]

# Depth prompt for investor-grade content
DEPTH_PROMPT = '''You are PitchPerfectAI, an expert investor and pitch consultant. Create detailed, data-backed, assertive pitch deck content. Write finished, confident paragraphs for investor pitch decks.'''

# Track verified models (cache to avoid repeated checks)
VERIFIED_MODELS = {}

# Reasons for the most recent failures, surfaced in error messages
LAST_ERRORS = []


def _record_error(msg):
    LAST_ERRORS.append(msg)
    del LAST_ERRORS[:-5]


def log_timestamp(stage, message):
    """Log with timestamp for tracking"""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"[{timestamp}] {stage}: {message}")


def get_context_ddgs(query):
    """
    Get contextual information using DDGS (duckduckgo search library v9+)
    """
    try:
        log_timestamp("DDGS", f"Searching: {query[:50]}...")
        from ddgs import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=2))
        
        snippets = '\n'.join([r.get('body', '') for r in results if r.get('body')])
        log_timestamp("DDGS", f"✓ Found {len(snippets)} chars")
        return snippets or ''
    except ImportError:
        log_timestamp("DDGS", "❌ Not installed: pip install ddgs")
        return ''
    except Exception as e:
        log_timestamp("DDGS", f"❌ Failed: {str(e)}")
        return ''


def discover_gemini_model(exclude=()):
    """
    Ask the Gemini API which models this key can use and pick the best
    text model (prefers stable Flash, newest version). Google retires
    model IDs regularly, so this avoids hardcoding a dead name.
    """
    try:
        response = requests.get(GEMINI_API_BASE, headers={'x-goog-api-key': GOOGLE_API_KEY},
                                params={'pageSize': 200}, timeout=20)
        if response.status_code != 200:
            _record_error(f"ListModels: HTTP {response.status_code} {response.text[:120]}")
            return None
        names = [
            m['name'].split('/', 1)[-1] for m in response.json().get('models', [])
            if 'generateContent' in m.get('supportedGenerationMethods', [])
        ]
    except Exception as e:
        _record_error(f"ListModels: {e}")
        return None

    def score(name):
        n = name.lower()
        if not n.startswith('gemini') or any(t in n for t in ('image', 'tts', 'audio', 'live', 'embedding', 'vision', 'thinking')):
            return None
        m = re.search(r'gemini-(\d+)(?:\.(\d+))?', n)
        version = (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)
        return (
            'flash' in n and 'lite' not in n,      # prefer full Flash
            'preview' not in n and 'exp' not in n, # prefer stable
            version,                               # prefer newest
        )

    candidates = [(score(n), n) for n in names if n not in exclude and score(n) is not None]
    if not candidates:
        _record_error(f"ListModels: no usable Gemini text model among {names[:10]}")
        return None
    best = max(candidates)[1]
    log_timestamp("MODELS", f"Discovered Gemini model: {best}")
    return best


def verify_endpoint(model_key):
    """
    Check that a model is configured and has not been marked unavailable.
    (No extra network round-trip: the real request reports availability.)
    """
    return model_key in FREE_MODELS and VERIFIED_MODELS.get(model_key, True)


def query_with_fallback(prompt, stage_name, preferred_models=None):
    """
    Query models with smart fallback chain
    Tries models in priority order until one succeeds

    Returns:
        Generated text or None if all models fail
    """
    if not GOOGLE_API_KEY:
        log_timestamp(stage_name, "❌ GOOGLE_API_KEY is not set")
        _record_error("GOOGLE_API_KEY is not set on the server")
        return None

    LAST_ERRORS.clear()
    # Always prefer the primary Gemini model; stage lists only affect fallback order
    models_to_try = MODEL_PRIORITY

    for model_key in models_to_try:
        if not verify_endpoint(model_key):
            log_timestamp(stage_name, f"⏭ Skipping {model_key} (not available)")
            continue

        result = query_inference_api(prompt, FREE_MODELS[model_key], stage_name, model_key)
        if result:
            return result

    # Configured models unavailable (e.g. retired): discover one this key can use
    if not any(verify_endpoint(k) for k in FREE_MODELS):
        discovered = discover_gemini_model()
        if discovered:
            FREE_MODELS['mistral'] = discovered
            VERIFIED_MODELS['mistral'] = True
            result = query_inference_api(prompt, discovered, stage_name, 'mistral')
            if result:
                return result

    log_timestamp(stage_name, "❌ All models failed")
    return None


def query_inference_api(prompt, model_id, stage_name, model_key, max_retries=3):
    """
    Query Google Gemini (generateContent) with retry logic
    """
    url = f"{GEMINI_API_BASE}/{model_id}:generateContent"
    payload = {
        'contents': [{'role': 'user', 'parts': [{'text': prompt[:30000]}]}],
        'generationConfig': {'temperature': 0.7, 'topP': 0.95, 'maxOutputTokens': 2048},
    }
    headers = {'Content-Type': 'application/json', 'x-goog-api-key': GOOGLE_API_KEY}

    for attempt in range(max_retries):
        try:
            log_timestamp(stage_name, f"Querying {model_id} (attempt {attempt + 1}/{max_retries})")
            if _time_left() < 8:
                _record_error(f"{model_id}: skipped, request time budget exhausted")
                return None
            response = requests.post(url, headers=headers, json=payload, timeout=max(5, min(55, _time_left() - 2)))

            if response.status_code == 200:
                data = response.json()
                candidates = data.get('candidates') or []
                parts = (candidates[0].get('content') or {}).get('parts', []) if candidates else []
                text = ''.join(p.get('text', '') for p in parts).strip()
                if not text:
                    reason = candidates[0].get('finishReason') if candidates else data.get('promptFeedback')
                    log_timestamp(stage_name, f"⚠ Empty response from {model_id} ({reason})")
                    _record_error(f"{model_id}: empty response ({reason})")
                    return None
                log_timestamp(stage_name, f"✓ Generated {len(text)} chars with {model_id}")
                return text

            if response.status_code == 404:
                # Model not available for this key - don't retry, try next model
                log_timestamp(stage_name, f"❌ 404 for {model_id}: {response.text[:150]}")
                VERIFIED_MODELS[model_key] = False
                _record_error(f"{model_id}: HTTP 404 (model not available) {response.text[:100]}")
                return None

            if response.status_code in (400, 401, 403):
                log_timestamp(stage_name, f"❌ {response.status_code} for {model_id}: {response.text[:150]}")
                _record_error(f"{model_id}: HTTP {response.status_code} {response.text[:150]}")
                return None

            log_timestamp(stage_name, f"⚠ {response.status_code}: {response.text[:150]}")
            _record_error(f"{model_id}: HTTP {response.status_code} {response.text[:120]}")
            if response.status_code == 429:
                # Quota exhausted for this model - retrying won't help, try the next one
                return None
            # 503 overloaded / other 5xx: back off and retry while time allows
            wait = 3 * (attempt + 1)
            if attempt < max_retries - 1 and _time_left() > wait + 15:
                time.sleep(wait)

        except requests.exceptions.Timeout:
            log_timestamp(stage_name, f"⏱ Timeout on attempt {attempt + 1}")
            _record_error(f"{model_id}: timed out")
        except Exception as e:
            log_timestamp(stage_name, f"❌ Error on attempt {attempt + 1}: {str(e)}")
            _record_error(f"{model_id}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))

    return None


def load_flan_locally():
    """
    Load FLAN-T5 locally using transformers (optional)
    
    NOTE: On Vercel, transformers/torch are not included (too large).
    This will gracefully fail and be skipped.
    """
    try:
        log_timestamp("FLAN-T5", "Attempting local load...")
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        
        # Try large first
        try:
            tokenizer = AutoTokenizer.from_pretrained('google/flan-t5-large')
            model = AutoModelForSeq2SeqLM.from_pretrained('google/flan-t5-large')
            log_timestamp("FLAN-T5", "✓ Loaded flan-t5-large locally")
            return model, tokenizer
        except Exception as e:
            log_timestamp("FLAN-T5", f"⏭ Large failed, trying base: {str(e)[:50]}")
            
        # Fallback to base
        tokenizer = AutoTokenizer.from_pretrained('google/flan-t5-base')
        model = AutoModelForSeq2SeqLM.from_pretrained('google/flan-t5-base')
        log_timestamp("FLAN-T5", "✓ Loaded flan-t5-base locally")
        return model, tokenizer
        
    except ImportError:
        log_timestamp("FLAN-T5", "⏭ Skipped (transformers not installed)")
        return None, None
    except Exception as e:
        log_timestamp("FLAN-T5", f"❌ Failed: {str(e)[:100]}")
        return None, None


def preprocess_with_flan(startup_name, startup_description):
    """
    Stage 0: Use FLAN-T5 locally for structural analysis (optional)
    """
    model, tokenizer = load_flan_locally()
    if not model or not tokenizer:
        return None
    
    try:
        prompt = f"""Extract key elements from this startup:

Name: {startup_name}
Description: {startup_description}

List:
1. Core Problem
2. Solution Approach
3. Target Market
4. Value Proposition
5. Business Model

Be concise."""

        log_timestamp("FLAN-T5", "Running preprocessing...")
        inputs = tokenizer(prompt, return_tensors='pt', max_length=512, truncation=True)
        outputs = model.generate(**inputs, max_new_tokens=300, temperature=0.7)
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        log_timestamp("FLAN-T5", f"✓ Generated {len(result)} chars")
        return result
        
    except Exception as e:
        log_timestamp("FLAN-T5", f"❌ Processing failed: {str(e)}")
        return None


def intelligent_pitch_generation(startup_name, startup_description):
    """
    Generate an investor pitch in a single Gemini call.

    Market context from a web search is added when available. One request
    (instead of one per section) keeps generation within the serverless time
    limit and makes it far less likely to hit transient 503/429 errors.
    """
    global _deadline
    _deadline = time.monotonic() + REQUEST_BUDGET_SECONDS
    log_timestamp("PIPELINE", f"Starting pitch generation for: {startup_name}")

    context_snippet = get_context_ddgs(f'{startup_name} industry trends') or ''

    prompt = f"""{DEPTH_PROMPT}

Write the investor pitch deck content for this startup.

Startup: {startup_name}
Description: {startup_description}
Market context from a web search (may be partial or irrelevant; use only if helpful):
{context_snippet[:1500]}

Output Markdown with exactly these five sections, each a level-2 heading, in this order:
## Problem
## Solution
## Market Opportunity
## Business Model & Competitive Advantage
## The Ask

Rules:
- Each section: 2-4 substantive paragraphs (bullets allowed for Market and Business Model).
- Market Opportunity: TAM/SAM/SOM with figures, growth, competitive landscape, target segments.
- Business Model: revenue model, competitive advantage, go-to-market, funding ask.
- Do not use level-1 or level-3+ headings, and do not add any text before the first section."""

    try:
        body = query_with_fallback(prompt, "PITCH")
    finally:
        _deadline = None

    if not body:
        raise Exception(f"PITCH GENERATION FAILED: {'; '.join(LAST_ERRORS) or 'unknown error'}")

    # Keep the frontend's '##' section split intact
    body = re.sub(r'^#{3,}\s*(.+?)\s*$', r'**\1**', body, flags=re.M)
    body = re.sub(r'^#\s+.*\n?', '', body, flags=re.M).strip()

    final_pitch = f"""# {startup_name} Pitch Deck

{body}

---

*Generated by PitchPerfectAI - Powered by Google Gemini*
"""
    log_timestamp("PIPELINE", f"✓ Complete - {len(final_pitch)} chars generated")
    return final_pitch


def friendly_error(raw):
    """Map a raw generation error to a short, user-facing message."""
    text = str(raw)
    if 'API_KEY is not set' in text or 'HTTP 400' in text or 'HTTP 401' in text or 'HTTP 403' in text:
        return "Pitch generation isn't configured correctly right now. Please try again later or contact support if this continues."
    if 'HTTP 503' in text or 'high demand' in text or 'overloaded' in text.lower():
        return "Our AI provider is experiencing very high demand right now. Please wait a minute and try again."
    if 'HTTP 429' in text or 'quota' in text.lower():
        return "We've hit our AI usage limit for the moment. Please try again in a few minutes."
    if 'timed out' in text or 'time budget' in text:
        return "Generating your pitch took too long. Please try again."
    return "Something went wrong while generating your pitch. Please try again."


# API Compatibility Functions

def generate_pitch_json(readme_content, extra_context=None):
    """Generate pitch deck JSON using Free Inference API"""
    prompt = f"""Generate a pitch deck in JSON format for this project.

README Content:
{readme_content[:1500]}

{f"Additional Context: {extra_context[:500]}" if extra_context else ""}

Create a JSON object with these exact fields:
- title, introduction, problem_statement, solution_overview, key_features, target_audience, technology_stack, future_scope

Return ONLY valid JSON."""

    log_timestamp("API", "Generating pitch JSON...")
    result = query_with_fallback(prompt, "JSON-GEN", ['mistral', 'zephyr'])
    
    if result:
        try:
            text = result.strip()
            if text.startswith('```json'):
                text = text[7:]
            elif text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end]
                parsed = json.loads(json_str)
                log_timestamp("API", "✓ JSON parsed successfully")
                return parsed
        except Exception as e:
            log_timestamp("API", f"⚠ JSON parsing failed: {str(e)}")
    
    log_timestamp("API", "Using fallback template")
    return generate_basic_template(readme_content)


def generate_basic_template(readme_content):
    """Generate a basic pitch deck template from README content"""
    lines = readme_content.split('\n')
    title = lines[0].strip('#').strip() if lines else "Project Pitch Deck"
    
    return {
        "title": title,
        "introduction": f"This is an innovative project that aims to solve real-world problems. Based on the codebase analysis, this project shows strong technical implementation and clear value proposition.",
        "problem_statement": "Many users face challenges that require efficient, scalable solutions. Current alternatives are often complex, expensive, or lack key features that users need.",
        "solution_overview": f"{title} addresses these challenges through a well-architected solution that combines modern technology with user-centric design.",
        "key_features": "• Modern, scalable architecture\n• User-friendly interface\n• Robust error handling\n• Comprehensive documentation",
        "target_audience": "This solution is designed for developers, businesses, and organizations looking for reliable, efficient tools.",
        "technology_stack": "Built with modern, industry-standard technologies ensuring reliability, maintainability, and scalability.",
        "future_scope": "Future development will focus on expanding features, improving performance, and incorporating user feedback."
    }


def refine_pitch_content(draft_content, refinement_prompt):
    """Refine pitch deck content using a second model pass"""
    prompt = f"""{refinement_prompt}

Current Content:
{draft_content[:1000]}

Provide improved content that is specific, data-driven, and compelling."""

    result = query_with_fallback(prompt, "REFINE", ['zephyr', 'mistral'])
    return result if result else draft_content


def deep_pitch_generation(startup_name, startup_description):
    """Backward compatibility wrapper"""
    return intelligent_pitch_generation(startup_name, startup_description)


# Test function
def test_visionARy_pipeline():
    """
    END-TO-END TEST: VisionARy pitch generation
    """
    print("\n" + "="*80)
    print("🧪 TESTING PITCH GENERATION PIPELINE - VisionARy")
    print("="*80 + "\n")
    
    startup_name = "VisionARy"
    startup_description = "An AR accessibility platform for the visually impaired that uses computer vision and spatial audio to help users navigate spaces, read text, and identify objects in real-time."
    
    print(f"📋 Startup: {startup_name}")
    print(f"📝 Description: {startup_description}")
    print("\n" + "="*80 + "\n")
    
    try:
        start_time = time.time()
        pitch = intelligent_pitch_generation(startup_name, startup_description)
        end_time = time.time()
        
        print("\n" + "="*80)
        print("✅ SUCCESS - PIPELINE COMPLETED")
        print("="*80 + "\n")
        
        print("📊 GENERATED PITCH DECK:")
        print("-" * 80)
        print(pitch)
        print("-" * 80)
        
        print("\n" + "="*80)
        print("📈 VALIDATION SUMMARY:")
        print("="*80)
        print(f"⏱  Total Time: {end_time - start_time:.2f}s")
        print(f"📝 Total Length: {len(pitch)} characters")
        print(f"💰 Total Cost: $0.00 (All free resources)")
        print("\n✓ Cognitive Layers Executed:")
        print("  • FLAN-T5 (Local preprocessing) - Optional")
        print("  • DDGS (Market context search)")
        print("  • AI Models (Problem, Solution, Market, Business)")
        print("  • Smart fallback chain active")
        print("\n🚀 Pipeline Status: FULLY OPERATIONAL")
        print("="*80 + "\n")
        
        return pitch
        
    except Exception as e:
        print("\n" + "="*80)
        print("❌ PIPELINE FAILED")
        print("="*80)
        print(f"Error: {str(e)}")
        print("\n🔍 Troubleshooting:")
        print("1. Check GOOGLE_API_KEY is set: export GOOGLE_API_KEY=...")
        print("2. Verify internet connection for API calls")
        print("3. Check Gemini API status: https://aistudio.google.com/status")
        print("4. Install ddgs: pip install ddgs")
        print("5. Models may be loading (503) - retry in 30 seconds")
        print("="*80 + "\n")
        raise


if __name__ == "__main__":
    # Run VisionARy test when executed directly
    test_visionARy_pipeline()
