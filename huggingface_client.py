"""
Hugging Face Inference API Client
Free alternative to Gemini for pitch deck generation
Uses a hybrid approach with FLAN-T5 pre-processing + Mistral/Zephyr models

UPGRADED: Multi-stage intelligent pipeline:
1. FLAN-T5 (local) - Structural analysis and extraction
2. Mistral-7B - Deep problem and market analysis
3. Zephyr-7B - Solution articulation and business strategy
"""
import os
import requests
import json
import time
from duckduckgo_search import DDGS

HF_TOKEN = os.getenv('HF_API_TOKEN')
HEADERS = {'Authorization': f'Bearer {HF_TOKEN}'} if HF_TOKEN else {}

# Hugging Face Inference API models (require license acceptance)
# IMPORTANT: You must accept licenses at:
# - https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3
# - https://huggingface.co/HuggingFaceH4/zephyr-7b-beta
MISTRAL_URL = 'https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3'
ZEPHYR_URL = 'https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta'
MIXTRAL_URL = 'https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1'

# FLAN-T5 for local pre-processing (loaded on-demand)
FLAN_MODEL = None
FLAN_TOKENIZER = None

# Depth prompt for investor-grade content
DEPTH_PROMPT = '''You are PitchPerfectAI, an expert investor and pitch consultant. You create detailed, data-backed, assertive pitch deck content. You never give vague suggestions; instead, you write finished, confident paragraphs that can go directly into an investor pitch deck.'''

def load_flan_model():
    """Load FLAN-T5 model locally for pre-processing (lazy loading)"""
    global FLAN_MODEL, FLAN_TOKENIZER
    
    if FLAN_MODEL is None:
        try:
            print("DEBUG: Loading FLAN-T5 model for pre-processing...")
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            
            FLAN_TOKENIZER = AutoTokenizer.from_pretrained('google/flan-t5-base')
            FLAN_MODEL = AutoModelForSeq2SeqLM.from_pretrained('google/flan-t5-base')
            print("DEBUG: FLAN-T5 model loaded successfully")
        except Exception as e:
            print(f"DEBUG: Failed to load FLAN-T5: {str(e)}")
            print("DEBUG: Will skip pre-processing stage")
            return False
    
    return FLAN_MODEL is not None

def preprocess_with_flan(startup_name, startup_description):
    """
    Use FLAN-T5 locally to extract structural elements from startup description
    This creates a structured summary that feeds into Mistral/Zephyr
    """
    if not load_flan_model():
        print("DEBUG: FLAN-T5 not available, skipping pre-processing")
        return None
    
    try:
        prompt = f"""Extract key structural elements from this startup description. 
        
Startup: {startup_name}
Description: {startup_description}

Identify and list:
1. Core Problem being solved
2. Proposed Solution approach
3. Target Market/Customers
4. Key Value Proposition
5. Potential Business Model

Return a concise bullet summary."""

        print("DEBUG: Running FLAN-T5 pre-processing...")
        inputs = FLAN_TOKENIZER(prompt, return_tensors='pt', max_length=512, truncation=True)
        outputs = FLAN_MODEL.generate(**inputs, max_new_tokens=300, temperature=0.7)
        structured_summary = FLAN_TOKENIZER.decode(outputs[0], skip_special_tokens=True)
        
        print(f"DEBUG: FLAN-T5 structured summary: {len(structured_summary)} chars")
        return structured_summary
        
    except Exception as e:
        print(f"DEBUG: FLAN-T5 pre-processing failed: {str(e)}")
        return None

