import os
import re
import json
from urllib.parse import urlparse
from datetime import datetime
from io import BytesIO

import requests
from flask import Blueprint, request, jsonify, send_file, redirect, url_for, session
from flask_login import login_required, current_user
import google.generativeai as genai
# PDF generation temporarily disabled for Vercel compatibility
# from reportlab.lib.pagesizes import letter, A4
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib.units import inch
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pptx import Presentation
from pptx.util import Inches as PptxInches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

from firebase_models import Project, User

api_bp = Blueprint('api', __name__)

def search_web_content(query, max_results=3):
    """Search the web for relevant content using a search API"""
    try:
        # Use DuckDuckGo Instant Answer API as a fallback search
        search_url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_redirect': '1',
            'no_html': '1',
            'skip_disambig': '1'
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            
            # Extract abstract and related topics
            if data.get('Abstract'):
                results.append({
                    'title': data.get('AbstractText', 'Market Research'),
                    'snippet': data.get('Abstract'),
                    'url': data.get('AbstractURL', '')
                })
            
            # Extract related topics
            for topic in data.get('RelatedTopics', [])[:max_results-1]:
                if isinstance(topic, dict) and topic.get('Text'):
                    results.append({
                        'title': topic.get('Text', '')[:100],
                        'snippet': topic.get('Text', ''),
                        'url': topic.get('FirstURL', '')
                    })
            
            return results[:max_results]
            
    except Exception as e:
        print(f"DEBUG: Web search failed: {str(e)}")
        
    # Fallback: return mock data based on query keywords
    return generate_mock_market_data(query)

def generate_mock_market_data(query):
    """Generate realistic mock market data when web search fails"""
    mock_data = []
    
    if "market size" in query.lower():
        mock_data.append({
            'title': 'Market Size Analysis',
            'snippet': f'The global market for {query.split()[0]} technology is projected to reach significant growth, with increasing adoption across various industries and expanding user base.',
            'url': ''
        })
    elif "trends" in query.lower():
        mock_data.append({
            'title': 'Industry Trends',
            'snippet': f'Current trends in {query.split()[0]} technology show accelerating innovation, increased investment, and growing market demand driven by digital transformation initiatives.',
            'url': ''
        })
    elif "competitors" in query.lower():
        mock_data.append({
            'title': 'Competitive Landscape',
            'snippet': f'The competitive landscape for {query.split()[0]} includes both established players and emerging startups, with differentiation opportunities in user experience and technical innovation.',
            'url': ''
        })
    else:
        mock_data.append({
            'title': 'Market Research',
            'snippet': f'Market analysis indicates growing opportunities in the {query.split()[0]} sector with favorable conditions for new entrants and innovative solutions.',
            'url': ''
        })
    
    return mock_data

def process_markdown_to_pptx(text, text_frame):
    """Process text and add it to PowerPoint text frame with enhanced formatting"""
    import re
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    
    # Clean up any remaining markdown symbols
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove ** bold markers
    text = re.sub(r'##\s*', '', text)  # Remove ## headers
    text = re.sub(r'#\s*', '', text)  # Remove # headers
    
    # Split text into lines
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:  # Skip empty lines
            continue
            
        if i > 0:  # Add new paragraph for each line except the first
            p = text_frame.add_paragraph()
        else:
            p = text_frame.paragraphs[0] if text_frame.paragraphs else text_frame.add_paragraph()
        
        # Set paragraph spacing for better readability
        p.space_before = Pt(6)
        p.space_after = Pt(6)
        
        # Check if this is a bullet point (starts with - or •)
        is_bullet = line.startswith('-') or line.startswith('•')
        if is_bullet:
            line = line[1:].strip()  # Remove bullet character
            p.level = 0  # Set bullet level
        
        # Check if this is an image prompt (contains "Image:" and parentheses)
        is_image_prompt = re.search(r'\(Image:', line, re.IGNORECASE)
        
        # Create text run
        run = p.add_run()
        run.text = line
        
        # Enhanced font styling
        run.font.name = 'Segoe UI'  # Modern, clean font
        run.font.color.rgb = RGBColor(0x2d, 0x2d, 0x2d)  # Dark gray for readability
        
        # Set font size based on content type
        if is_image_prompt:
            run.font.size = Pt(10)  # Small size for image prompts
            run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)  # Lighter gray for image prompts
            run.font.italic = True  # Italicize image prompts
        elif is_bullet:
            run.font.size = Pt(12)  # Body text size for bullet points
        else:
            run.font.size = Pt(12)  # Body text size for regular content

def add_slide_styling(slide, slide_title):
    """Add enhanced visual styling to slides"""
    try:
        from pptx.dml.color import RGBColor
        from pptx.enum.dml import MSO_THEME_COLOR
        
        # Add subtle gradient or accent colors based on slide type
        slide_type = slide_title.lower()
        
        # Define color schemes for different slide types
        if any(word in slide_type for word in ['problem', 'challenge', 'pain']):
            accent_color = RGBColor(0xd9, 0x53, 0x4f)  # Red for problems
        elif any(word in slide_type for word in ['solution', 'product', 'demo']):
            accent_color = RGBColor(0x5c, 0xb8, 0x5c)  # Green for solutions
        elif any(word in slide_type for word in ['market', 'opportunity', 'growth']):
            accent_color = RGBColor(0x42, 0x85, 0xf4)  # Blue for market
        elif any(word in slide_type for word in ['team', 'about', 'founder']):
            accent_color = RGBColor(0xff, 0x9f, 0x40)  # Orange for team
        elif any(word in slide_type for word in ['financial', 'revenue', 'funding']):
            accent_color = RGBColor(0x9c, 0x27, 0xb0)  # Purple for financials
        else:
            accent_color = RGBColor(0x1f, 0x4e, 0x79)  # Default professional blue
        
        # Try to add a subtle accent line or shape (this may not work on all templates)
        try:
            # Add a thin accent line at the top of the slide
            from pptx.shapes.autoshape import Shape
            from pptx.enum.shapes import MSO_SHAPE
            
            # Create a thin rectangle as accent line
            left = PptxInches(0)
            top = PptxInches(0)
            width = PptxInches(10)
            height = PptxInches(0.05)
            
            accent_shape = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, left, top, width, height
            )
            
            # Style the accent line
            fill = accent_shape.fill
            fill.solid()
            fill.fore_color.rgb = accent_color
            
            # Remove border
            line = accent_shape.line
            line.fill.background()
            
        except Exception:
            # If accent line fails, continue without it
            pass
            
    except Exception:
        # If styling fails, continue without enhanced styling
        pass

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Constants from original app
essential_readme_paths = [
    "README.md", "README.MD", "Readme.md", "README",
    "docs/README.md", "docs/README"
]

common_branches = ["main", "master", "develop"]

def parse_github_repo(url: str):
    """Return (owner, repo) if URL looks like a GitHub repo; else (None, None)."""
    if not url:
        return None, None
    try:
        u = urlparse(url)
    except Exception:
        return None, None

    host = (u.netloc or '').lower()
    if host not in {"github.com", "www.github.com"}:
        return None, None

    parts = [p for p in (u.path or '').split('/') if p]
    if len(parts) < 2:
        return None, None

    owner, repo = parts[0], parts[1]
    if repo.endswith('.git'):
        repo = repo[:-4]
    return owner, repo

def try_fetch_readme_raw(owner: str, repo: str):
    """Try common branches and README paths from raw.githubusercontent.com."""
    for br in common_branches:
        for p in essential_readme_paths:
            raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{br}/{p}"
            try:
                r = requests.get(raw, timeout=12)
                if r.status_code == 200 and r.text.strip():
                    return r.text, raw
            except requests.RequestException:
                continue
    return None, None

def try_fetch_readme_api(owner: str, repo: str, user_token: str = None):
    """Fallback to GitHub API to get the default README if possible."""
    api = f"https://api.github.com/repos/{owner}/{repo}/readme"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "PitchPerfectAI-saas",
    }
    # Use user's GitHub token first (for private repos), fallback to global token
    token = user_token or GITHUB_TOKEN
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(api, headers=headers, timeout=12)
        if r.status_code == 200:
            j = r.json()
            download_url = j.get("download_url")
            if download_url:
                rr = requests.get(download_url, timeout=12)
                if rr.status_code == 200 and rr.text.strip():
                    return rr.text, download_url
    except requests.RequestException:
        pass
    return None, None

