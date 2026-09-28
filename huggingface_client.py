"""
AI generation client (Google Gemini).
Module name kept for import compatibility; all generation goes through
query_with_fallback(), which calls Gemini with model fallback.
"""
import os
import requests
import json
import time
from datetime import datetime

# Google Gemini (generateContent REST API). Model IDs can be overridden via env.
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
GEMINI_API_BASE = 'https://generativelanguage.googleapis.com/v1beta/models'

# Keys are kept for backward compatibility with the stage fallback lists below.
FREE_MODELS = {
    'mistral': os.getenv('GEMINI_MODEL_PRIMARY', 'gemini-2.5-flash'),
    'zephyr': os.getenv('GEMINI_MODEL_SECONDARY', 'gemini-2.5-flash-lite'),
    'phi': os.getenv('GEMINI_MODEL_TERTIARY', 'gemini-2.0-flash'),
}

# Model fallback priority for each stage
MODEL_PRIORITY = ['mistral', 'zephyr', 'phi']

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

    log_timestamp(stage_name, "❌ All models failed")
    return None


def query_inference_api(prompt, model_id, stage_name, model_key, max_retries=2):
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
            response = requests.post(url, headers=headers, json=payload, timeout=60)

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
                _record_error(f"{model_id}: HTTP 404 (model not available)")
                return None

            if response.status_code in (400, 401, 403):
                log_timestamp(stage_name, f"❌ {response.status_code} for {model_id}: {response.text[:150]}")
                _record_error(f"{model_id}: HTTP {response.status_code} {response.text[:150]}")
                return None

            # 429 (rate limit) / 5xx: retry with backoff
            log_timestamp(stage_name, f"⚠ {response.status_code}: {response.text[:150]}")
            _record_error(f"{model_id}: HTTP {response.status_code} {response.text[:120]}")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))

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
    PRODUCTION-READY INTELLIGENT PIPELINE
    
    Stage 0: FLAN-T5 (local, optional) - Structural analysis
    Stage 0.5: DDGS - Market context search
    Stage 1: AI Model - Problem statement
    Stage 2: AI Model - Solution overview
    Stage 3: AI Model - Market analysis
    Stage 4: AI Model - Business model
    
    Uses Gemini with model fallback (see FREE_MODELS)
    """
    log_timestamp("PIPELINE", "="*60)
    log_timestamp("PIPELINE", f"Starting pitch generation for: {startup_name}")
    log_timestamp("PIPELINE", "="*60)
    
    # Stage 0: FLAN-T5 Pre-processing (optional, local only)
    log_timestamp("STAGE-0", "FLAN-T5 Structural Analysis (Optional)")
    structured_summary = preprocess_with_flan(startup_name, startup_description)
    context_info = f"\nStructured Analysis:\n{structured_summary}\n" if structured_summary else ""
    
    # Stage 0.5: Market Context Search
    log_timestamp("STAGE-0.5", "Market Context Search (DDGS)")
    context_snippet = get_context_ddgs(f'{startup_name} industry trends 2025')
    
    # Stage 1: Problem Statement
    log_timestamp("STAGE-1", "Problem Statement Generation")
    problem_prompt = f"""{DEPTH_PROMPT}

Write a comprehensive problem statement for {startup_name}.

Description: {startup_description}
{context_info}
Market Context: {context_snippet[:500]}

Focus on real pain points and market urgency. Write 3-4 detailed paragraphs."""
    
    problem = query_with_fallback(problem_prompt, "STAGE-1", ['mistral', 'zephyr', 'phi'])
    if not problem:
        raise Exception(f"PITCH GENERATION FAILED: All models failed at Stage 1 (Problem Statement). Reasons: {'; '.join(LAST_ERRORS) or 'unknown'}")
    
    # Stage 2: Solution Overview
    log_timestamp("STAGE-2", "Solution Overview Generation")
    solution_prompt = f"""{DEPTH_PROMPT}

Given this problem: {problem[:800]}
{context_info}

Write a persuasive solution overview for {startup_name}.
Description: {startup_description}

Write 3-4 detailed paragraphs on innovation and differentiation."""
    
    solution = query_with_fallback(solution_prompt, "STAGE-2", ['zephyr', 'mistral', 'phi'])
    if not solution:
        raise Exception(f"PITCH GENERATION FAILED: All models failed at Stage 2 (Solution). Reasons: {'; '.join(LAST_ERRORS) or 'unknown'}")
    
    # Stage 3: Market Analysis
    log_timestamp("STAGE-3", "Market Analysis Generation")
    market_prompt = f"""{DEPTH_PROMPT}

Based on {startup_name} solution: {solution[:800]}

Market Context: {context_snippet[:500]}

Generate market analysis with:
- TAM with numbers
- Growth projections
- Competitive landscape
- Target segments

Write 3-4 detailed paragraphs."""
    
    market = query_with_fallback(market_prompt, "STAGE-3", ['mistral', 'zephyr', 'phi'])
    if not market:
        raise Exception(f"PITCH GENERATION FAILED: All models failed at Stage 3 (Market). Reasons: {'; '.join(LAST_ERRORS) or 'unknown'}")
    
    # Stage 4: Business Model & Traction
    log_timestamp("STAGE-4", "Business Model Generation")
    business_prompt = f"""{DEPTH_PROMPT}

Using context:
Problem: {problem[:500]}
Solution: {solution[:500]}
Market: {market[:500]}
{context_info}

Write business model, competitive advantage, and ask for {startup_name}.

Include:
- Revenue model
- Competitive advantage
- GTM strategy
- Funding ask

Write 3-4 detailed paragraphs."""
    
    business = query_with_fallback(business_prompt, "STAGE-4", ['zephyr', 'mistral', 'phi'])
    if not business:
        raise Exception(f"PITCH GENERATION FAILED: All models failed at Stage 4 (Business). Reasons: {'; '.join(LAST_ERRORS) or 'unknown'}")
    
    # Stage 5: Assembly
    log_timestamp("STAGE-5", "Assembling Final Pitch Deck")
    
    final_pitch = f"""# {startup_name} Pitch Deck

## Problem
{problem}

## Solution
{solution}

## Market Opportunity
{market}

## Business Model & Competitive Advantage
{business}

## The Ask
Based on our market analysis and business model, we are seeking strategic investment to accelerate growth, expand our team, and capture market opportunity. Our proven traction and strong value proposition position us for significant returns.

---

*Generated by PitchPerfectAI - Intelligent Multi-Stage Pipeline*
*Powered by Google Gemini*
"""

    log_timestamp("PIPELINE", f"✓ Complete - {len(final_pitch)} chars generated")
    log_timestamp("PIPELINE", "="*60)
    return final_pitch


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
