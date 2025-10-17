"""
Hugging Face Inference API Client
Free alternative to Gemini for pitch deck generation
Uses a hybrid approach with Mistral and Zephyr models

UPGRADED: Now includes multi-step depth pipeline for investor-grade pitch decks
"""
import os
import requests
import json
import time
from duckduckgo_search import DDGS

HF_TOKEN = os.getenv('HF_API_TOKEN')
HEADERS = {'Authorization': f'Bearer {HF_TOKEN}'} if HF_TOKEN else {}

# Free Hugging Face models for inference
MISTRAL_URL = 'https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3'
ZEPHYR_URL = 'https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta'
MIXTRAL_URL = 'https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1'

# Depth prompt for investor-grade content
DEPTH_PROMPT = '''You are PitchPerfectAI, an expert investor and pitch consultant. You create detailed, data-backed, assertive pitch deck content. You never give vague suggestions; instead, you write finished, confident paragraphs that can go directly into an investor pitch deck.'''

def query_model(prompt, model_url, max_retries=3):
    """Query a Hugging Face model with retry logic"""
    for attempt in range(max_retries):
        try:
            payload = {
                'inputs': prompt[:2000],  # Limit input size
                'parameters': {
                    'max_new_tokens': 1000,
                    'temperature': 0.7,
                    'top_p': 0.95,
                    'return_full_text': False
                }
            }
            
            print(f"DEBUG: Querying {model_url} (attempt {attempt + 1}/{max_retries})")
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
                print(f"DEBUG: Model loading, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                print(f"DEBUG: API error {response.status_code}: {response.text}")
                
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
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=2)
            snippets = '\n'.join([r['body'] for r in results if 'body' in r])
            print(f"DEBUG: Context found: {len(snippets)} chars")
            return snippets or ''
    except Exception as e:
        print(f"DEBUG: Context search failed: {str(e)}")
        return ''


def deep_pitch_generation(startup_name, startup_description):
    """
    Generate detailed, investor-grade pitch deck using multi-step pipeline
    
    Args:
        startup_name: Name of the startup
        startup_description: Brief description of what the startup does
    
    Returns:
        Markdown-formatted pitch deck with Problem, Solution, Market, and Business Model sections
    """
    print(f"DEBUG: Starting deep pitch generation for {startup_name}")
    
    # Get market context
    context_snippet = get_context(f'{startup_name} industry trends 2025')
    
    # Step 1: Problem Statement
    print("DEBUG: Generating problem statement...")
    problem_prompt = f"""{DEPTH_PROMPT}

Write a comprehensive problem statement for {startup_name}. 

Description: {startup_description}

Market Context:
{context_snippet[:500]}

Focus on real pain points, inefficiencies, and urgency in the market. Write 3-4 detailed paragraphs that investors will find compelling. Include specific statistics or market insights where relevant."""
    
    problem = query_model(problem_prompt, MISTRAL_URL)
    if not problem:
        problem = "The market faces significant challenges that require innovative solutions. Current alternatives are inadequate, creating a substantial opportunity for disruption."
    
    # Step 2: Solution Overview
    print("DEBUG: Generating solution overview...")
    solution_prompt = f"""{DEPTH_PROMPT}

Given this problem:
{problem[:800]}

Write a persuasive, investor-level solution overview for {startup_name} that emphasizes innovation and differentiation.

Description: {startup_description}

Write 3-4 detailed paragraphs explaining how the solution works, what makes it unique, and why it's superior to alternatives. Be specific and confident."""
    
    solution = query_model(solution_prompt, ZEPHYR_URL)
    if not solution:
        solution = f"{startup_name} provides an innovative solution that addresses these challenges through cutting-edge technology and user-centric design."
    
    # Step 3: Market Opportunity
    print("DEBUG: Generating market analysis...")
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
    
    # Step 4: Business Model & Traction
    print("DEBUG: Generating business model...")
    business_prompt = f"""{DEPTH_PROMPT}

Using the context below:

Problem: {problem[:500]}
Solution: {solution[:500]}
Market: {market[:500]}

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
    
    # Step 5: Assemble Final Pitch
    print("DEBUG: Assembling final pitch deck...")
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

*Generated by PitchPerfectAI - Investor-Grade Pitch Deck Generator*
"""
    
    print(f"DEBUG: Deep pitch generation complete - {len(final_pitch)} chars")
    return final_pitch