def analyze_repository_structure(owner: str, repo: str, user_token: str = None) -> dict:
    """Analyze repository structure and code to extract project insights without README."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "PitchPerfectAI-saas",
    }
    if user_token:
        headers["Authorization"] = f"Bearer {user_token}"
    
    analysis = {
        "project_type": "Unknown",
        "tech_stack": [],
        "main_language": "Unknown",
        "frameworks": [],
        "features": [],
        "structure_insights": [],
        "dependencies": {},
        "file_count": 0,
        "directory_structure": []
    }
    
    try:
        # Get repository contents
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            contents = response.json()
            analysis["file_count"] = len(contents)
            
            # Analyze root directory structure
            for item in contents:
                if item["type"] == "dir":
                    analysis["directory_structure"].append(item["name"])
                elif item["type"] == "file":
                    filename = item["name"].lower()
                    
                    # Detect project type and tech stack from files
                    if filename == "package.json":
                        analysis["project_type"] = "Node.js/JavaScript"
                        analysis["tech_stack"].append("Node.js")
                        # Try to get package.json content for dependencies
                        try:
                            pkg_response = requests.get(item["download_url"], timeout=5)
                            if pkg_response.status_code == 200:
                                pkg_data = pkg_response.json()
                                if "dependencies" in pkg_data:
                                    analysis["dependencies"]["runtime"] = list(pkg_data["dependencies"].keys())[:10]
                                if "devDependencies" in pkg_data:
                                    analysis["dependencies"]["dev"] = list(pkg_data["devDependencies"].keys())[:10]
                        except:
                            pass
                    
                    elif filename == "requirements.txt":
                        analysis["project_type"] = "Python"
                        analysis["tech_stack"].append("Python")
                        # Try to get requirements content
                        try:
                            req_response = requests.get(item["download_url"], timeout=5)
                            if req_response.status_code == 200:
                                deps = [line.split("==")[0].split(">=")[0].split("<=")[0].strip() 
                                       for line in req_response.text.split("\n") if line.strip()]
                                analysis["dependencies"]["python"] = deps[:15]
                        except:
                            pass
                    
                    elif filename == "pom.xml":
                        analysis["project_type"] = "Java/Maven"
                        analysis["tech_stack"].extend(["Java", "Maven"])
                    
                    elif filename == "build.gradle":
                        analysis["project_type"] = "Java/Gradle"
                        analysis["tech_stack"].extend(["Java", "Gradle"])
                    
                    elif filename == "cargo.toml":
                        analysis["project_type"] = "Rust"
                        analysis["tech_stack"].append("Rust")
                    
                    elif filename == "go.mod":
                        analysis["project_type"] = "Go"
                        analysis["tech_stack"].append("Go")
                    
                    elif filename == "composer.json":
                        analysis["project_type"] = "PHP"
                        analysis["tech_stack"].append("PHP")
                    
                    elif filename in ["dockerfile", "docker-compose.yml", "docker-compose.yaml"]:
                        analysis["tech_stack"].append("Docker")
                    
                    elif filename in [".github", ".gitlab-ci.yml", "jenkinsfile"]:
                        analysis["features"].append("CI/CD Pipeline")
                    
                    elif filename in ["vercel.json", "netlify.toml"]:
                        analysis["features"].append("Cloud Deployment")
        
        # Get language statistics
        lang_url = f"https://api.github.com/repos/{owner}/{repo}/languages"
        lang_response = requests.get(lang_url, headers=headers, timeout=10)
        if lang_response.status_code == 200:
            languages = lang_response.json()
            if languages:
                analysis["main_language"] = max(languages.keys(), key=lambda k: languages[k])
                analysis["tech_stack"].extend(list(languages.keys())[:5])
        
        # Detect frameworks based on directory structure and dependencies
        dirs = analysis["directory_structure"]
        deps = analysis["dependencies"]
        
        # Web frameworks detection
        if "react" in str(deps).lower() or "src" in dirs:
            analysis["frameworks"].append("React")
        if "vue" in str(deps).lower():
            analysis["frameworks"].append("Vue.js")
        if "angular" in str(deps).lower():
            analysis["frameworks"].append("Angular")
        if "express" in str(deps).lower():
            analysis["frameworks"].append("Express.js")
        if "flask" in str(deps).lower() or "django" in str(deps).lower():
            analysis["frameworks"].append("Flask" if "flask" in str(deps).lower() else "Django")
        if "fastapi" in str(deps).lower():
            analysis["frameworks"].append("FastAPI")
        
        # Database detection
        if any(db in str(deps).lower() for db in ["mongodb", "mongoose"]):
            analysis["tech_stack"].append("MongoDB")
        if any(db in str(deps).lower() for db in ["postgresql", "psycopg", "pg"]):
            analysis["tech_stack"].append("PostgreSQL")
        if "mysql" in str(deps).lower():
            analysis["tech_stack"].append("MySQL")
        if "redis" in str(deps).lower():
            analysis["tech_stack"].append("Redis")
        
        # Structure insights
        if "api" in dirs or "backend" in dirs:
            analysis["structure_insights"].append("Backend API service")
        if "frontend" in dirs or "client" in dirs or "ui" in dirs:
            analysis["structure_insights"].append("Frontend application")
        if "docs" in dirs or "documentation" in dirs:
            analysis["structure_insights"].append("Well-documented project")
        if "tests" in dirs or "test" in dirs:
            analysis["structure_insights"].append("Includes test suite")
        if "scripts" in dirs or "bin" in dirs:
            analysis["structure_insights"].append("Automation scripts included")
        if "config" in dirs or "configs" in dirs:
            analysis["structure_insights"].append("Configurable application")
        
    except Exception as e:
        print(f"Error analyzing repository structure: {e}")
    
    return analysis

def fetch_additional_repo_signals(owner: str, repo: str, user_token: str = None) -> str:
    """Collect extra signals to help infer problem_statement and future_scope when README is sparse."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "PitchPerfectAI-saas",
    }
    # Use user's GitHub token first (for private repos), fallback to global token
    token = user_token or GITHUB_TOKEN
    if token:
        headers["Authorization"] = f"Bearer {token}"

    parts = []

    # Repo metadata
    try:
        repo_api = f"https://api.github.com/repos/{owner}/{repo}"
        r = requests.get(repo_api, headers=headers, timeout=12)
        if r.status_code == 200:
            j = r.json()
            desc = j.get("description") or ""
            topics = j.get("topics") or []
            if desc:
                parts.append(f"Repo Description: {desc}")
            if topics:
                parts.append("Topics: " + ", ".join(topics))
    except requests.RequestException:
        pass

    # Languages
    try:
        langs_api = f"https://api.github.com/repos/{owner}/{repo}/languages"
        r = requests.get(langs_api, headers=headers, timeout=12)
        if r.status_code == 200:
            langs = r.json() or {}
            if isinstance(langs, dict) and langs:
                top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:6]
                lang_list = ", ".join([f"{k} ({v})" for k, v in top])
                parts.append("Languages (bytes): " + lang_list)
    except requests.RequestException:
        pass

    return "\n\n".join(parts).strip()

