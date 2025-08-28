import os
import re
import json
from urllib.parse import urlparse
from datetime import datetime
from io import BytesIO

import requests
from flask import Blueprint, jsonify, request, send_file
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

from firebase_models import Project

api_bp = Blueprint('api', __name__)

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

def try_fetch_readme_api(owner: str, repo: str):
    """Fallback to GitHub API to get the default README if possible."""
    api = f"https://api.github.com/repos/{owner}/{repo}/readme"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "synoptic-saas",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
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

def fetch_additional_repo_signals(owner: str, repo: str) -> str:
    """Collect extra signals to help infer problem_statement and future_scope when README is sparse."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "synoptic-saas",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

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
    if not content:
        content, source = try_fetch_readme_api(owner, repo)

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

    data = request.get_json(silent=True) or {}
    repo_url = (data.get("repo_url") or "").strip()

    owner, repo = parse_github_repo(repo_url)
    if not owner:
        return jsonify({"error": "Invalid GitHub repository URL."}), 400

    content, _ = try_fetch_readme_raw(owner, repo)
    if not content:
        content, _ = try_fetch_readme_api(owner, repo)

    if not content:
        return jsonify({"error": "README not found in repository."}), 404

    try:
        extra = fetch_additional_repo_signals(owner, repo)
        title = repo
        repo_owner = owner
        repo_name = repo
        prompt = f"""Generate a comprehensive pitch deck for the following GitHub repository:

Project: {title}
Repository: {repo_owner}/{repo_name}

README Content:\n{content}\n\n

Please generate a detailed pitch deck with the following slides:

**Slide 1: Title Slide**
   - Project name and tagline
   - Team/creator information
   - Date

**Slide 2: Problem**
   - What problem does this project solve?
   - Pain points and market gaps
   - Why this matters now

**Slide 3: Solution**
   - How does this project address the problem?
   - Key features and functionality
   - Unique value proposition

**Slide 4: Market Opportunity**
   - Target market size
   - User personas and segments
   - Market trends and timing

**Slide 5: Product Demo**
   - Key features walkthrough
   - User experience highlights
   - Technical capabilities

**Slide 6: Technology Stack**
   - Architecture overview
   - Key technologies used
   - Technical advantages

**Slide 7: Traction & Metrics**
   - Current usage/adoption
   - Key performance indicators
   - Growth metrics

**Slide 8: Competition**
   - Competitive landscape
   - Competitive advantages
   - Differentiation strategy

**Slide 9: Business Model**
   - Revenue streams
   - Monetization strategy
   - Pricing approach

**Slide 10: Roadmap**
   - Future features and milestones
   - Development timeline
   - Strategic vision

**Slide 11: Team**
   - Key team members
   - Relevant experience
   - Advisory board

**Slide 12: Ask & Next Steps**
   - What you're seeking (funding, partnerships, users)
   - Use of funds/resources
   - Call to action

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
                readme_content, _ = try_fetch_readme_api(project.repo_owner, project.repo_name)
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
                readme_content, _ = try_fetch_readme_api(project.repo_owner, project.repo_name)
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

@api_bp.route('/export/<project_id>/<format>')
@login_required
def export_project(project_id, format):
    """Export project proposal in various formats"""
    if format == 'docx':
        return export_project_docx(project_id)
    elif format == 'pdf':
        return export_project_pdf(project_id)
    else:
        return jsonify({'error': 'Unsupported format'}), 400
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
    """Export project proposal in various formats"""
    if format == 'docx':
        return export_project_docx(project_id)
    elif format == 'pdf':
        return export_project_pdf(project_id)
    else:
        return jsonify({'error': 'Unsupported format'}), 400

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
    
    # Proposal sections
    if project.proposal_data:
        proposal = project.proposal_data
        
        sections = [
            ("Project Overview", proposal.get("project_overview") or proposal.get("introduction")),
            ("Problem Statement", proposal.get("problem_statement")),
            ("Solution", proposal.get("solution")),
            ("Target Audience", proposal.get("target_audience")),
            ("Technology Stack", proposal.get("technology_stack")),
            ("Future Scope", proposal.get("future_scope"))
        ]
        
        for section_title, content in sections:
            if content and content != "Not available in README.":
                doc.add_heading(section_title, level=1)
                doc.add_paragraph(content)
                doc.add_paragraph()
        
        # Key Features
        if proposal.get("key_features"):
            doc.add_heading("Key Features", level=1)
            for feature in proposal["key_features"]:
                p = doc.add_paragraph()
                p.add_run(f"• {feature}")
            doc.add_paragraph()
        
        # Success Metrics
        if proposal.get("success_metrics"):
            doc.add_heading("Success Metrics", level=1)
            for metric in proposal["success_metrics"]:
                p = doc.add_paragraph()
                p.add_run(f"• {metric}")
            doc.add_paragraph()
    
    # Save to buffer
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    filename = f"{project.title.replace(' ', '_')}_proposal.docx"
    return send_file(buffer, as_attachment=True, download_name=filename, 
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

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