def query_model(prompt, model_url, max_retries=3):
    """Query a Hugging Face model with retry logic"""
    # Check if HF token is configured
    if not HF_TOKEN:
        print(f"WARNING: HF_API_TOKEN not configured! Set it in environment variables.")
    
    for attempt in range(max_retries):
        try:
            # Format prompt for instruction-tuned models
            formatted_prompt = f"[INST] {prompt[:2000]} [/INST]"
            
            payload = {
                'inputs': formatted_prompt,
                'parameters': {
                    'max_new_tokens': 1000,
                    'temperature': 0.7,
                    'top_p': 0.95,
                    'return_full_text': False,
                    'do_sample': True
                },
                'options': {
                    'wait_for_model': True,
                    'use_cache': False
                }
            }
            
            print(f"DEBUG: Querying {model_url} (attempt {attempt + 1}/{max_retries})")
            print(f"DEBUG: Using HF token: {'Yes' if HF_TOKEN else 'No'}")
            response = requests.post(model_url, headers=HEADERS, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle different response formats
                if isinstance(data, list) and len(data) > 0:
                    if 'generated_text' in data[0]:
                        text = data[0]['generated_text']
                        print(f"DEBUG: Model response length: {len(text)} chars")
                        return text
                elif isinstance(data, dict) and 'generated_text' in data:
                    text = data['generated_text']
                    print(f"DEBUG: Model response length: {len(text)} chars")
                    return text
                
                print(f"DEBUG: Unexpected response format: {data}")
                
            elif response.status_code == 503:
                # Model is loading, wait and retry
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"DEBUG: Model loading (503), waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            elif response.status_code == 404:
                print(f"DEBUG: Model not found (404).")
                print(f"DEBUG: Full response: {response.text}")
                print(f"DEBUG: Model URL: {model_url}")
                # Don't retry on 404 - model doesn't exist
                return None
            elif response.status_code == 403:
                print(f"DEBUG: Access forbidden (403). Check if model requires authentication.")
                print(f"DEBUG: Response: {response.text[:300]}")
                return None
            else:
                print(f"DEBUG: API error {response.status_code}")
                print(f"DEBUG: Response: {response.text[:300]}")
                
        except Exception as e:
            print(f"DEBUG: Query error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
    
    return None

def generate_pitch_json(readme_content, extra_context=None):
    """
    Generate pitch deck JSON using Hugging Face models
    Returns a dict with pitch deck structure
    """
    # Build prompt for structured JSON output
    prompt = f"""Generate a pitch deck in JSON format for this project.

README Content:
{readme_content[:1500]}

{f"Additional Context: {extra_context[:500]}" if extra_context else ""}

Create a JSON object with these exact fields:
- title: Project name (string)
- introduction: Brief intro, 2-3 sentences (string)
- problem_statement: Problem being solved, 3-4 sentences (string)
- solution_overview: How project solves it, 3-4 sentences (string)
- key_features: Main features as bullet points (string)
- target_audience: Who it's for, 2-3 sentences (string)
- technology_stack: Technologies used (string)
- future_scope: Future plans, 2-3 sentences (string)

Return ONLY valid JSON, no markdown formatting or extra text."""

    # Try Mixtral first (most capable)
    print("DEBUG: Trying Mixtral for pitch generation...")
    result = query_model(prompt, MIXTRAL_URL)
    
    if not result:
        # Fallback to Mistral
        print("DEBUG: Mixtral failed, trying Mistral...")
        result = query_model(prompt, MISTRAL_URL)
    
    if not result:
        # Fallback to Zephyr
        print("DEBUG: Mistral failed, trying Zephyr...")
        result = query_model(prompt, ZEPHYR_URL)
    
    if result:
        # Try to extract JSON from response
        try:
            # Clean up response
            text = result.strip()
            
            # Remove markdown code blocks
            if text.startswith('```json'):
                text = text[7:]
            elif text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            
            # Find JSON object
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end]
                parsed = json.loads(json_str)
                print("DEBUG: Successfully parsed JSON from Hugging Face")
                return parsed
        except Exception as e:
            print(f"DEBUG: JSON parsing failed: {str(e)}")
    
    # If all fails, return basic template
    print("DEBUG: All Hugging Face models failed, using template")
    return generate_basic_template(readme_content)

def generate_basic_template(readme_content):
    """Generate a basic pitch deck template from README content"""
    lines = readme_content.split('\n')
    title = lines[0].strip('#').strip() if lines else "Project Pitch Deck"
    
    return {
        "title": title,
        "introduction": f"This is an innovative project that aims to solve real-world problems. Based on the codebase analysis, this project shows strong technical implementation and clear value proposition.",
        "problem_statement": "Many users face challenges that require efficient, scalable solutions. Current alternatives are often complex, expensive, or lack key features that users need.",
        "solution_overview": f"{title} addresses these challenges through a well-architected solution that combines modern technology with user-centric design. The implementation focuses on reliability, performance, and ease of use.",
        "key_features": "• Modern, scalable architecture\n• User-friendly interface\n• Robust error handling\n• Comprehensive documentation\n• Active development and maintenance",
        "target_audience": "This solution is designed for developers, businesses, and organizations looking for reliable, efficient tools. It serves both technical and non-technical users who need powerful yet accessible solutions.",
        "technology_stack": "Built with modern, industry-standard technologies ensuring reliability, maintainability, and scalability. The stack is chosen for optimal performance and developer experience.",
        "future_scope": "Future development will focus on expanding features, improving performance, and incorporating user feedback. Plans include enhanced integrations, additional customization options, and continued optimization."
    }

def refine_pitch_content(draft_content, refinement_prompt):
    """
    Refine pitch deck content using a second model pass
    Used for Pitchy chatbot improvements
    """
    prompt = f"""{refinement_prompt}

Current Content:
{draft_content[:1000]}

Provide improved content that is specific, data-driven, and compelling."""

    # Use Zephyr for refinement (good at following instructions)
    result = query_model(prompt, ZEPHYR_URL)
    
    if not result:
        # Fallback to Mistral
        result = query_model(prompt, MISTRAL_URL)
    
    return result if result else draft_content


# ============================================================================
# MULTI-STEP DEPTH PIPELINE FOR INVESTOR-GRADE PITCH DECKS
# ============================================================================

def get_context(query):
    """
    Get contextual information from DuckDuckGo search
    Returns snippets of relevant information for the query
    """
    try:
        print(f"DEBUG: Searching for context: {query}")
        # DDGS v8+ uses different initialization
        results = DDGS().text(query, max_results=2)
        snippets = '\n'.join([r.get('body', '') for r in results if r.get('body')])
        print(f"DEBUG: Context found: {len(snippets)} chars")
        return snippets or ''
    except Exception as e:
        print(f"DEBUG: Context search failed: {str(e)}")
        # Gracefully continue without context
        return ''


def intelligent_pitch_generation(startup_name, startup_description):
    """
    INTELLIGENT MULTI-STAGE PIPELINE for investor-grade pitch decks
    
    Stage 0: FLAN-T5 (local) - Extract structural elements
    Stage 1: Mistral-7B - Deep problem analysis
    Stage 2: Zephyr-7B - Solution articulation
    Stage 3: Mistral-7B - Market opportunity
    Stage 4: Zephyr-7B - Business model & traction
    
    Args:
        startup_name: Name of the startup
        startup_description: Brief description of what the startup does
    
    Returns:
        Markdown-formatted pitch deck with Problem, Solution, Market, and Business Model sections
    """
    print(f"DEBUG: Starting intelligent pitch generation for {startup_name}")
    
    # Stage 0: FLAN-T5 Pre-processing (local structural analysis)
    structured_summary = preprocess_with_flan(startup_name, startup_description)
    
    # Get market context from web search
    context_snippet = get_context(f'{startup_name} industry trends 2025')
    
    # Stage 1: Problem Statement (Mistral-7B with FLAN pre-processing)
    print("DEBUG: Stage 1 - Generating problem statement with Mistral...")
    
    # Use FLAN structured summary if available
    context_info = f"\nStructured Analysis:\n{structured_summary}\n" if structured_summary else ""
    
    problem_prompt = f"""{DEPTH_PROMPT}

Write a comprehensive problem statement for {startup_name}. 

Description: {startup_description}
{context_info}
Market Context:
{context_snippet[:500]}

Focus on real pain points, inefficiencies, and urgency in the market. Write 3-4 detailed paragraphs that investors will find compelling. Include specific statistics or market insights where relevant."""
    
    problem = query_model(problem_prompt, MISTRAL_URL)
    if not problem:
        problem = "The market faces significant challenges that require innovative solutions. Current alternatives are inadequate, creating a substantial opportunity for disruption."
    
    # Stage 2: Solution Overview (Zephyr-7B)
    print("DEBUG: Stage 2 - Generating solution overview with Zephyr...")
    solution_prompt = f"""{DEPTH_PROMPT}

Given this problem:
{problem[:800]}
{context_info}
Write a persuasive, investor-level solution overview for {startup_name} that emphasizes innovation and differentiation.

Description: {startup_description}

Write 3-4 detailed paragraphs explaining how the solution works, what makes it unique, and why it's superior to alternatives. Be specific and confident."""
    
    solution = query_model(solution_prompt, ZEPHYR_URL)
    if not solution:
        solution = f"{startup_name} provides an innovative solution that addresses these challenges through cutting-edge technology and user-centric design."
    
    # Stage 3: Market Opportunity (Mistral-7B)
    print("DEBUG: Stage 3 - Generating market analysis with Mistral...")
    market_prompt = f"""{DEPTH_PROMPT}

Based on the startup {startup_name} and its solution:
{solution[:800]}

Market Context:
{context_snippet[:500]}

Generate a detailed market analysis, including:
- Total Addressable Market (TAM) with specific numbers
- Market trends and growth projections
- Competitive landscape overview
- Target customer segments

Write 3-4 detailed paragraphs with specific data points and projections."""
    
    market = query_model(market_prompt, MISTRAL_URL)
    if not market:
        market = "The market opportunity is substantial, with significant growth potential across multiple customer segments. Industry trends indicate strong demand for innovative solutions in this space."
    
    # Stage 4: Business Model & Traction (Zephyr-7B)
    print("DEBUG: Stage 4 - Generating business model with Zephyr...")
    business_prompt = f"""{DEPTH_PROMPT}

Using the context below:

Problem: {problem[:500]}
Solution: {solution[:500]}
Market: {market[:500]}
{context_info}
Write a comprehensive business model, traction, and go-to-market section for {startup_name} as if for a real investor deck.

Include:
- Revenue model and pricing strategy
- Go-to-market strategy
- Key partnerships or traction metrics
- Growth projections

Write 3-4 detailed paragraphs that demonstrate a clear path to profitability."""
    
    business = query_model(business_prompt, ZEPHYR_URL)
    if not business:
        business = f"{startup_name} employs a scalable business model with multiple revenue streams. The go-to-market strategy focuses on rapid customer acquisition and strategic partnerships."
    
    # Stage 5: Assemble Final Pitch
    print("DEBUG: Assembling final pitch deck...")
    
    # Add FLAN-T5 attribution if used
    generation_note = "*Generated by PitchPerfectAI - Intelligent Multi-Stage Pipeline*"
    if structured_summary:
        generation_note += "\n*Powered by FLAN-T5 structural analysis + Mistral-7B + Zephyr-7B*"
    
    final_pitch = f"""# {startup_name} Pitch Deck

## Problem
{problem}

## Solution
{solution}

## Market Opportunity
{market}

## Business Model & Traction
{business}

---

{generation_note}
"""
    
    print(f"DEBUG: Intelligent pitch generation complete - {len(final_pitch)} chars")
    return final_pitch


# Backward compatibility alias
def deep_pitch_generation(startup_name, startup_description):
    """
    Backward compatibility wrapper for intelligent_pitch_generation
    """
    return intelligent_pitch_generation(startup_name, startup_description)