def build_gemini_prompt_from_code(repo_analysis: dict, repo_name: str, extra_context: str = None) -> str:
    """Build AI prompt for pitch deck generation based on code analysis instead of README."""
    
    # Extract key information from analysis
    project_type = repo_analysis.get("project_type", "Unknown")
    tech_stack = repo_analysis.get("tech_stack", [])
    main_language = repo_analysis.get("main_language", "Unknown")
    frameworks = repo_analysis.get("frameworks", [])
    features = repo_analysis.get("features", [])
    structure_insights = repo_analysis.get("structure_insights", [])
    dependencies = repo_analysis.get("dependencies", {})
    file_count = repo_analysis.get("file_count", 0)
    directories = repo_analysis.get("directory_structure", [])
    
    # Build comprehensive analysis summary
    analysis_summary = f"""
PROJECT ANALYSIS SUMMARY:
Repository Name: {repo_name}
Project Type: {project_type}
Main Language: {main_language}
File Count: {file_count}

TECHNOLOGY STACK:
{', '.join(tech_stack[:10]) if tech_stack else 'Not detected'}

FRAMEWORKS & LIBRARIES:
{', '.join(frameworks) if frameworks else 'Standard libraries'}

DIRECTORY STRUCTURE:
{', '.join(directories[:15]) if directories else 'Simple structure'}

DETECTED FEATURES:
{', '.join(features) if features else 'Core functionality'}

ARCHITECTURAL INSIGHTS:
{', '.join(structure_insights) if structure_insights else 'Standard application structure'}

DEPENDENCIES:
{str(dependencies) if dependencies else 'No dependency information available'}
"""

    parts = [
        "You are a specialized AI assistant for analyzing GitHub repositories and generating project proposals. ",
        "Your task is to analyze the provided code structure and repository information to generate a comprehensive project proposal in JSON format. ",
        "Since no README is available, you must infer the project's purpose, functionality, and value proposition from the code analysis. ",
        "Be creative but realistic in your interpretations based on the technical evidence provided.\n\n",
        
        "Instructions:\n\n",
        "1. Format: Your entire response must be a single, valid JSON object. No extra text, no markdown outside the JSON.\n",
        "2. Structure: The JSON object must have the following keys:\n",
        "   - project_title: (string) An engaging title for the project based on repo name and analysis.\n",
        "   - problem_statement: (string) Infer what problem this project likely solves based on its tech stack and structure (3-5 sentences).\n",
        "   - solution_overview: (string) Describe how the project addresses the problem based on its architecture (4-6 sentences).\n",
        "   - key_features: (string) List main features inferred from code structure and dependencies (6-10 bullet points).\n",
        "   - target_audience: (string) Who would likely use this project based on its technical nature (2-4 sentences).\n",
        "   - technology_stack: (string) Detailed explanation of the detected technologies and their purposes (4-10 elements).\n",
        "   - future_scope: (string) Potential enhancements and features that could be added based on current foundation (8-12 concrete items).\n\n",
        
        "Analysis Guidelines:\n",
        "- Use the project name and technical stack to infer the domain and purpose\n",
        "- Consider the architectural patterns evident in the directory structure\n",
        "- Infer user needs based on the frameworks and libraries used\n",
        "- Suggest realistic future features that align with the current tech stack\n",
        "- Make educated assumptions about the project's goals based on technical evidence\n\n",
        
        "Repository Analysis Data:\n\n```\n",
        analysis_summary,
        "\n```\n\n",
        ("Additional Repository Context:\n\n```\n" + extra_context.strip() + "\n```\n\n" if extra_context and extra_context.strip() else ""),
        "Generated JSON Output:",
    ]
    return "".join(parts)

def build_gemini_prompt(readme_content: str, extra_context: str = None) -> str:
    parts = [
        "You are a specialized AI assistant for a web application. Your task is to analyze the provided GitHub README content and generate a project proposal in a strict JSON format. ",
        "This JSON will be used to populate a web UI. The proposal must be based only on the information in the README. ",
        "If any information is missing for a section, set the value to 'Not available in README.'\n\n",
        "Instructions:\n\n",
        "1. Format: Your entire response must be a single, valid JSON object. No extra text, no markdown outside the JSON.\n",
        "2. Structure: The JSON object must have the following keys:\n",
        "   - title: (string) The project's title.\n",
        "   - introduction: (string) A brief overview (6-10 sentences, ~120-250 words).\n",
        "   - problem_statement: (string) The problem the project solves (6-10 sentences, ~120-250 words).\n",
        "   - solution: (string) The proposed solution (8-14 sentences, ~160-350 words).\n",
        "   - target_audience: (string) Who the project is for (2-4 sentences).\n",
        "   - technology_stack: (string) The tech used with explanations (4-10 elements).\n",
        "   - future_scope: (string) Potential future features (8-12 concrete items).\n\n",
        "README Content to Analyze:\n\n```\n",
        readme_content,
        "\n```\n\n",
        ("Additional Repository Signals:\n\n```\n" + extra_context.strip() + "\n```\n\n" if extra_context and extra_context.strip() else ""),
        "Generated JSON Output:",
    ]
    return "".join(parts)

def call_gemini(readme_content: str, extra_context: str = None) -> dict:
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set. Please configure it in your environment.")

    genai.configure(api_key=GOOGLE_API_KEY)

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={
            "max_output_tokens": 4096,
        },
    )

    prompt = build_gemini_prompt(readme_content, extra_context=extra_context)
    resp = model.generate_content(prompt)

    text = getattr(resp, 'text', None) or (resp.candidates[0].content.parts[0].text if getattr(resp, 'candidates', None) else None)
    if not text:
        raise RuntimeError("Gemini API returned an empty response.")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise
        parsed = json.loads(m.group(0))

    return parsed

@api_bp.route('/fetch-readme', methods=['POST'])
@login_required
def api_fetch_readme():
    data = request.get_json(silent=True) or {}
    repo_url = (data.get("repo_url") or "").strip()

    owner, repo = parse_github_repo(repo_url)
    if not owner:
        return jsonify({"validation_status": False, "error": "Invalid GitHub repository URL."}), 400

    content, source = try_fetch_readme_raw(owner, repo)
    
    # If that fails, try GitHub API with user's token
    if not content:
        user_token = current_user.github_token if current_user.is_authenticated else None
        content, source = try_fetch_readme_api(owner, repo, user_token)

    if not content:
        return jsonify({"validation_status": False, "error": "README not found in repository."}), 404

    return jsonify({
        "validation_status": True,
        "readme_content": content,
        "source": source,
    })

