"""
Hugging Face Inference API Client
Free alternative to Gemini for pitch deck generation
Uses a hybrid approach with Mistral and Zephyr models
"""
import os
import requests
import json
import time

HF_TOKEN = os.getenv('HF_API_TOKEN')
HEADERS = {'Authorization': f'Bearer {HF_TOKEN}'} if HF_TOKEN else {}

# Free Hugging Face models for inference
MISTRAL_URL = 'https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3'
ZEPHYR_URL = 'https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta'
MIXTRAL_URL = 'https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1'

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
