import os
import re
import json
from urllib.parse import urlparse
from datetime import datetime
from io import BytesIO

import requests
from flask import Blueprint, jsonify, request, send_file, session
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

from firebase_models import Project

api_bp = Blueprint('api', __name__)

def process_markdown_to_pptx(text, text_frame):
    """Process markdown text and add it to PowerPoint text frame with proper formatting"""
    import re
    
    # Split text into lines
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        if i > 0:  # Add new paragraph for each line except the first
            p = text_frame.add_paragraph()
        else:
            p = text_frame.paragraphs[0] if text_frame.paragraphs else text_frame.add_paragraph()
        
        # Process bold text (**text**)
        parts = re.split(r'\*\*(.*?)\*\*', line)
        
        for j, part in enumerate(parts):
            if not part:  # Skip empty parts
                continue
                
            run = p.add_run()
            run.text = part
            
            # Make every second part bold (the content between **)
            if j % 2 == 1:
                run.font.bold = True
            
            # Set font size
            run.font.size = Pt(22)

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
    # Check if user has tokens available
    if not current_user.can_generate_pitch_deck():
        return jsonify({"error": "No tokens available for pitch deck generation"}), 400

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
            return jsonify({"error": "README not found in repository."}), 404
            
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
        
        prompt = f"""Generate a comprehensive pitch deck for the following project:

Project: {title}
{f'Repository: {repo_owner}/{repo_name}' if repo_url else 'Custom Project'}

Project Content:\n{content}\n\n

Please generate a detailed pitch deck with exactly {slide_count} slides as specified below:

{slide_structure}

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
        
        # Deduct token after successful pitch deck generation
        current_user.use_token()
        
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
    
    filename = f"{project.title.replace(' ', '_')}_pitch_deck.docx"
    return send_file(buffer, as_attachment=True, download_name=filename, 
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

@api_bp.route('/projects/<project_id>/export/pptx', methods=['GET'])
@login_required
def export_project_pptx(project_id):
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
        
        # Parse content into slides
        if '**Slide' in content:
            # Parse structured slide content
            slides = content.split('**Slide')[1:]  # Skip empty first element
            for slide_text in slides:
                lines = slide_text.strip().split('\n')
                if lines:
                    # Create new slide
                    slide_layout = prs.slide_layouts[1]  # Title and content layout
                    slide = prs.slides.add_slide(slide_layout)
                    
                    # First line is the slide title
                    slide_title = lines[0].replace(':', '').strip()
                    if slide.shapes.title:
                        slide.shapes.title.text = slide_title
                        # Set title font size for template 1 only (28pt)
                        if template == '1':
                            for paragraph in slide.shapes.title.text_frame.paragraphs:
                                for run in paragraph.runs:
                                    run.font.size = Pt(28)
                    
                    # Rest is content
                    slide_content = '\n'.join(lines[1:]).strip()
                    if slide_content and len(slide.placeholders) > 1:
                        content_placeholder = slide.placeholders[1]
                        text_frame = content_placeholder.text_frame
                        text_frame.clear()
                        
                        # Process content with bold formatting
                        formatted_content = process_markdown_to_pptx(slide_content, text_frame)
                        
                        # Set font size for all paragraphs - 16pt for template 1, 22pt for others
                        font_size = Pt(16) if template == '1' else Pt(22)
                        for paragraph in text_frame.paragraphs:
                            for run in paragraph.runs:
                                run.font.size = font_size
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
                    if slide.shapes.title:
                        slide.shapes.title.text = f"Slide {i + 1}"
                        # Set title font size for template 1 only (28pt)
                        if template == '1':
                            for paragraph in slide.shapes.title.text_frame.paragraphs:
                                for run in paragraph.runs:
                                    run.font.size = Pt(28)
                    if len(slide.placeholders) > 1:
                        content_placeholder = slide.placeholders[1]
                        text_frame = content_placeholder.text_frame
                        text_frame.clear()
                        
                        # Process content with bold formatting
                        process_markdown_to_pptx(paragraph, text_frame)
                        
                        # Set font size for all paragraphs - 16pt for template 1, 22pt for others
                        font_size = Pt(16) if template == '1' else Pt(22)
                        for p in text_frame.paragraphs:
                            for run in p.runs:
                                run.font.size = font_size
            else:
                # Create slides from sections
                for section_title, section_content in content_sections:
                    slide_layout = prs.slide_layouts[1]
                    slide = prs.slides.add_slide(slide_layout)
                    if slide.shapes.title:
                        slide.shapes.title.text = section_title
                        # Set title font size for template 1 only (28pt)
                        if template == '1':
                            for paragraph in slide.shapes.title.text_frame.paragraphs:
                                for run in paragraph.runs:
                                    run.font.size = Pt(28)
                    if len(slide.placeholders) > 1:
                        content_placeholder = slide.placeholders[1]
                        text_frame = content_placeholder.text_frame
                        text_frame.clear()
                        
                        # Process content with bold formatting
                        process_markdown_to_pptx(section_content, text_frame)
                        
                        # Set font size for all paragraphs - 16pt for template 1, 22pt for others
                        font_size = Pt(16) if template == '1' else Pt(22)
                        for p in text_frame.paragraphs:
                            for run in p.runs:
                                run.font.size = font_size
    
    # Save to buffer
    buffer = BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    
    filename = f"{project.title.replace(' ', '_')}_pitch_deck.pptx"
    return send_file(buffer, as_attachment=True, download_name=filename, 
                    mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation')

@api_bp.route('/generate-documentation/<project_id>')
@login_required
def generate_documentation(project_id):
    """Generate technical documentation for a project"""
    project = Project.get(project_id)
    
    if not project or project.user_id != current_user.id:
        return jsonify({'error': 'Project not found or access denied'}), 404
    
    if not current_user.can_generate_proposal():
        return jsonify({'error': 'No tokens available for documentation generation'}), 400
    
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
        
        # Use a token for documentation generation
        current_user.use_token()
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
    project = Project.get(project_id)
    
    if not project or project.user_id != current_user.id:
        return jsonify({'error': 'Project not found or access denied'}), 404
    
    if not current_user.can_generate_proposal():
        return jsonify({'error': 'No tokens available for user guide generation'}), 400
    
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
        
        # Use a token for user guide generation
        current_user.use_token()
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
    
    filename = f"{project.title.replace(' ', '_')}_documentation.docx"
    return send_file(buffer, as_attachment=True, download_name=filename, 
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

@api_bp.route('/generate-user-guide/<project_id>/export', methods=['GET'])
@login_required
def export_user_guide_docx(project_id):
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
    
    filename = f"{project.title.replace(' ', '_')}_user_guide.docx"
    return send_file(buffer, as_attachment=True, download_name=filename, 
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