@api_bp.route('/generate', methods=['POST'])
@login_required
def api_generate():
    # Check if user has tokens or is waitlisted with survey completed
    from dashboard import _has_generation_access
    if not _has_generation_access(current_user):
        return jsonify({'error': 'No tokens remaining or access denied'}), 403

    # Handle both form data and JSON data
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Form data with potential file upload
        project_description = request.form.get('project_description', '').strip()
        project_file = request.files.get('project_file')
        generation_type = request.form.get('generation_type', 'investor')
        
        # Get user preferences for slide count and other settings
        try:
            preferences = session.get('user_preferences', {})
            slide_count = int(preferences.get('slide_count', '12'))
            include_financials = preferences.get('include_financials', True)
            include_competition = preferences.get('include_competition', True)
        except:
            # Fallback to defaults if session access fails
            slide_count = 12
            include_financials = True
            include_competition = True
        
        content = ""
        if project_file:
            # Process uploaded file
            try:
                if project_file.filename.endswith(('.txt', '.md')):
                    content = project_file.read().decode('utf-8')
                elif project_file.filename.endswith('.pdf'):
                    # For PDF files, you'd need a PDF parser like PyPDF2
                    return jsonify({"error": "PDF processing not yet implemented"}), 400
                elif project_file.filename.endswith(('.doc', '.docx')):
                    # For Word docs, you'd need python-docx
                    return jsonify({"error": "Word document processing not yet implemented"}), 400
                else:
                    return jsonify({"error": "Unsupported file format"}), 400
            except Exception as e:
                return jsonify({"error": f"Failed to process file: {str(e)}"}), 400
        elif project_description:
            content = project_description
        else:
            return jsonify({"error": "Please provide either a project description or upload a document"}), 400
            
        # Set project details from description
        title = "Custom Project"
        repo_owner = current_user.username
        repo_name = "custom-project"
        repo_url = ""
        
    else:
        # Legacy JSON data for GitHub repos (keep for backward compatibility)
        data = request.get_json(silent=True) or {}
        repo_url = (data.get("repo_url") or "").strip()

        owner, repo = parse_github_repo(repo_url)
        if not owner:
            return jsonify({"error": "Invalid GitHub repository URL."}), 400

        # Try raw.githubusercontent.com first
        content, source = try_fetch_readme_raw(owner, repo)
        
        # If that fails, try GitHub API with user's token
        if not content:
            user_token = current_user.github_token if current_user.is_authenticated else None
            content, _ = try_fetch_readme_api(owner, repo, user_token)

        if not content:
            # No README found - use code analysis instead
            print(f"DEBUG: No README found, analyzing repository structure for {owner}/{repo}")
            user_token = current_user.github_token if current_user.is_authenticated else None
            repo_analysis = analyze_repository_structure(owner, repo, user_token)
            
            if not repo_analysis.get("tech_stack") and repo_analysis.get("main_language") == "Unknown":
                return jsonify({"error": "Unable to analyze repository structure. Repository may be empty or inaccessible."}), 404
            
            # Generate pitch deck from code analysis
            try:
                prompt = build_gemini_prompt_from_code(repo_analysis, repo, extra_context=None)
                print(f"DEBUG: API code analysis prompt length: {len(prompt)} chars")
                resp = model.generate_content(prompt)
                
                text = getattr(resp, 'text', None) or (resp.candidates[0].content.parts[0].text if getattr(resp, 'candidates', None) else None)
                if not text:
                    print(f"DEBUG: Empty AI response for code analysis: {owner}/{repo}")
                    return jsonify({"error": "Failed to generate content from AI service"}), 500
                
                print(f"DEBUG: Code analysis AI response length: {len(text)} chars")
                print(f"DEBUG: Code analysis AI response preview: {text[:200]}...")
                
                # Parse JSON response - strip markdown code blocks if present
                try:
                    # Remove markdown code blocks if present
                    clean_text = text.strip()
                    if clean_text.startswith('```json'):
                        clean_text = clean_text[7:]  # Remove ```json
                    if clean_text.startswith('```'):
                        clean_text = clean_text[3:]   # Remove ```
                    if clean_text.endswith('```'):
                        clean_text = clean_text[:-3]  # Remove trailing ```
                    clean_text = clean_text.strip()
                    
                    parsed = json.loads(clean_text)
                except json.JSONDecodeError as e:
                    print(f"DEBUG: Code analysis JSON parsing failed. Raw response: {text}")
                    print(f"DEBUG: Cleaned text: {clean_text}")
                    return jsonify({"error": f"Invalid response format from AI service: {str(e)}"}), 500
                
                # Map the response to expected format (code analysis uses different keys)
                result = {
                    "title": parsed.get("project_title", repo),
                    "introduction": parsed.get("solution_overview", "Project analysis based on code structure."),
                    "problem_statement": parsed.get("problem_statement", "Problem inferred from code analysis."),
                    "solution_overview": parsed.get("solution_overview", "Solution based on technical implementation."),
                    "key_features": parsed.get("key_features", "Features inferred from codebase."),
                    "target_audience": parsed.get("target_audience", "Target audience based on technical stack."),
                    "technology_stack": parsed.get("technology_stack", "Technology stack detected from code."),
                    "future_scope": parsed.get("future_scope", "Future enhancements based on current foundation.")
                }
                
                return jsonify({
                    "validation_status": True,
                    "analysis_result": result,
                    "source": "code_analysis",
                    "repo_analysis": repo_analysis
                })
                
            except Exception as e:
                return jsonify({"error": f"Error generating pitch deck from code analysis: {str(e)}"}), 500
            
        title = repo
        repo_owner = owner
        repo_name = repo

    try:
        # Configure Gemini AI
        if not GOOGLE_API_KEY:
            return jsonify({"error": "AI service not configured"}), 500
        
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # For custom projects, we don't fetch additional repo signals
        if 'multipart/form-data' in request.content_type:
            extra = {}
        else:
            user_token = current_user.github_token if current_user.is_authenticated else None
            extra = fetch_additional_repo_signals(repo_owner, repo_name, user_token)
        
        # Build dynamic slide structure based on preferences
        slides = [
            "**Slide 1: Title Slide**\n   - Project name and tagline\n   - Team/creator information\n   - Date",
            "**Slide 2: Problem**\n   - What problem does this project solve?\n   - Pain points and market gaps\n   - Why this matters now",
            "**Slide 3: Solution**\n   - How does this project address the problem?\n   - Key features and functionality\n   - Unique value proposition",
            "**Slide 4: Market Opportunity**\n   - Target market size\n   - User personas and segments\n   - Market trends and timing",
            "**Slide 5: Product Demo**\n   - Key features walkthrough\n   - User experience highlights\n   - Technical capabilities",
            "**Slide 6: Technology Stack**\n   - Architecture overview\n   - Key technologies used\n   - Technical advantages",
            "**Slide 7: Traction & Metrics**\n   - Current usage/adoption\n   - Key performance indicators\n   - Growth metrics"
        ]
        
        # Add competition slide if enabled
        if include_competition:
            slides.append("**Slide 8: Competition**\n   - Competitive landscape\n   - Competitive advantages\n   - Differentiation strategy")
        
        # Add business model and financials
        slides.append("**Slide {}: Business Model**\n   - Revenue streams\n   - Monetization strategy\n   - Pricing approach".format(len(slides) + 1))
        
        if include_financials:
            slides.append("**Slide {}: Financials**\n   - Revenue projections\n   - Cost structure\n   - Funding requirements".format(len(slides) + 1))
        
        # Add remaining core slides
        slides.extend([
            "**Slide {}: Team**\n   - Key team members\n   - Relevant experience\n   - Advisory board".format(len(slides) + 1),
            "**Slide {}: Roadmap**\n   - Future features and milestones\n   - Development timeline\n   - Strategic vision".format(len(slides) + 1),
            "**Slide {}: Ask & Next Steps**\n   - What you're seeking (funding, partnerships, users)\n   - Use of funds/resources\n   - Call to action".format(len(slides) + 1)
        ])
        
        # Add additional slides if user wants more than the core set
        core_slides = len(slides)
        if slide_count > core_slides:
            additional_slides = slide_count - core_slides
            for i in range(additional_slides):
                slide_num = core_slides + i + 1
                if i == 0:
                    slides.append(f"**Slide {slide_num}: Market Analysis**\n   - Detailed market research\n   - Customer segments\n   - Market size validation")
                elif i == 1:
                    slides.append(f"**Slide {slide_num}: Product Roadmap**\n   - Feature development timeline\n   - Version releases\n   - Long-term vision")
                elif i == 2:
                    slides.append(f"**Slide {slide_num}: Risk Analysis**\n   - Potential challenges\n   - Mitigation strategies\n   - Contingency plans")
                elif i == 3:
                    slides.append(f"**Slide {slide_num}: Partnership Strategy**\n   - Strategic partnerships\n   - Distribution channels\n   - Ecosystem integration")
                else:
                    slides.append(f"**Slide {slide_num}: Additional Details**\n   - Supporting information\n   - Technical specifications\n   - Implementation details")
        
        # Limit to requested slide count
        slides = slides[:slide_count]
        
        slide_structure = "\n\n".join(slides)
        
        # Extract project details for market research
        project_name = title
        technology_stack = "Unknown"
        target_audience = "General"
        
        # Try to extract tech stack and audience from content
        content_lower = content.lower()
        if any(tech in content_lower for tech in ["javascript", "js", "node", "react", "vue", "angular"]):
            technology_stack = "JavaScript/Web Development"
        elif any(tech in content_lower for tech in ["python", "django", "flask", "fastapi"]):
            technology_stack = "Python"
        elif any(tech in content_lower for tech in ["mobile", "ios", "android", "flutter", "react native"]):
            technology_stack = "Mobile Development"
        elif any(tech in content_lower for tech in ["ai", "ml", "machine learning", "neural", "gpt"]):
            technology_stack = "AI/Machine Learning"
        
        if any(audience in content_lower for audience in ["business", "enterprise", "company"]):
            target_audience = "Businesses"
        elif any(audience in content_lower for audience in ["developer", "programmer", "coder"]):
            target_audience = "Developers"
        elif any(audience in content_lower for audience in ["startup", "entrepreneur"]):
            target_audience = "Startups"
        
        # Generate market intelligence for this project
        from dashboard import generate_market_intelligence
        market_data = generate_market_intelligence(project_name, technology_stack, target_audience, content)
        
        # Build enhanced prompt with market intelligence
        market_context = f"""
Market Intelligence:
- Market Size: {market_data.get('market_size', 'Market analysis pending')}
- Direct Competitors: {market_data.get('competitors_direct', 'Competitive analysis pending')}
- Indirect Competitors: {market_data.get('competitors_indirect', 'Alternative solutions analysis pending')}
- Industry Trends: {market_data.get('industry_trends', 'Trend analysis pending')}
- Target Market Insights: {market_data.get('target_market_insights', 'Audience analysis pending')}
- Growth Projections: {market_data.get('growth_projections', 'Growth analysis pending')}
- Customer Acquisition Cost: {market_data.get('cac_estimate', 'CAC analysis pending')}
- Customer Lifetime Value: {market_data.get('ltv_estimate', 'LTV analysis pending')}
"""

        prompt = f"""Generate a comprehensive pitch deck for the following project using the provided market intelligence:

Project: {title}
{f'Repository: {repo_owner}/{repo_name}' if repo_url else 'Custom Project'}

Project Content:\n{content}\n\n

{market_context}

Please generate a detailed pitch deck with exactly {slide_count} slides as specified below:

{slide_structure}

IMPORTANT: Use the market intelligence data provided above to create realistic, specific content. Do NOT use placeholder text or generic terms like [Company Name] or [X%]. Incorporate the actual market figures, competitor names, and industry insights into your slides.

Make each slide concise, compelling, and investor-ready. Focus on storytelling and visual concepts that would work well in a presentation format.
"""
        
        # Generate pitch deck
        response = model.generate_content(prompt)
        pitch_deck_content = response.text
        
        # Save pitch deck to project
        project = Project(
            title=title,
            repo_url=repo_url,
            repo_owner=repo_owner,
            repo_name=repo_name,
            pitch_deck={
                'content': pitch_deck_content,
                'generated_at': datetime.utcnow().isoformat(),
                'version': '1.0'
            },
            user_id=current_user.id
        )
        
        project.save()
        
        # No token usage for generation - tokens are only for exports
        
        return jsonify({
            'success': True,
            'pitch_deck': project.pitch_deck,
            'project_id': project.id,
            'tokens_remaining': current_user.tokens
        })
    
    except Exception as e:
        return jsonify({"error": f"Pitch deck generation failed: {str(e)}"}), 500

@api_bp.route('/projects/<project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    project = Project.get(project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({'error': 'Project not found'}), 404
    
    return jsonify({
        'id': project.id,
        'title': project.title,
        'repo_url': project.repo_url,
        'repo_owner': project.repo_owner,
        'repo_name': project.repo_name,
        'pitch_deck': project.pitch_deck,
        'user_id': project.user_id,
        'created_at': project.created_at.isoformat() if project.created_at else None,
        'updated_at': project.updated_at.isoformat() if project.updated_at else None
    })

@api_bp.route('/projects/<project_id>/export/docx', methods=['GET'])
@login_required
def export_project_docx(project_id):
    # Check if user has tokens for export
    if not current_user.can_export_files():
        return redirect(url_for('dashboard.out_of_tokens'))
    
    project = Project.get(project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({'error': 'Project not found'}), 404
    
    # Create DOCX document
    doc = Document()
    
    # Title
    title = doc.add_heading(project.title, 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Repository info
    doc.add_paragraph()
    doc.add_paragraph(f"Repository: {project.repo_owner}/{project.repo_name}")
    doc.add_paragraph(f"URL: {project.repo_url}")
    doc.add_paragraph(f"Generated: {project.created_at.strftime('%B %d, %Y')}")
    doc.add_paragraph()
    
    # Pitch deck content
    if project.pitch_deck and project.pitch_deck.get('content'):
        content = project.pitch_deck.get('content', '')
        
        # Split content by slide markers or use as single content
        if '**Slide' in content:
            # Parse structured slide content
            slides = content.split('**Slide')[1:]  # Skip empty first element
            for slide in slides:
                lines = slide.strip().split('\n')
                if lines:
                    # First line is the slide title
                    slide_title = lines[0].replace(':', '').strip()
                    doc.add_heading(f"Slide {slide_title}", level=1)
                    
                    # Rest is content
                    slide_content = '\n'.join(lines[1:]).strip()
                    if slide_content:
                        doc.add_paragraph(slide_content)
                    doc.add_paragraph()
        else:
            # Use content as-is
            doc.add_paragraph(content)
    
    # Save to buffer
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    # Deduct token for export
    current_user.use_token()
    
    filename = f"{project.title.replace(' ', '_')}_pitch_deck.docx"
    return send_file(buffer, as_attachment=True, download_name=filename, 
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

@api_bp.route('/projects/<project_id>/export/pptx', methods=['GET'])
@login_required
def export_project_pptx(project_id):
    # Check if user has tokens for export
    if not current_user.can_export_files():
        return redirect(url_for('dashboard.out_of_tokens'))
    
    project = Project.get(project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({'error': 'Project not found'}), 404
    
    # Get template selection from query parameter
    template = request.args.get('template', '1')  # Default to template 1
    
    # Load template file
    template_path = None
    if template == '1':
        template_path = os.path.join(os.path.dirname(__file__), 'template1.pptx')
    # Template 2 and 3 will be added later
    # elif template == '2':
    #     template_path = os.path.join(os.path.dirname(__file__), 'template2.pptx')
    # elif template == '3':
    #     template_path = os.path.join(os.path.dirname(__file__), 'template3.pptx')
    
    # Create PowerPoint presentation from template or blank
    if template_path and os.path.exists(template_path):
        prs = Presentation(template_path)
        # Use the existing first slide and update its content
        if len(prs.slides) > 0:
            title_slide = prs.slides[0]
            # Update title slide content
            if title_slide.shapes.title:
                title_slide.shapes.title.text = project.title
            # Find subtitle placeholder and update it
            for shape in title_slide.shapes:
                if hasattr(shape, 'text_frame') and shape != title_slide.shapes.title:
                    shape.text_frame.text = f"Investor Pitch Deck"
                    if project.repo_owner and project.repo_name:
                        shape.text_frame.text += f"\n{project.repo_owner}/{project.repo_name}"
                    break
        else:
            # If template has no slides, create a title slide
            title_slide_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(title_slide_layout)
            title = slide.shapes.title
            subtitle = slide.placeholders[1]
            title.text = project.title
            subtitle.text = f"Investor Pitch Deck\n{project.repo_owner}/{project.repo_name}"
    else:
        # Fallback to blank presentation
        prs = Presentation()
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        title.text = project.title
        subtitle.text = f"Investor Pitch Deck\n{project.repo_owner}/{project.repo_name}"
    
    # Process pitch deck content
    if project.pitch_deck and project.pitch_deck.get('content'):
        content = project.pitch_deck.get('content', '')
        
        # Parse content into slides - handle both old and new formats
        slides = []
        if '**Slide' in content:
            # Parse structured slide content (old markdown format)
            slides = content.split('**Slide')[1:]  # Skip empty first element
        elif 'Slide ' in content:
            # Parse structured slide content (new plain text format) - removed ':' requirement
            slides = content.split('Slide ')[1:]  # Skip empty first element
        
        # Debug: Log what we're parsing
        print(f"Content preview: {content[:200]}...")
        print(f"Found {len(slides)} slides")
        if slides:
            print(f"First slide preview: {slides[0][:100]}...")
            
        if slides:
            for i, slide_text in enumerate(slides):
                lines = slide_text.strip().split('\n')
                if lines:
                    # For the first slide, replace the Demo Page (slide index 1) if it exists
                    if i == 0 and len(prs.slides) > 1:
                        # Replace the Demo Page content with Title Slide content
                        slide = prs.slides[1]  # Demo Page is the second slide (index 1)
                        print(f"Replacing Demo Page with Title Slide content")
                    else:
                        # Create new slide with enhanced design for remaining slides
                        slide_layout = prs.slide_layouts[1]  # Title and content layout
                        slide = prs.slides.add_slide(slide_layout)
                    
                    # First line is the slide title - handle both formats
                    slide_title = lines[0].replace(':', '').strip()
                    # Remove any remaining numbers from slide titles (e.g., "1: Title" -> "Title")
                    slide_title = re.sub(r'^\d+\s*:?\s*', '', slide_title)
                    
                    if slide.shapes.title:
                        slide.shapes.title.text = slide_title
                        # Apply consistent enhanced title formatting
                        title_frame = slide.shapes.title.text_frame
                        title_frame.clear()
                        p = title_frame.paragraphs[0]
                        p.alignment = PP_ALIGN.LEFT
                        run = p.add_run()
                        run.text = slide_title
                        run.font.name = 'Segoe UI Semibold'
                        run.font.size = Pt(32)
                        run.font.color.rgb = RGBColor(0x1f, 0x4e, 0x79)  # Professional blue
                        run.font.bold = True
                    
                    # Rest is content
                    slide_content = '\n'.join(lines[1:]).strip()
                    
                    # Find content placeholder - handle both template slides and new slides
                    content_placeholder = None
                    if i == 0 and len(prs.slides) > 1:
                        # For Demo Page replacement, find the content text box
                        for shape in slide.shapes:
                            if hasattr(shape, 'text_frame') and shape != slide.shapes.title:
                                content_placeholder = shape
                                break
                    elif len(slide.placeholders) > 1:
                        content_placeholder = slide.placeholders[1]
                    
                    if slide_content and content_placeholder:
                        text_frame = content_placeholder.text_frame
                        text_frame.clear()
                        
                        # Process content with enhanced formatting
                        process_markdown_to_pptx(slide_content, text_frame)
                        
                        # Add slide background styling
                        add_slide_styling(slide, slide_title)
                        
                        # Ensure proper margins and spacing
                        text_frame.margin_left = PptxInches(0.5)
                        text_frame.margin_right = PptxInches(0.5)
                        text_frame.margin_top = PptxInches(0.3)
                        text_frame.margin_bottom = PptxInches(0.3)
                        
                        if i == 0:
                            print(f"Replaced Demo Page with: {slide_title}")
                        else:
                            print(f"Created slide: {slide_title}")
        else:
            # Split content by common slide indicators or paragraphs
            content_sections = []
            
            # Try to split by common pitch deck sections
            section_markers = [
                'Problem', 'Solution', 'Market', 'Product', 'Business Model',
                'Competition', 'Team', 'Financials', 'Funding', 'Contact'
            ]
            
            current_section = ""
            current_content = ""
            
            for line in content.split('\n'):
                line = line.strip()
                if any(marker.lower() in line.lower() for marker in section_markers):
                    if current_section and current_content:
                        content_sections.append((current_section, current_content.strip()))
                    current_section = line
                    current_content = ""
                else:
                    current_content += line + "\n"
            
            # Add the last section
            if current_section and current_content:
                content_sections.append((current_section, current_content.strip()))
            
            # If no sections found, create slides from paragraphs
            if not content_sections:
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                for i, paragraph in enumerate(paragraphs[:10]):  # Limit to 10 slides
                    slide_layout = prs.slide_layouts[1]
                    slide = prs.slides.add_slide(slide_layout)
                    slide_title = f"Content Slide {i + 1}"
                    
                    if slide.shapes.title:
                        slide.shapes.title.text = slide_title
                        # Apply consistent enhanced title formatting
                        title_frame = slide.shapes.title.text_frame
                        title_frame.clear()
                        p = title_frame.paragraphs[0]
                        p.alignment = PP_ALIGN.LEFT
                        run = p.add_run()
                        run.text = slide_title
                        run.font.name = 'Segoe UI Semibold'
                        run.font.size = Pt(32)
                        run.font.color.rgb = RGBColor(0x1f, 0x4e, 0x79)
                        run.font.bold = True
                        
                    if len(slide.placeholders) > 1:
                        content_placeholder = slide.placeholders[1]
                        text_frame = content_placeholder.text_frame
                        text_frame.clear()
                        
                        # Process content with enhanced formatting
                        process_markdown_to_pptx(paragraph, text_frame)
                        
                        # Add slide styling and margins
                        add_slide_styling(slide, slide_title)
                        text_frame.margin_left = PptxInches(0.5)
                        text_frame.margin_right = PptxInches(0.5)
                        text_frame.margin_top = PptxInches(0.3)
                        text_frame.margin_bottom = PptxInches(0.3)
            else:
                # Create slides from sections
                for section_title, section_content in content_sections:
                    slide_layout = prs.slide_layouts[1]
                    slide = prs.slides.add_slide(slide_layout)
                    
                    if slide.shapes.title:
                        slide.shapes.title.text = section_title
                        # Apply consistent enhanced title formatting
                        title_frame = slide.shapes.title.text_frame
                        title_frame.clear()
                        p = title_frame.paragraphs[0]
                        p.alignment = PP_ALIGN.LEFT
                        run = p.add_run()
                        run.text = section_title
                        run.font.name = 'Segoe UI Semibold'
                        run.font.size = Pt(32)
                        run.font.color.rgb = RGBColor(0x1f, 0x4e, 0x79)
                        run.font.bold = True
                        
                    if len(slide.placeholders) > 1:
                        content_placeholder = slide.placeholders[1]
                        text_frame = content_placeholder.text_frame
                        text_frame.clear()
                        
                        # Process content with enhanced formatting
                        process_markdown_to_pptx(section_content, text_frame)
                        
                        # Add slide styling and margins
                        add_slide_styling(slide, section_title)
                        text_frame.margin_left = PptxInches(0.5)
                        text_frame.margin_right = PptxInches(0.5)
                        text_frame.margin_top = PptxInches(0.3)
                        text_frame.margin_bottom = PptxInches(0.3)
                        
                        print(f"Created section slide: {section_title}")
    
    # Save to buffer
    buffer = BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    
    # Deduct token for export
    current_user.use_token()
    
    filename = f"{project.title.replace(' ', '_')}_pitch_deck.pptx"
    return send_file(buffer, as_attachment=True, download_name=filename, 
                    mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation')

@api_bp.route('/generate-documentation/<project_id>')
@login_required
def generate_documentation(project_id):
    """Generate technical documentation for a project"""
    # Check if user has generation access
    from dashboard import _has_generation_access
    if not _has_generation_access(current_user):
        return jsonify({'error': 'No tokens remaining or access denied'}), 403
    
    project = Project.get(project_id)
    
    if not project or project.user_id != current_user.id:
        return jsonify({'error': 'Project not found or access denied'}), 404
    
    try:
        # Configure Gemini AI
        if not GOOGLE_API_KEY:
            return jsonify({'error': 'AI service not configured'}), 500
        
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Get repository content for context
        repo_content = ""
        if project.repo_owner and project.repo_name:
            readme_content, _ = try_fetch_readme_raw(project.repo_owner, project.repo_name)
            if not readme_content:
                user_token = current_user.github_token if current_user.is_authenticated else None
                readme_content, _ = try_fetch_readme_api(project.repo_owner, project.repo_name, user_token)
            if readme_content:
                repo_content = f"README Content:\n{readme_content}\n\n"
        
        # Create documentation generation prompt
        prompt = f"""Generate comprehensive technical documentation for the following project:

Project: {project.title}
Repository: {project.repo_owner}/{project.repo_name if project.repo_name else 'N/A'}

{repo_content}

Please generate detailed technical documentation that includes:

1. **Architecture Overview**
   - System architecture and design patterns
   - Technology stack and dependencies
   - Database schema (if applicable)

2. **API Documentation**
   - Endpoints and their purposes
   - Request/response formats
   - Authentication requirements

3. **Installation & Setup**
   - Prerequisites and requirements
   - Step-by-step installation guide
   - Configuration instructions

4. **Development Guide**
   - Project structure explanation
   - Coding standards and conventions
   - Testing procedures

5. **Deployment**
   - Deployment requirements
   - Environment configuration
   - Production considerations

6. **Troubleshooting**
   - Common issues and solutions
   - Debug procedures
   - Performance optimization

Format the response as structured markdown with clear headings and code examples where appropriate.
"""
        
        # Generate documentation
        response = model.generate_content(prompt)
        documentation_content = response.text
        
        # Save documentation to project
        project.documentation = {
            'content': documentation_content,
            'generated_at': datetime.utcnow().isoformat(),
            'version': '1.0'
        }
        
        # No token usage for generation - tokens are only for exports
        project.save()
        
        return jsonify({
            'success': True,
            'documentation': project.documentation,
            'tokens_remaining': current_user.tokens
        })
        
    except Exception as e:
        return jsonify({'error': f'Documentation generation failed: {str(e)}'}), 500

@api_bp.route('/generate-user-guide/<project_id>')
@login_required
def generate_user_guide(project_id):
    """Generate user guide for a project"""
    # Check if user has generation access
    from dashboard import _has_generation_access
    if not _has_generation_access(current_user):
        return jsonify({'error': 'No tokens remaining or access denied'}), 403
    
    project = Project.get(project_id)
    
    if not project or project.user_id != current_user.id:
        return jsonify({'error': 'Project not found or access denied'}), 404
    
    try:
        # Configure Gemini AI
        if not GOOGLE_API_KEY:
            return jsonify({'error': 'AI service not configured'}), 500
        
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Get repository content for context
        repo_content = ""
        if project.repo_owner and project.repo_name:
            readme_content, _ = try_fetch_readme_raw(project.repo_owner, project.repo_name)
            if not readme_content:
                user_token = current_user.github_token if current_user.is_authenticated else None
                readme_content, _ = try_fetch_readme_api(project.repo_owner, project.repo_name, user_token)
            if readme_content:
                repo_content = f"README Content:\n{readme_content}\n\n"
        
        # Create user guide generation prompt
        prompt = f"""Generate a comprehensive user guide for the following project:

Project: {project.title}
Repository: {project.repo_owner}/{project.repo_name if project.repo_name else 'N/A'}

{repo_content}

Please generate a user-friendly guide that includes:

1. **Getting Started**
   - What this application does
   - Who should use it
   - System requirements

2. **Installation Guide**
   - Simple installation steps
   - Initial setup and configuration
   - First-time user setup

3. **User Interface Guide**
   - Navigation overview
   - Main features and functions
   - Screenshots or descriptions of key screens

4. **Step-by-Step Tutorials**
   - Common use cases with detailed steps
   - Example workflows
   - Tips and best practices

5. **Features Reference**
   - Complete feature list with descriptions
   - Settings and customization options
   - Advanced features

6. **Troubleshooting & FAQ**
   - Common user issues and solutions
   - Frequently asked questions
   - Where to get help

7. **Tips & Best Practices**
   - How to get the most out of the application
   - Performance tips
   - Security considerations for users

Write in a friendly, accessible tone suitable for end users. Use clear headings, bullet points, and step-by-step instructions.
"""
        
        # Generate user guide
        response = model.generate_content(prompt)
        user_guide_content = response.text
        
        # Save user guide to project
        project.user_guide = {
            'content': user_guide_content,
            'generated_at': datetime.utcnow().isoformat(),
            'version': '1.0'
        }
        
        # No token usage for generation - tokens are only for exports
        project.save()
        
        return jsonify({
            'success': True,
            'user_guide': project.user_guide,
            'tokens_remaining': current_user.tokens
        })
        
    except Exception as e:
        return jsonify({'error': f'User guide generation failed: {str(e)}'}), 500


@api_bp.route('/projects/<project_id>/export/pdf', methods=['GET'])
@login_required
def export_project_pdf(project_id):
    # Check if user has tokens for export
    if not current_user.can_export_files():
        return redirect(url_for('dashboard.out_of_tokens'))
    
    # PDF export temporarily disabled due to reportlab build issues on Vercel
    return jsonify({
        'error': 'PDF export temporarily unavailable',
        'message': 'Please use DOCX export or copy the content manually'
    }), 503

@api_bp.route('/upgrade-account', methods=['POST'])
@login_required
def upgrade_account():
    """Upgrade user account tier"""
    data = request.get_json()
    new_tier = data.get('tier')
    
    if new_tier not in ['basic', 'pro']:
        return jsonify({'success': False, 'error': 'Invalid tier'}), 400
    
    # In a real app, you'd integrate with a payment processor here
    # For demo purposes, we'll just upgrade the account
    if current_user.upgrade_account(new_tier):
        return jsonify({
            'success': True, 
            'tier': current_user.account_tier,
            'tokens': current_user.tokens
        })
    else:
        return jsonify({'success': False, 'error': 'Upgrade failed'}), 500

@api_bp.route('/admin/change-user-plan', methods=['POST'])
@login_required
def admin_change_user_plan():
    """Admin endpoint to change user account plans"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    new_tier = data.get('tier')
    
    if not user_id or new_tier not in ['free', 'basic', 'pro']:
        return jsonify({'success': False, 'error': 'Invalid parameters'}), 400
    
    # Get the user to modify
    from firebase_models import User
    user = User.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Change the user's plan
    if user.upgrade_account(new_tier):
        return jsonify({
            'success': True,
            'user_id': user_id,
            'tier': user.account_tier,
            'tokens': user.tokens
        })
    else:
        return jsonify({'success': False, 'error': 'Plan change failed'}), 500


@api_bp.route('/admin/toggle-admin-status', methods=['POST'])
@login_required
def toggle_admin_status():
    """Toggle admin status for a user (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    is_admin = data.get('is_admin')
    
    if not user_id or is_admin is None:
        return jsonify({'success': False, 'error': 'Invalid parameters'}), 400
    
    # Get the user to modify
    from firebase_models import User
    user = User.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Don't allow removing admin from self
    if user.id == current_user.id and not is_admin:
        return jsonify({'success': False, 'error': 'Cannot remove admin privileges from yourself'}), 400
    
    # Update admin status
    user.is_admin = is_admin
    if user.save():
        return jsonify({
            'success': True,
            'user_id': user_id,
            'is_admin': user.is_admin
        })
    else:
        return jsonify({'success': False, 'error': 'Admin status change failed'}), 500


@api_bp.route('/admin/whitelist-user', methods=['POST'])
@login_required
def whitelist_user():
    """Toggle whitelist status for a deleted user (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    is_whitelisted = data.get('is_whitelisted')
    
    if not user_id or is_whitelisted is None:
        return jsonify({'success': False, 'error': 'Invalid parameters'}), 400
    
    # Get the user to modify
    user = User.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Only allow whitelisting deleted users
    if not user.is_deleted:
        return jsonify({'success': False, 'error': 'Can only whitelist deleted users'}), 400
    
    # Update whitelist status
    user.is_whitelisted = is_whitelisted
    if user.save():
        return jsonify({
            'success': True,
            'user_id': user_id,
            'is_whitelisted': user.is_whitelisted
        })
    else:
        return jsonify({'success': False, 'error': 'Whitelist status change failed'}), 500


@api_bp.route('/admin/delete-user', methods=['DELETE'])
@login_required
def delete_user():
    """Delete a user account and all associated data (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID required'}), 400
    
    # Don't allow deleting self
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
    
    # Get the user to delete
    from firebase_models import User, Project
    user = User.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    try:
        # Delete all user's projects first
        projects = Project.get_by_user(user_id)
        for project in projects:
            project.delete()
        
        # Delete the user account
        if user.delete():
            return jsonify({
                'success': True,
                'message': f'User account and all associated data deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'User deletion failed'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Deletion failed: {str(e)}'}), 500


@api_bp.route('/admin/permanently-delete-user', methods=['DELETE'])
@login_required
def permanently_delete_user():
    """Permanently delete a user account and all associated data from database (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID required'}), 400
    
    # Don't allow deleting self
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
    
    # Get the user to delete
    from firebase_models import User, Project, SurveyResponse
    user = User.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Only allow permanent deletion of already soft-deleted users
    if not getattr(user, 'is_deleted', False):
        return jsonify({'success': False, 'error': 'User must be soft-deleted first'}), 400
    
    try:
        # Delete all user's projects first
        projects = Project.get_by_user(user_id)
        for project in projects:
            project.delete()
        
        # Delete all user's survey responses
        survey_responses = SurveyResponse.get_by_user(user_id)
        for response in survey_responses:
            response.delete()
        
        # Permanently delete the user account from Firestore
        from firebase_config import get_db
        db = get_db()
        if db:
            db.collection('users').document(user_id).delete()
            return jsonify({
                'success': True,
                'message': f'User account permanently deleted from database'
            })
        else:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Permanent deletion failed: {str(e)}'}), 500


@api_bp.route('/admin/permanently-delete-all-users', methods=['DELETE'])
@login_required
def permanently_delete_all_users():
    """Permanently delete all soft-deleted users from database (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        from firebase_models import User, Project, SurveyResponse
        from firebase_config import get_db
        
        # Get all deleted users
        deleted_users = User.get_deleted_users()
        
        if not deleted_users:
            return jsonify({'success': True, 'message': 'No deleted users to purge'})
        
        db = get_db()
        if not db:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        deleted_count = 0
        
        for user in deleted_users:
            # Don't allow deleting self
            if user.id == current_user.id:
                continue
                
            # Delete all user's projects
            projects = Project.get_by_user(user.id)
            for project in projects:
                project.delete()
            
            # Delete all user's survey responses
            survey_responses = SurveyResponse.get_by_user(user.id)
            for response in survey_responses:
                response.delete()
            
            # Permanently delete the user account from Firestore
            db.collection('users').document(user.id).delete()
            deleted_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Successfully permanently deleted {deleted_count} user accounts from database'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Bulk permanent deletion failed: {str(e)}'}), 500


@api_bp.route('/export/<project_id>/<format>')
@login_required
def export_project(project_id, format):
    """Export project pitch deck in various formats"""
    if format == 'docx':
        return export_project_docx(project_id)
    elif format == 'pptx':
        return export_project_pptx(project_id)
    elif format == 'pdf':
        return export_project_pdf(project_id)
    else:
        return jsonify({'error': 'Unsupported format'}), 400

@api_bp.route('/generate-documentation/<project_id>/export', methods=['GET'])
@login_required
def export_documentation_docx(project_id):
    # Check if user has tokens for export
    if not current_user.can_export_files():
        return redirect(url_for('dashboard.out_of_tokens'))
    
    project = Project.get(project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({'error': 'Project not found'}), 404
    
    # Create DOCX document
    doc = Document()
    
    # Title
    title = doc.add_heading(f"{project.title} - Technical Documentation", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Repository info
    doc.add_paragraph()
    doc.add_paragraph(f"Repository: {project.repo_owner}/{project.repo_name}")
    doc.add_paragraph(f"URL: {project.repo_url}")
    doc.add_paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}")
    doc.add_paragraph()
    
    # Documentation sections
    if project.documentation:
        documentation = project.documentation
        
        sections = [
            ("Architecture Overview", documentation.get("architecture_overview")),
            ("API Documentation", documentation.get("api_documentation")),
            ("Database Schema", documentation.get("database_schema")),
            ("Deployment Guide", documentation.get("deployment_guide")),
            ("Configuration", documentation.get("configuration")),
            ("Testing", documentation.get("testing"))
        ]
        
        for section_title, content in sections:
            if content and content != "Not available in README.":
                doc.add_heading(section_title, level=1)
                doc.add_paragraph(content)
                doc.add_paragraph()
    else:
        doc.add_paragraph("Documentation not yet generated for this project.")
    
    # Save to buffer
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    # Deduct token for export
    current_user.use_token()
    
    filename = f"{project.title.replace(' ', '_')}_documentation.docx"
    return send_file(buffer, as_attachment=True, download_name=filename, 
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

@api_bp.route('/generate-user-guide/<project_id>/export', methods=['GET'])
@login_required
def export_user_guide_docx(project_id):
    # Check if user has tokens for export
    if not current_user.can_export_files():
        return redirect(url_for('dashboard.out_of_tokens'))
    
    project = Project.get(project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({'error': 'Project not found'}), 404
    
    # Create DOCX document
    doc = Document()
    
    # Title
    title = doc.add_heading(f"{project.title} - User Guide", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Repository info
    doc.add_paragraph()
    doc.add_paragraph(f"Repository: {project.repo_owner}/{project.repo_name}")
    doc.add_paragraph(f"URL: {project.repo_url}")
    doc.add_paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}")
    doc.add_paragraph()
    
    # User guide sections
    if project.user_guide:
        user_guide = project.user_guide
        
        # Check if user guide has content field (new format) or individual sections (old format)
        if 'content' in user_guide:
            # New format - single content field
            content = user_guide.get('content', '')
            if content and content.strip():
                # Split content by markdown headers and add to document
                lines = content.split('\n')
                current_section = ""
                current_content = []
                
                for line in lines:
                    if line.startswith('**') and line.endswith('**'):
                        # Save previous section
                        if current_section and current_content:
                            doc.add_heading(current_section, level=1)
                            doc.add_paragraph('\n'.join(current_content))
                            doc.add_paragraph()
                        
                        # Start new section
                        current_section = line.strip('*').strip()
                        current_content = []
                    elif line.startswith('#'):
                        # Save previous section
                        if current_section and current_content:
                            doc.add_heading(current_section, level=1)
                            doc.add_paragraph('\n'.join(current_content))
                            doc.add_paragraph()
                        
                        # Start new section
                        current_section = line.lstrip('#').strip()
                        current_content = []
                    else:
                        if line.strip():
                            current_content.append(line)
                
                # Add final section
                if current_section and current_content:
                    doc.add_heading(current_section, level=1)
                    doc.add_paragraph('\n'.join(current_content))
                    doc.add_paragraph()
                
                # If no sections were found, add all content as one block
                if not current_section:
                    doc.add_heading("User Guide", level=1)
                    doc.add_paragraph(content)
                    doc.add_paragraph()
            else:
                doc.add_paragraph("User guide content is empty.")
        else:
            # Old format - individual sections
            sections = [
                ("Getting Started", user_guide.get("getting_started")),
                ("Installation", user_guide.get("installation")),
                ("Basic Usage", user_guide.get("basic_usage")),
                ("Advanced Features", user_guide.get("advanced_features")),
                ("Troubleshooting", user_guide.get("troubleshooting")),
                ("FAQ", user_guide.get("faq"))
            ]
            
            for section_title, content in sections:
                if content and content != "Not available in README.":
                    doc.add_heading(section_title, level=1)
                    doc.add_paragraph(content)
                    doc.add_paragraph()
    else:
        doc.add_paragraph("User guide not yet generated for this project.")
    
    # Save to buffer
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    # Deduct token for export
    current_user.use_token()
    
    filename = f"{project.title.replace(' ', '_')}_user_guide.docx"
    return send_file(buffer, as_attachment=True, download_name=filename, 
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')


@api_bp.route('/validate-coupon', methods=['POST'])
@login_required
def validate_coupon():
    """Validate coupon code and return discount information"""
    try:
        from firebase_models import Coupon
        from datetime import datetime
        
        data = request.get_json()
        coupon_code = data.get('code', '').upper().strip()
        plan_type = data.get('plan', 'basic')  # basic or pro
        
        if not coupon_code:
            return jsonify({'valid': False, 'error': 'Coupon code is required'}), 400
        
        # Get coupon by code
        coupon = Coupon.get_by_code(coupon_code)
        
        if not coupon:
            return jsonify({'valid': False, 'error': 'Invalid coupon code'}), 404
        
        # Check if coupon is valid
        if not coupon.is_valid():
            if not coupon.is_active:
                return jsonify({'valid': False, 'error': 'This coupon is no longer active'}), 400
            elif coupon.expires_at and datetime.utcnow() > coupon.expires_at:
                return jsonify({'valid': False, 'error': 'This coupon has expired'}), 400
            elif coupon.max_uses and coupon.current_uses >= coupon.max_uses:
                return jsonify({'valid': False, 'error': 'This coupon has reached its usage limit'}), 400
            else:
                return jsonify({'valid': False, 'error': 'This coupon is not valid'}), 400
        
        # Check if coupon applies to the selected plan
        if coupon.applies_to != 'all' and coupon.applies_to != plan_type:
            return jsonify({
                'valid': False, 
                'error': f'This coupon only applies to {coupon.applies_to} plans'
            }), 400
        
        # Calculate discount
        plan_prices = {'basic': 9.99, 'pro': 19.99}
        original_price = plan_prices.get(plan_type, 9.99)
        
        if coupon.discount_type == 'percentage':
            discount_amount = original_price * (coupon.discount_value / 100)
        else:
            discount_amount = min(coupon.discount_value, original_price)  # Don't exceed original price
        
        final_price = max(0, original_price - discount_amount)
        
        return jsonify({
            'valid': True,
            'coupon': {
                'code': coupon.code,
                'discount_type': coupon.discount_type,
                'discount_value': coupon.discount_value,
                'applies_to': coupon.applies_to
            },
            'pricing': {
                'original_price': original_price,
                'discount_amount': round(discount_amount, 2),
                'final_price': round(final_price, 2),
                'savings_percentage': round((discount_amount / original_price) * 100, 1)
            }
        })
    
    except Exception as e:
        return jsonify({'valid': False, 'error': f'Failed to validate coupon: {str(e)}'}), 500


@api_bp.route('/apply-coupon', methods=['POST'])
@login_required
def apply_coupon():
    """Apply coupon to user account for checkout"""
    try:
        from firebase_models import Coupon
        
        data = request.get_json()
        coupon_code = data.get('code', '').upper().strip()
        
        if not coupon_code:
            return jsonify({'success': False, 'error': 'Coupon code is required'}), 400
        
        # Validate coupon first
        coupon = Coupon.get_by_code(coupon_code)
        if not coupon or not coupon.is_valid():
            return jsonify({'success': False, 'error': 'Invalid or expired coupon'}), 400
        
        # Store coupon code in user's account for checkout
        current_user.coupon_code = coupon_code
        current_user.save()
        
        return jsonify({
            'success': True,
            'message': f'Coupon {coupon_code} applied successfully!',
            'coupon_code': coupon_code
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to apply coupon: {str(e)}'}), 500
