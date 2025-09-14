from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from firebase_models import Project, User, Survey, SurveyResponse, Coupon
from datetime import datetime
from functools import wraps
import requests
import json

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

def generate_realistic_market_data(project_name, technology_stack, target_audience, project_description=""):
    """Generate realistic market data using deterministic knowledge base"""
    
    # Technology-based market intelligence
    tech_markets = {
        "javascript": {
            "market_size": "JavaScript development tools market valued at $24.3B in 2024, growing at 8.2% CAGR to reach $36.1B by 2029",
            "competitors_direct": "GitHub Copilot ($10/month), Replit ($20/month), CodeSandbox ($9/month), StackBlitz ($20/month), Glitch (freemium)",
            "competitors_indirect": "VS Code Extensions, JetBrains WebStorm ($59/year), Sublime Text ($99), Atom (discontinued)",
            "cac_estimate": "$45-85 for developer tools through content marketing, GitHub integration, and developer community engagement",
            "ltv_estimate": "$240-480 annually based on subscription retention rates of 65-80% for developer productivity tools"
        },
        "python": {
            "market_size": "Python development ecosystem market at $15.7B in 2024, projected 9.1% CAGR reaching $24.2B by 2029",
            "competitors_direct": "PyCharm Professional ($89/year), Jupyter Hub ($0.10/hour), Google Colab Pro ($9.99/month), Deepnote ($19/month)",
            "competitors_indirect": "VS Code Python extension, Spyder IDE, Anaconda Navigator, Sublime Text with Python packages",
            "cac_estimate": "$35-65 for Python tools via data science communities, university partnerships, and technical content",
            "ltv_estimate": "$180-360 annually with 70-85% retention in data science and ML developer segments"
        },
        "react": {
            "market_size": "React development tools market segment worth $8.9B in 2024, growing 12.3% annually to $15.8B by 2029",
            "competitors_direct": "Vercel Pro ($20/month), Netlify Pro ($19/month), Create React App alternatives, Next.js hosting platforms",
            "competitors_indirect": "Angular CLI, Vue CLI, Svelte Kit, traditional web hosting providers like AWS, Heroku",
            "cac_estimate": "$55-95 for React tools through developer conferences, open source contributions, and frontend communities",
            "ltv_estimate": "$300-600 annually with high retention due to framework lock-in and deployment convenience"
        },
        "web": {
            "market_size": "Web development tools market valued at $31.2B in 2024, expected 10.5% CAGR to reach $51.1B by 2029",
            "competitors_direct": "Webflow ($14-39/month), Wix ($14-39/month), Squarespace ($12-40/month), WordPress.com ($4-45/month)",
            "competitors_indirect": "Traditional web hosting, custom development agencies, no-code platforms like Bubble, Airtable",
            "cac_estimate": "$25-55 for web tools via SEO, social media advertising, and referral programs targeting SMBs",
            "ltv_estimate": "$168-468 annually with 60-75% retention rates in small business and freelancer segments"
        },
        "mobile": {
            "market_size": "Mobile app development tools market at $19.4B in 2024, growing 11.2% CAGR to reach $32.8B by 2029",
            "competitors_direct": "Expo ($99/month), Firebase ($25-400/month), AWS Amplify ($0.01-0.15/request), Supabase ($25/month)",
            "competitors_indirect": "Native development (Xcode/Android Studio), Xamarin, Cordova/PhoneGap, Unity for games",
            "cac_estimate": "$75-125 for mobile tools through app store optimization, developer conferences, and mobile-first content",
            "ltv_estimate": "$450-900 annually due to higher complexity and enterprise adoption in mobile development"
        },
        "ai": {
            "market_size": "AI development tools market valued at $42.8B in 2024, explosive 25.1% CAGR projected to reach $129.3B by 2029",
            "competitors_direct": "OpenAI API ($0.002/1K tokens), Anthropic Claude ($0.008/1K), Hugging Face Pro ($9-20/month), Replicate ($0.0002/second)",
            "competitors_indirect": "Google AI Platform, AWS SageMaker, Azure ML, traditional ML frameworks (TensorFlow, PyTorch)",
            "cac_estimate": "$95-175 for AI tools via technical demos, research partnerships, and ML community engagement",
            "ltv_estimate": "$600-1200 annually with premium pricing justified by AI capabilities and enterprise adoption"
        }
    }
    
    # Audience-based market insights
    audience_insights = {
        "developers": "Global developer population of 27.7M in 2024, growing 3.2% annually. 65% willing to pay $10-50/month for productivity tools. Primary pain points: debugging efficiency, deployment complexity, collaboration workflows.",
        "businesses": "SMB software spending at $145B annually, with 23% allocated to development tools. Enterprise segment shows 89% higher LTV but 3x longer sales cycles. Focus on ROI metrics and team productivity gains.",
        "startups": "Early-stage startups allocate 15-25% of technical budget to development tools. High price sensitivity but strong growth potential. Freemium models show 12-18% conversion rates to paid plans.",
        "enterprises": "Enterprise development tool spending averages $2,400 per developer annually. Security, compliance, and integration capabilities are key decision factors. Sales cycles 6-12 months but high retention rates."
    }
    
    # Determine primary technology category
    tech_lower = technology_stack.lower()
    primary_tech = "web"  # default
    
    if any(term in tech_lower for term in ["javascript", "js", "node", "npm"]):
        primary_tech = "javascript"
    elif any(term in tech_lower for term in ["python", "django", "flask", "fastapi"]):
        primary_tech = "python"
    elif any(term in tech_lower for term in ["react", "next", "gatsby", "jsx"]):
        primary_tech = "react"
    elif any(term in tech_lower for term in ["mobile", "ios", "android", "flutter", "react native"]):
        primary_tech = "mobile"
    elif any(term in tech_lower for term in ["ai", "ml", "machine learning", "neural", "gpt", "llm"]):
        primary_tech = "ai"
    
    # Get base market data
    market_base = tech_markets.get(primary_tech, tech_markets["web"])
    
    # Determine audience insights
    audience_lower = target_audience.lower()
    audience_key = "developers"  # default
    
    if "business" in audience_lower or "company" in audience_lower:
        audience_key = "businesses"
    elif "startup" in audience_lower or "entrepreneur" in audience_lower:
        audience_key = "startups"
    elif "enterprise" in audience_lower or "corporation" in audience_lower:
        audience_key = "enterprises"
    
    target_insights = audience_insights.get(audience_key, audience_insights["developers"])
    
    # Generate industry trends based on technology
    trends_map = {
        "javascript": "Rise of TypeScript adoption (78% of developers), serverless architecture growth, JAMstack popularity, micro-frontend architecture adoption",
        "python": "AI/ML integration surge, data science democratization, cloud-native Python applications, automated testing framework evolution",
        "react": "Server-side rendering renaissance, component library standardization, React 18 concurrent features adoption, performance optimization focus",
        "web": "Progressive Web App adoption, Core Web Vitals importance, headless CMS growth, edge computing integration",
        "mobile": "Cross-platform development preference, 5G capability integration, AR/VR feature adoption, app store optimization evolution",
        "ai": "Generative AI mainstream adoption, edge AI deployment, ethical AI framework development, multimodal AI integration"
    }
    
    # Growth projections based on technology maturity
    growth_map = {
        "javascript": "Steady 8-12% annual growth driven by web application complexity and Node.js server adoption",
        "python": "Strong 9-15% growth fueled by data science boom and AI/ML application development",
        "react": "Robust 12-18% growth as React dominates frontend development with 40.14% developer adoption",
        "web": "Moderate 6-10% growth with focus on performance, accessibility, and mobile-first development",
        "mobile": "Healthy 10-14% growth driven by emerging markets and 5G network expansion",
        "ai": "Explosive 20-30% growth as AI integration becomes standard across all software categories"
    }
    
    return {
        "market_size": market_base["market_size"],
        "competitors_direct": market_base["competitors_direct"],
        "competitors_indirect": market_base["competitors_indirect"],
        "industry_trends": trends_map.get(primary_tech, trends_map["web"]),
        "target_market_insights": target_insights,
        "growth_projections": growth_map.get(primary_tech, growth_map["web"]),
        "cac_estimate": market_base["cac_estimate"],
        "ltv_estimate": market_base["ltv_estimate"]
    }

def search_market_intelligence(project_name, technology_stack, target_audience):
    """Search for real market intelligence using web search APIs"""
    import os
    
    # Try multiple search approaches
    search_queries = [
        f"{technology_stack} market size 2024 growth rate",
        f"{technology_stack} development tools competitors pricing",
        f"{target_audience} software spending {technology_stack}",
        f"{project_name} similar companies funding valuation"
    ]
    
    market_data = {
        "market_size": "",
        "competitors_direct": "",
        "competitors_indirect": "",
        "industry_trends": "",
        "target_market_insights": "",
        "growth_projections": "",
        "cac_estimate": "",
        "ltv_estimate": ""
    }
    
    # Use DuckDuckGo search (no API key required)
    try:
        from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            # Search for market size data
            results = list(ddgs.text(search_queries[0], max_results=5))
            if results:
                market_size_info = extract_market_data_from_results(results, "market_size")
                if market_size_info:
                    market_data["market_size"] = market_size_info
            
            # Search for competitors
            results = list(ddgs.text(search_queries[1], max_results=5))
            if results:
                competitor_info = extract_market_data_from_results(results, "competitors")
                if competitor_info:
                    market_data["competitors_direct"] = competitor_info
            
            # Search for target audience insights
            results = list(ddgs.text(search_queries[2], max_results=5))
            if results:
                audience_info = extract_market_data_from_results(results, "audience")
                if audience_info:
                    market_data["target_market_insights"] = audience_info
        
        # Only return if we got meaningful data
        if any(market_data.values()):
            return market_data
            
    except ImportError:
        print("DEBUG: duckduckgo_search not available, trying requests-based search")
        # Fallback to basic web scraping
        return search_with_requests(search_queries)
    except Exception as e:
        print(f"DEBUG: DuckDuckGo search failed: {str(e)}")
    
    return None

def extract_market_data_from_results(results, data_type):
    """Extract relevant market data from search results"""
    combined_text = ""
    for result in results[:3]:  # Use top 3 results
        combined_text += f"{result.get('title', '')} {result.get('body', '')} "
    
    # Look for specific patterns based on data type
    if data_type == "market_size":
        # Look for market size figures
        import re
        patterns = [
            r'\$[\d.,]+\s*[BMK](?:illion)?',  # $5.2B, $500M, etc.
            r'[\d.,]+%\s*(?:CAGR|growth)',    # 15% CAGR, 8% growth
            r'market.*?worth.*?\$[\d.,]+[BMK]', # market worth $X
        ]
        for pattern in patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            if matches:
                return f"Market research indicates {' '.join(matches[:2])}"
    
    elif data_type == "competitors":
        # Look for company names and pricing
        import re
        # Common SaaS pricing patterns
        pricing_pattern = r'(\w+(?:\s+\w+)*)\s*[\$][\d.,]+(?:/month|/year|/user)'
        matches = re.findall(pricing_pattern, combined_text, re.IGNORECASE)
        if matches:
            return f"Key competitors include {', '.join(matches[:5])}"
    
    elif data_type == "audience":
        # Look for spending or adoption figures
        import re
        spending_patterns = [
            r'[\d.,]+%.*?(?:adopt|use|spend)',
            r'\$[\d.,]+.*?(?:budget|spending|allocation)',
            r'[\d.,]+(?:M|million|K|thousand).*?(?:users|developers|companies)'
        ]
        for pattern in spending_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            if matches:
                return f"Target market analysis shows {matches[0]}"
    
    return None

def search_with_requests(queries):
    """Fallback search using requests (limited functionality)"""
    # This is a basic fallback - in production you'd want to use proper APIs
    return None

def generate_openai_market_research(project_name, technology_stack, target_audience, project_description):
    """Generate market research using OpenAI with strict no-placeholder instructions"""
    import os
    
    try:
        import openai
        
        # Configure OpenAI
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            return None
        
        prompt = f"""
        You are a senior market research analyst. Provide SPECIFIC, FACTUAL market intelligence for this project.
        
        CRITICAL: Do NOT use placeholder text, brackets, or generic terms like [Company Name] or [X%]. 
        Use only real companies, actual figures, and specific data points from your knowledge.
        
        Project: {project_name}
        Technology: {technology_stack}
        Target Audience: {target_audience}
        Description: {project_description}
        
        Provide specific market data in this format:
        
        MARKET_SIZE: [Provide actual market size figures with specific dollar amounts and growth rates]
        COMPETITORS_DIRECT: [List real companies with actual pricing - no placeholders]
        COMPETITORS_INDIRECT: [List real alternative solutions with names and details]
        INDUSTRY_TRENDS: [Describe specific, named trends with data points]
        TARGET_INSIGHTS: [Provide specific demographic and behavioral data]
        GROWTH_PROJECTIONS: [Give actual growth forecasts with numbers]
        CAC_ESTIMATE: [Provide realistic CAC with specific reasoning]
        LTV_ESTIMATE: [Provide realistic LTV with specific calculations]
        
        Use your knowledge of real companies, actual market data, and industry benchmarks.
        Be specific and factual - no generic placeholder text allowed.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.3  # Lower temperature for more factual responses
        )
        
        market_intelligence = response.choices[0].message.content
        
        # Parse the response
        return parse_market_intelligence(market_intelligence)
        
    except Exception as e:
        print(f"DEBUG: OpenAI market research failed: {str(e)}")
        return None

def generate_market_intelligence(project_name, technology_stack, target_audience, project_description=""):
    """Generate comprehensive market intelligence using web search and alternative AI"""
    
    try:
        # First try web search for real market data
        market_data = search_market_intelligence(project_name, technology_stack, target_audience)
        if market_data:
            return market_data
    except Exception as e:
        print(f"DEBUG: Web search failed: {str(e)}")
    
    try:
        # Fallback to OpenAI with specific instructions to avoid placeholders
        market_data = generate_openai_market_research(project_name, technology_stack, target_audience, project_description)
        if market_data:
            return market_data
    except Exception as e:
        print(f"DEBUG: OpenAI research failed: {str(e)}")
    
    # Final fallback to deterministic data
    return generate_realistic_market_data(project_name, technology_stack, target_audience, project_description)

def parse_market_intelligence(intelligence_text):
    """Parse AI-generated market intelligence into structured data"""
    try:
        market_data = {
            "market_size": "",
            "competitors_direct": "",
            "competitors_indirect": "",
            "industry_trends": "",
            "target_market_insights": "",
            "growth_projections": "",
            "cac_estimate": "",
            "ltv_estimate": ""
        }
        
        # Extract sections using keywords
        lines = intelligence_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('MARKET_SIZE:'):
                current_section = 'market_size'
                market_data[current_section] = line.replace('MARKET_SIZE:', '').strip()
            elif line.startswith('COMPETITORS_DIRECT:'):
                current_section = 'competitors_direct'
                market_data[current_section] = line.replace('COMPETITORS_DIRECT:', '').strip()
            elif line.startswith('COMPETITORS_INDIRECT:'):
                current_section = 'competitors_indirect'
                market_data[current_section] = line.replace('COMPETITORS_INDIRECT:', '').strip()
            elif line.startswith('MARKET_TRENDS:'):
                current_section = 'industry_trends'
                market_data[current_section] = line.replace('MARKET_TRENDS:', '').strip()
            elif line.startswith('TARGET_INSIGHTS:'):
                current_section = 'target_market_insights'
                market_data[current_section] = line.replace('TARGET_INSIGHTS:', '').strip()
            elif line.startswith('GROWTH_PROJECTIONS:'):
                current_section = 'growth_projections'
                market_data[current_section] = line.replace('GROWTH_PROJECTIONS:', '').strip()
            elif line.startswith('CAC_ESTIMATE:'):
                current_section = 'cac_estimate'
                market_data[current_section] = line.replace('CAC_ESTIMATE:', '').strip()
            elif line.startswith('LTV_ESTIMATE:'):
                current_section = 'ltv_estimate'
                market_data[current_section] = line.replace('LTV_ESTIMATE:', '').strip()
            elif current_section and line:
                market_data[current_section] += " " + line
        
        return market_data
        
    except Exception as e:
        print(f"DEBUG: Failed to parse market intelligence: {str(e)}")
        return generate_realistic_market_data("", "", "", "")

def generate_realistic_market_data(project_name, technology_stack, target_audience, project_description=""):
    """Generate realistic market data using deterministic knowledge base"""
    
    # Technology-based market intelligence
    tech_markets = {
        "javascript": {
            "market_size": "JavaScript development tools market valued at $24.3B in 2024, growing at 8.2% CAGR to reach $36.1B by 2029",
            "competitors_direct": "GitHub Copilot ($10/month), Replit ($20/month), CodeSandbox ($9/month), StackBlitz ($20/month), Glitch (freemium)",
            "competitors_indirect": "VS Code Extensions, JetBrains WebStorm ($59/year), Sublime Text ($99), Atom (discontinued)",
            "cac_estimate": "$45-85 for developer tools through content marketing, GitHub integration, and developer community engagement",
            "ltv_estimate": "$240-480 annually based on subscription retention rates of 65-80% for developer productivity tools"
        },
        "python": {
            "market_size": "Python development ecosystem market at $15.7B in 2024, projected 9.1% CAGR reaching $24.2B by 2029",
            "competitors_direct": "PyCharm Professional ($89/year), Jupyter Hub ($0.10/hour), Google Colab Pro ($9.99/month), Deepnote ($19/month)",
            "competitors_indirect": "VS Code Python extension, Spyder IDE, Anaconda Navigator, Sublime Text with Python packages",
            "cac_estimate": "$35-65 for Python tools via data science communities, university partnerships, and technical content",
            "ltv_estimate": "$180-360 annually with 70-85% retention in data science and ML developer segments"
        },
        "react": {
            "market_size": "React development tools market segment worth $8.9B in 2024, growing 12.3% annually to $15.8B by 2029",
            "competitors_direct": "Vercel Pro ($20/month), Netlify Pro ($19/month), Create React App alternatives, Next.js hosting platforms",
            "competitors_indirect": "Angular CLI, Vue CLI, Svelte Kit, traditional web hosting providers like AWS, Heroku",
            "cac_estimate": "$55-95 for React tools through developer conferences, open source contributions, and frontend communities",
            "ltv_estimate": "$300-600 annually with high retention due to framework lock-in and deployment convenience"
        },
        "web": {
            "market_size": "Web development tools market valued at $31.2B in 2024, expected 10.5% CAGR to reach $51.1B by 2029",
            "competitors_direct": "Webflow ($14-39/month), Wix ($14-39/month), Squarespace ($12-40/month), WordPress.com ($4-45/month)",
            "competitors_indirect": "Traditional web hosting, custom development agencies, no-code platforms like Bubble, Airtable",
            "cac_estimate": "$25-55 for web tools via SEO, social media advertising, and referral programs targeting SMBs",
            "ltv_estimate": "$168-468 annually with 60-75% retention rates in small business and freelancer segments"
        },
        "mobile": {
            "market_size": "Mobile app development tools market at $19.4B in 2024, growing 11.2% CAGR to reach $32.8B by 2029",
            "competitors_direct": "Expo ($99/month), Firebase ($25-400/month), AWS Amplify ($0.01-0.15/request), Supabase ($25/month)",
            "competitors_indirect": "Native development (Xcode/Android Studio), Xamarin, Cordova/PhoneGap, Unity for games",
            "cac_estimate": "$75-125 for mobile tools through app store optimization, developer conferences, and mobile-first content",
            "ltv_estimate": "$450-900 annually due to higher complexity and enterprise adoption in mobile development"
        },
        "ai": {
            "market_size": "AI development tools market valued at $42.8B in 2024, explosive 25.1% CAGR projected to reach $129.3B by 2029",
            "competitors_direct": "OpenAI API ($0.002/1K tokens), Anthropic Claude ($0.008/1K), Hugging Face Pro ($9-20/month), Replicate ($0.0002/second)",
            "competitors_indirect": "Google AI Platform, AWS SageMaker, Azure ML, traditional ML frameworks (TensorFlow, PyTorch)",
            "cac_estimate": "$95-175 for AI tools via technical demos, research partnerships, and ML community engagement",
            "ltv_estimate": "$600-1200 annually with premium pricing justified by AI capabilities and enterprise adoption"
        }
    }
    
    # Audience-based market insights
    audience_insights = {
        "developers": "Global developer population of 27.7M in 2024, growing 3.2% annually. 65% willing to pay $10-50/month for productivity tools. Primary pain points: debugging efficiency, deployment complexity, collaboration workflows.",
        "businesses": "SMB software spending at $145B annually, with 23% allocated to development tools. Enterprise segment shows 89% higher LTV but 3x longer sales cycles. Focus on ROI metrics and team productivity gains.",
        "startups": "Early-stage startups allocate 15-25% of technical budget to development tools. High price sensitivity but strong growth potential. Freemium models show 12-18% conversion rates to paid plans.",
        "enterprises": "Enterprise development tool spending averages $2,400 per developer annually. Security, compliance, and integration capabilities are key decision factors. Sales cycles 6-12 months but high retention rates."
    }
    
    # Determine primary technology category
    tech_lower = technology_stack.lower()
    primary_tech = "web"  # default
    
    if any(term in tech_lower for term in ["javascript", "js", "node", "npm"]):
        primary_tech = "javascript"
    elif any(term in tech_lower for term in ["python", "django", "flask", "fastapi"]):
        primary_tech = "python"
    elif any(term in tech_lower for term in ["react", "next", "gatsby", "jsx"]):
        primary_tech = "react"
    elif any(term in tech_lower for term in ["mobile", "ios", "android", "flutter", "react native"]):
        primary_tech = "mobile"
    elif any(term in tech_lower for term in ["ai", "ml", "machine learning", "neural", "gpt", "llm"]):
        primary_tech = "ai"
    
    # Get base market data
    market_base = tech_markets.get(primary_tech, tech_markets["web"])
    
    # Determine audience insights
    audience_lower = target_audience.lower()
    audience_key = "developers"  # default
    
    if "business" in audience_lower or "company" in audience_lower:
        audience_key = "businesses"
    elif "startup" in audience_lower or "entrepreneur" in audience_lower:
        audience_key = "startups"
    elif "enterprise" in audience_lower or "corporation" in audience_lower:
        audience_key = "enterprises"
    
    target_insights = audience_insights.get(audience_key, audience_insights["developers"])
    
    # Generate industry trends based on technology
    trends_map = {
        "javascript": "Rise of TypeScript adoption (78% of developers), serverless architecture growth, JAMstack popularity, micro-frontend architecture adoption",
        "python": "AI/ML integration surge, data science democratization, cloud-native Python applications, automated testing framework evolution",
        "react": "Server-side rendering renaissance, component library standardization, React 18 concurrent features adoption, performance optimization focus",
        "web": "Progressive Web App adoption, Core Web Vitals importance, headless CMS growth, edge computing integration",
        "mobile": "Cross-platform development preference, 5G capability integration, AR/VR feature adoption, app store optimization evolution",
        "ai": "Generative AI mainstream adoption, edge AI deployment, ethical AI framework development, multimodal AI integration"
    }
    
    # Growth projections based on technology maturity
    growth_map = {
        "javascript": "Steady 8-12% annual growth driven by web application complexity and Node.js server adoption",
        "python": "Strong 9-15% growth fueled by data science boom and AI/ML application development",
        "react": "Robust 12-18% growth as React dominates frontend development with 40.14% developer adoption",
        "web": "Moderate 6-10% growth with focus on performance, accessibility, and mobile-first development",
        "mobile": "Healthy 10-14% growth driven by emerging markets and 5G network expansion",
        "ai": "Explosive 20-30% growth as AI integration becomes standard across all software categories"
    }
    
    return {
        "market_size": market_base["market_size"],
        "competitors_direct": market_base["competitors_direct"],
        "competitors_indirect": market_base["competitors_indirect"],
        "industry_trends": trends_map.get(primary_tech, trends_map["web"]),
        "target_market_insights": target_insights,
        "growth_projections": growth_map.get(primary_tech, growth_map["web"]),
        "cac_estimate": market_base["cac_estimate"],
        "ltv_estimate": market_base["ltv_estimate"]
    }

def _has_generation_access(user):
    """Check if user has access to generate pitch decks"""
    # Free tier users have no access
    if user.account_tier == 'free':
        return user.tokens and user.tokens > 0
    
    # Waitlisted users can generate if they completed survey and haven't used export
    if user.account_tier == 'waitlisted':
        return user.survey_completed and not user.survey_export_used
    
    # Basic and Pro users need tokens
    if user.account_tier in ['basic', 'pro']:
        return user.tokens and user.tokens > 0
    
    return False

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@dashboard_bp.route('/')
@login_required
def index():
    # Get user's recent projects
    recent_projects = Project.get_by_user(current_user.id, limit=5)
    
    stats = {
        'total_projects': len(Project.get_by_user(current_user.id)),
        'recent_count': len(recent_projects)
    }
    
    return render_template('dashboard/index.html', 
                         recent_projects=recent_projects, 
                         stats=stats)

@dashboard_bp.route('/generator')
@login_required
def generator():
    # Check if coming from GitHub repo selection
    from_github = request.args.get('from_github')
    selected_repo = session.get('selected_repo')
    
    # If coming from GitHub selection, auto-generate immediately
    if from_github and selected_repo:
        # Import here to avoid circular imports
        from api import try_fetch_readme_raw, try_fetch_readme_api, fetch_additional_repo_signals, analyze_repository_structure, build_gemini_prompt_from_code
        from firebase_models import Project
        import google.generativeai as genai
        import os
        import json
        from datetime import datetime
        
        try:
            repo_url = selected_repo['url']
            repo_owner = selected_repo['owner']
            repo_name = selected_repo['name']
            
            # Create a preliminary project to save user's work before generation
            preliminary_project = Project(
                title=repo_name,
                repo_url=repo_url,
                repo_owner=repo_owner,
                repo_name=repo_name,
                pitch_deck={
                    'content': 'Generation in progress...',
                    'generated_at': datetime.utcnow().isoformat(),
                    'version': '0.1',
                    'status': 'generating'
                },
                user_id=current_user.id
            )
            preliminary_project.save()
            
            # All users can generate projects - token checks only apply to exports
            
            # Debug session data
            print(f"DEBUG: Selected repo data: {selected_repo}")
            print(f"DEBUG: User token exists: {bool(current_user.github_token)}")
            print(f"DEBUG: Fetching README for {repo_owner}/{repo_name}")
            
            # Configure Gemini AI first (needed for both paths)
            GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
            if not GOOGLE_API_KEY:
                flash('AI service not configured', 'error')
                return redirect(url_for('dashboard.index'))
            
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Try to get README content
            user_token = current_user.github_token if current_user.is_authenticated else None
            if user_token:
                # Private repo - use API directly with user token
                content, source = try_fetch_readme_api(repo_owner, repo_name, user_token)
                print(f"DEBUG: API fetch result: {'Found' if content else 'Not found'}")
            else:
                # Public repo - try raw first, then API
                content, source = try_fetch_readme_raw(repo_owner, repo_name)
                if not content:
                    content, _ = try_fetch_readme_api(repo_owner, repo_name, user_token)
            
            if not content:
                print(f"DEBUG: No README found for {repo_owner}/{repo_name}, analyzing code structure instead")
                
                # Use code analysis instead of README
                repo_analysis = analyze_repository_structure(repo_owner, repo_name, user_token)
                
                if not repo_analysis.get("tech_stack") and repo_analysis.get("main_language") == "Unknown":
                    flash('Unable to analyze repository structure. Repository may be empty or inaccessible.', 'error')
                    return redirect(url_for('dashboard.generator'))
                
                # Generate content from code analysis
                prompt = build_gemini_prompt_from_code(repo_analysis, repo_name, extra_context=None)
                print(f"DEBUG: Code analysis prompt length: {len(prompt)} chars")
                
                try:
                    resp = model.generate_content(prompt)
                except Exception as e:
                    print(f"DEBUG: AI generation failed: {str(e)}")
                    flash(f'AI service error: {str(e)}', 'error')
                    return redirect(url_for('dashboard.generator'))
                
                text = getattr(resp, 'text', None) or (resp.candidates[0].content.parts[0].text if getattr(resp, 'candidates', None) else None)
                if not text:
                    print(f"DEBUG: Empty AI response for {repo_owner}/{repo_name}")
                    flash('Failed to generate content from AI service', 'error')
                    return redirect(url_for('dashboard.generator'))
                
                print(f"DEBUG: AI response length: {len(text)} chars")
                print(f"DEBUG: AI response preview: {text[:200]}...")
                
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
                    print(f"DEBUG: JSON parsing failed. Raw response: {text}")
                    print(f"DEBUG: Cleaned text: {clean_text}")
                    flash(f'Invalid response format from AI service: {str(e)}', 'error')
                    return redirect(url_for('dashboard.generator'))
                
                # Map the response to expected format (code analysis uses different keys)
                analysis_result = {
                    "title": parsed.get("project_title", repo_name),
                    "introduction": parsed.get("solution_overview", "Project analysis based on code structure."),
                    "problem_statement": parsed.get("problem_statement", "Problem inferred from code analysis."),
                    "solution_overview": parsed.get("solution_overview", "Solution based on technical implementation."),
                    "key_features": parsed.get("key_features", "Features inferred from codebase."),
                    "target_audience": parsed.get("target_audience", "Target audience based on technical stack."),
                    "technology_stack": parsed.get("technology_stack", "Technology stack detected from code."),
                    "future_scope": parsed.get("future_scope", "Future enhancements based on current foundation.")
                }
                
                content_source = "code_analysis"
                print(f"DEBUG: Generated content from code analysis for {repo_owner}/{repo_name}")
                
                # Generate market intelligence for code analysis projects
                print(f"DEBUG: Generating market intelligence for {repo_owner}/{repo_name}")
                market_research = generate_market_intelligence(
                    analysis_result.get("title", repo_name),
                    analysis_result.get("technology_stack", ""),
                    analysis_result.get("target_audience", ""),
                    analysis_result.get("solution_overview", "")
                )
            else:
                # README found - process normally
                content_source = "readme"
                print(f"DEBUG: Found README for {repo_owner}/{repo_name}")
                
                # Generate market intelligence for README projects
                print(f"DEBUG: Generating market intelligence for {repo_owner}/{repo_name}")
                market_research = generate_market_intelligence(
                    repo_name,
                    "web application",  # Default tech stack
                    "developers and businesses",  # Default target audience
                    content[:500] if content else ""  # First 500 chars of README as description
                )
            
            
            # Generate pitch deck content based on source
            if content_source == "code_analysis":
                # Convert analysis_result to slide format
                prompt = f"""You are an expert pitch deck consultant creating a compelling investor presentation. Convert the following project analysis into a comprehensive, detailed pitch deck that tells a compelling story and captures investor interest.

Project Analysis:
Title: {analysis_result['title']}
Problem Statement: {analysis_result['problem_statement']}
Solution Overview: {analysis_result['solution_overview']}
Key Features: {analysis_result['key_features']}
Target Audience: {analysis_result['target_audience']}
Technology Stack: {analysis_result['technology_stack']}
Future Scope: {analysis_result['future_scope']}

Market Intelligence Data:
Market Size Analysis: {market_research['market_size']}
Direct Competitors: {market_research['competitors_direct']}
Indirect Competitors: {market_research['competitors_indirect']}
Industry Trends: {market_research['industry_trends']}
Target Market Insights: {market_research['target_market_insights']}
Growth Projections: {market_research['growth_projections']}
Customer Acquisition Cost: {market_research['cac_estimate']}
Customer Lifetime Value: {market_research['ltv_estimate']}

Create a detailed, investor-ready 13-slide pitch deck. Each slide should be rich with specific details, compelling narratives, and actionable insights. Use ONLY plain text formatting - NO markdown symbols like ** or ## or - bullets. Format each slide clearly with the slide number and title, followed by detailed content in bullet points using simple dashes:

CRITICAL ANTI-PLACEHOLDER REQUIREMENTS:
- NO placeholder text anywhere - no [Company Name], [X%], [Insert Details], [TBD], [Amount], etc.
- Extract ALL content from the project description and repository analysis provided
- Use the market intelligence data for specific figures, competitors, and industry insights
- Apply industry knowledge to create realistic, specific information for any gaps
- Every slide must be complete and presentation-ready with concrete details
- Never use generic terms or ask readers to "insert" information

Slide 1: Title Slide
   - Compelling project name with memorable tagline that captures the essence
   - Repository owner and development team information
   - Current date and version
   - Brief one-liner describing the revolutionary impact

Slide 2: Problem Statement
   - Detailed description of the critical problem this project solves
   - Specific pain points users currently experience
   - Market size and scope of the problem (quantify when possible)
   - Why existing solutions fall short
   - Urgency and timing - why this problem needs solving now

Slide 3: Solution Overview
   - Comprehensive explanation of how this project uniquely addresses the problem
   - Detailed core features and key functionality breakdown
   - Unique value proposition and competitive differentiators
   - User experience improvements and benefits
   - Technical innovation and breakthrough aspects

Slide 4: Market Opportunity
   - Research and calculate total addressable market (TAM) with specific dollar figures and annual growth rates for this project's sector
   - Determine serviceable addressable market (SAM) and serviceable obtainable market (SOM) based on realistic market penetration
   - Create detailed user personas with specific demographics, pain points, buying behavior, and willingness to pay
   - Analyze market segments and prioritize target segments based on size, growth potential, and competitive intensity
   - Develop geographic expansion roadmap with specific market entry strategies and timing
   - Project revenue potential with conservative, optimistic, and realistic scenarios based on market data
   - Analyze market timing, technology adoption curves, and competitive dynamics

Slide 5: Product Demo
   - Comprehensive walkthrough of key features and capabilities
   - User experience highlights and interface advantages
   - Technical capabilities showcase with specific examples
   - Performance metrics and benchmarks
   - Integration possibilities and ecosystem compatibility

Slide 6: Technology Stack
   - Detailed technical architecture overview and design decisions
   - Scalability approach and performance optimization strategies
   - Security measures, reliability features, and data protection
   - Development methodology and quality assurance processes
   - Innovation aspects and technical competitive advantages

Slide 7: Business Model
   - Primary revenue streams with detailed monetization strategies
   - Pricing model analysis (freemium, subscription, one-time, usage-based)
   - Calculate realistic customer acquisition cost based on the marketing channels and target audience
   - Estimate customer lifetime value using industry benchmarks and project characteristics
   - Unit economics breakdown with contribution margins
   - Strategic partnership revenue opportunities and channel strategies
   - Revenue diversification plan and recurring revenue components
   - Scalability factors and operational leverage points

Slide 8: Competitive Analysis
   - Research and identify 3-5 direct competitors in the same space, analyze their features, pricing models, and target markets
   - Research and identify 3-5 indirect competitors or substitute solutions that address similar user needs
   - Create a detailed feature comparison showing where this project has advantages and gaps
   - Analyze competitor pricing strategies and position this project's value proposition
   - Identify market positioning opportunities and white space in the competitive landscape
   - Provide specific SWOT analysis based on actual competitor research
   - Outline competitive differentiation strategy and sustainable advantages

Slide 9: Go-to-Market Strategy
   - Phase-by-phase market entry strategy with specific timelines and milestones
   - Customer acquisition channels ranked by cost-effectiveness and scalability
   - Sales funnel optimization with conversion rate targets at each stage
   - Strategic partnerships and channel partner enablement programs
   - Marketing mix strategy (digital, content, events, PR) with budget allocation
   - Customer success and retention programs to maximize lifetime value
   - Geographic expansion sequence and localization requirements

Slide 10: Team and Expertise
   - Detailed core team member profiles with relevant experience
   - Specific background and expertise that validates execution capability
   - Advisory support, mentors, and strategic partnerships
   - Hiring plans and key positions to fill
   - Track record of success and relevant achievements

Slide 11: Financial Projections
   - 5-year financial model with revenue, expenses, and profitability projections
   - Key assumptions driving growth (user acquisition, pricing, market penetration)
   - Detailed cost structure including COGS, operating expenses, and capital requirements
   - Break-even analysis and path to profitability timeline
   - Cash flow projections and working capital requirements
   - Key performance indicators (KPIs) and financial metrics tracking
   - Sensitivity analysis showing best case, base case, and worst case scenarios

Slide 12: Investment Ask
   - Specific funding amount requested with clear justification
   - Detailed breakdown of fund allocation across key areas
   - Expected milestones and measurable outcomes for each funding tranche
   - Investor benefits and potential return on investment
   - Exit strategy considerations and value creation timeline

Slide 13: Next Steps and Vision
   - Immediate development milestones with specific timelines
   - Comprehensive long-term product vision and roadmap
   - Strategic partnership opportunities and expansion plans
   - Market expansion strategy and international opportunities
   - Innovation pipeline and future product development

IMPORTANT: You are an expert investor and serial entrepreneur with deep market knowledge. Use the market intelligence data provided above to generate specific, realistic content for every slide. For competitive analysis, use the direct and indirect competitors listed in the market intelligence. For market opportunity, use the market size analysis and target insights provided. For business metrics, use the CAC and LTV estimates from the market intelligence data. Integrate this research seamlessly into the pitch deck slides - do not just copy-paste but weave the insights naturally into compelling investor narratives. Every slide should reflect the specific market intelligence gathered for this project."""

                response = model.generate_content(prompt)
                pitch_deck_content = response.text
            else:
                # Process README content normally
                user_token = current_user.github_token if current_user.is_authenticated else None
                extra = fetch_additional_repo_signals(repo_owner, repo_name, user_token)
                
                # Generate pitch deck content from README
                prompt = f"""You are an expert pitch deck consultant creating a compelling investor presentation. Generate a comprehensive, detailed pitch deck for the following GitHub repository that tells a compelling story and captures investor interest.

Project: {repo_name}
Repository: {repo_owner}/{repo_name}

README Content:\n{content}\n\n

Market Intelligence Data:
Market Size Analysis: {market_research['market_size']}
Direct Competitors: {market_research['competitors_direct']}
Indirect Competitors: {market_research['competitors_indirect']}
Industry Trends: {market_research['industry_trends']}
Target Market Insights: {market_research['target_market_insights']}
Growth Projections: {market_research['growth_projections']}
Customer Acquisition Cost: {market_research['cac_estimate']}
Customer Lifetime Value: {market_research['ltv_estimate']}

Create a detailed, investor-ready pitch deck. Each slide should be rich with specific details, compelling narratives, and actionable insights derived from the README content, repository context, and market research data above. Use ONLY plain text formatting - NO markdown symbols like ** or ## or - bullets. Format each slide clearly with the slide number and title, followed by detailed content in bullet points using simple dashes:

CRITICAL ANTI-PLACEHOLDER REQUIREMENTS:
- NO placeholder text anywhere - no [Company Name], [X%], [Insert Details], [TBD], [Amount], etc.
- Extract ALL content from the README and repository analysis provided
- Use the market intelligence data for specific figures, competitors, and industry insights
- Apply industry knowledge to create realistic, specific information for any gaps
- Every slide must be complete and presentation-ready with concrete details
- Never use generic terms or ask readers to "insert" information

Slide 1: Title Slide
   - Compelling project name with memorable tagline that captures the essence
   - Repository owner and development team information
   - Current date and version
   - Brief one-liner describing the revolutionary impact

Slide 2: Problem Statement
   - Detailed description of the critical problem this project solves
   - Specific pain points users currently experience
   - Market size and scope of the problem (quantify when possible)
   - Why existing solutions fall short
   - Urgency and timing - why this problem needs solving now

Slide 3: Solution Overview
   - Comprehensive explanation of how this project uniquely addresses the problem
   - Detailed core features and key functionality breakdown
   - Unique value proposition and competitive differentiators
   - User experience improvements and benefits
   - Technical innovation and breakthrough aspects

Slide 4: Market Opportunity
   - Research and calculate total addressable market (TAM) with specific dollar figures and annual growth rates for this project's sector
   - Determine serviceable addressable market (SAM) and serviceable obtainable market (SOM) based on realistic market penetration
   - Create detailed user personas with specific demographics, pain points, buying behavior, and willingness to pay
   - Analyze market segments and prioritize target segments based on size, growth potential, and competitive intensity
   - Develop geographic expansion roadmap with specific market entry strategies and timing
   - Project revenue potential with conservative, optimistic, and realistic scenarios based on market data
   - Analyze market timing, technology adoption curves, and competitive dynamics

Slide 5: Product Demonstration
   - Comprehensive walkthrough of key features and capabilities
   - User experience highlights and interface advantages
   - Technical capabilities showcase with specific examples
   - Performance metrics and benchmarks
   - Integration possibilities and ecosystem compatibility

Slide 6: Business Model
   - Comprehensive revenue generation strategy and monetization approach
   - Detailed pricing structure with multiple tiers or options
   - Customer acquisition cost and lifetime value projections
   - Partnership revenue opportunities
   - Subscription, licensing, or transaction-based revenue streams

Slide 7: Traction and Growth
   - Current user adoption metrics and growth trajectory
   - Performance indicators and key milestones achieved
   - Community engagement statistics and user feedback
   - Market validation and early adopter testimonials
   - Growth rate projections and scaling strategies

Slide 8: Competitive Analysis
   - Research and identify 3-5 direct competitors in the same space, analyze their features, pricing models, and target markets
   - Research and identify 3-5 indirect competitors or substitute solutions that address similar user needs
   - Create a detailed feature comparison showing where this project has advantages and gaps
   - Analyze competitor pricing strategies and position this project's value proposition
   - Identify market positioning opportunities and white space in the competitive landscape
   - Provide specific SWOT analysis based on actual competitor research
   - Outline competitive differentiation strategy and sustainable advantages

Slide 9: Technology Stack
   - Detailed technical architecture overview and design decisions
   - Scalability approach and performance optimization strategies
   - Security measures, reliability features, and data protection
   - Development methodology and quality assurance processes
   - Innovation aspects and technical competitive advantages

Slide 10: Team and Expertise
   - Detailed core team member profiles with relevant experience
   - Specific background and expertise that validates execution capability
   - Advisory support, mentors, and strategic partnerships
   - Hiring plans and key positions to fill
   - Track record of success and relevant achievements

Slide 11: Financial Projections
   - 5-year financial model with revenue, expenses, and profitability projections
   - Key assumptions driving growth (user acquisition, pricing, market penetration)
   - Detailed cost structure including COGS, operating expenses, and capital requirements
   - Break-even analysis and path to profitability timeline
   - Cash flow projections and working capital requirements
   - Key performance indicators (KPIs) and financial metrics tracking
   - Sensitivity analysis showing best case, base case, and worst case scenarios

Slide 12: Investment Ask
   - Specific funding amount requested with clear justification
   - Detailed breakdown of fund allocation across key areas
   - Expected milestones and measurable outcomes for each funding tranche
   - Investor benefits and potential return on investment
   - Exit strategy considerations and value creation timeline

Slide 13: Next Steps and Vision
   - Immediate development milestones with specific timelines
   - Comprehensive long-term product vision and roadmap
   - Strategic partnership opportunities and expansion plans
   - Market expansion strategy and international opportunities
   - Innovation pipeline and future product development

Additional context: {extra}

IMPORTANT: Make each slide rich with specific details, compelling narratives, and actionable insights derived from both the README content AND the market research data provided above. Incorporate market size figures, industry trends, competitive insights, and growth projections into relevant slides. Avoid generic statements. Use concrete examples from the repository, specific metrics when available, and create a compelling story that builds investor confidence. Extract maximum value from both the README content and market research to create substantive, detailed slides. Each slide should have 4-6 detailed points that provide substantial value and insight."""
            
            response = model.generate_content(prompt)
            pitch_deck_content = response.text
            
            # Update the preliminary project with the generated content
            preliminary_project.pitch_deck = {
                'content': pitch_deck_content,
                'generated_at': datetime.utcnow().isoformat(),
                'version': '1.0',
                'status': 'completed'
            }
            preliminary_project.save()
            # No token usage for generation - tokens are only for exports
            
            # Clear session data
            session.pop('selected_repo', None)
            
            flash('Pitch deck generated successfully!', 'success')
            return redirect(url_for('dashboard.project_detail', project_id=preliminary_project.id))
            
        except Exception as e:
            flash(f'Failed to generate pitch deck: {str(e)}', 'error')
            return redirect(url_for('dashboard.index'))
    
    # Regular generator page for manual URL entry
    return render_template('dashboard/generator.html', from_github=from_github)

@dashboard_bp.route('/documentation/<project_id>')
@login_required
def documentation(project_id):
    """View project documentation"""
    project = Project.get(project_id)
    
    if not project or project.user_id != current_user.id:
        flash('Project not found or access denied.', 'error')
        return redirect(url_for('dashboard.projects'))
    
    return render_template('dashboard/documentation.html', project=project)

@dashboard_bp.route('/user-guide/<project_id>')
@login_required
def user_guide(project_id):
    """View project user guide"""
    project = Project.get(project_id)
    
    if not project or project.user_id != current_user.id:
        flash('Project not found or access denied.', 'error')
        return redirect(url_for('dashboard.projects'))
    
    return render_template('dashboard/user_guide.html', project=project)

@dashboard_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    if query:
        projects = Project.search_by_user(current_user.id, query)
    else:
        projects = []
    
    return jsonify([{
        'id': p.id,
        'title': p.title,
        'repo_url': p.repo_url,
        'created_at': p.created_at.isoformat() if p.created_at else None
    } for p in projects])

@dashboard_bp.route('/admin')
@login_required
@admin_required
def admin():
    """Admin dashboard with user statistics"""
    # Get statistics
    total_users = User.get_user_count()
    total_projects = Project.get_project_count()
    total_generations = Project.get_generation_count()
    
    # Get recent users and projects
    recent_users = User.get_all_users(limit=10)
    recent_projects = Project.get_all_projects(limit=10)
    
    stats = {
        'total_users': total_users,
        'total_projects': total_projects,
        'total_generations': total_generations
    }
    
    return render_template('dashboard/admin.html', 
                         stats=stats, 
                         recent_users=recent_users,
                         recent_projects=recent_projects)

@dashboard_bp.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Admin user management page"""
    users = User.get_all_users(limit=100)
    deleted_users = User.get_deleted_users(limit=100)
    return render_template('dashboard/admin_users.html', users=users, deleted_users=deleted_users)

@dashboard_bp.route('/admin/projects')
@login_required
@admin_required
def admin_projects():
    """Admin project management page"""
    projects = Project.get_all_projects(limit=100)
    
    # Get user information for each project
    projects_with_users = []
    for project in projects:
        user = User.get(project.user_id) if project.user_id else None
        project_data = {
            'project': project,
            'user': user
        }
        projects_with_users.append(project_data)
    
    return render_template('dashboard/admin_projects.html', projects_with_users=projects_with_users)

@dashboard_bp.route('/projects')
@login_required
def projects():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    search = request.args.get('search', '')
    
    if search:
        all_projects = Project.search_by_user(current_user.id, search)
    else:
        all_projects = Project.get_by_user(current_user.id)
    
    # Manual pagination since we're using Firebase
    total = len(all_projects)
    start = (page - 1) * per_page
    end = start + per_page
    items = all_projects[start:end]
    
    # Create a mock pagination object
    class MockPagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None
            
        def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
            last = self.pages
            for num in range(1, last + 1):
                if num <= left_edge or \
                   (self.page - left_current - 1 < num < self.page + right_current) or \
                   num > last - right_edge:
                    yield num
    
    projects = MockPagination(items, page, per_page, total)
    
    return render_template('dashboard/projects.html', projects=projects, search=search)

@dashboard_bp.route('/projects/<project_id>')
@login_required
def project_detail(project_id):
    project = Project.get(project_id)
    if not project or project.user_id != current_user.id:
        flash('Project not found', 'error')
        return redirect(url_for('dashboard.projects'))
    return render_template('dashboard/project_detail.html', project=project)

@dashboard_bp.route('/projects/<project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.get(project_id)
    if not project or project.user_id != current_user.id:
        flash('Project not found', 'error')
        return redirect(url_for('dashboard.projects'))
    
    if project.delete():
        flash('Project deleted successfully', 'success')
    else:
        flash('Failed to delete project', 'error')
    return redirect(url_for('dashboard.projects'))

@dashboard_bp.route('/projects/<project_id>/rename', methods=['POST'])
@login_required
def rename_project(project_id):
    """Rename a project"""
    try:
        project = Project.get(project_id)
        if not project or project.user_id != current_user.id:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.get_json()
        new_title = data.get('title', '').strip()
        
        if not new_title:
            return jsonify({'error': 'Title is required'}), 400
        
        project.title = new_title
        project.save()
        
        return jsonify({'success': True, 'message': 'Project renamed successfully'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to rename project: {str(e)}'}), 500

@dashboard_bp.route('/settings')
@login_required
def settings():
    # Get user's project statistics
    user_projects = Project.get_by_user(current_user.id)
    stats = {
        'total_projects': len(user_projects)
    }
    
    # Get user preferences from session
    preferences = session.get('user_preferences', {
        'default_style': 'investor',
        'slide_count': '12',
        'include_financials': True,
        'include_competition': True
    })
    
    return render_template('dashboard/settings.html', stats=stats, preferences=preferences)

@dashboard_bp.route('/settings/profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        
        if not username or not email:
            return jsonify({'error': 'Username and email are required'}), 400
        
        # Check if username is already taken by another user
        existing_user = User.get_by_username(username)
        if existing_user and existing_user.id != current_user.id:
            return jsonify({'error': 'Username already taken'}), 400
        
        # Check if email is already taken by another user
        existing_user = User.get_by_email(email)
        if existing_user and existing_user.id != current_user.id:
            return jsonify({'error': 'Email already taken'}), 400
        
        # Update user information
        current_user.username = username
        current_user.email = email
        current_user.save()
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500

@dashboard_bp.route('/settings/password', methods=['POST'])
@login_required
def update_password():
    """Update user password"""
    try:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new passwords are required'}), 400
        
        # Verify current password
        if not current_user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Update password
        current_user.set_password(new_password)
        current_user.save()
        
        return jsonify({'success': True, 'message': 'Password updated successfully'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to update password: {str(e)}'}), 500

@dashboard_bp.route('/settings/preferences', methods=['POST'])
@login_required
def update_preferences():
    """Update user preferences"""
    try:
        data = request.get_json()
        # For now, we'll store preferences in session or could extend User model
        # This is a placeholder for future preference storage
        session['user_preferences'] = {
            'default_style': data.get('default_style', 'investor'),
            'slide_count': data.get('slide_count', '12'),
            'include_financials': data.get('include_financials', True),
            'include_competition': data.get('include_competition', True)
        }
        
        return jsonify({'success': True, 'message': 'Preferences saved successfully'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to save preferences: {str(e)}'}), 500

@dashboard_bp.route('/settings/disconnect-github', methods=['POST'])
@login_required
def disconnect_github():
    """Disconnect GitHub account"""
    try:
        current_user.github_id = None
        current_user.github_username = None
        current_user.github_token = None
        current_user.save()
        
        return jsonify({'success': True, 'message': 'GitHub account disconnected'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to disconnect GitHub: {str(e)}'}), 500

@dashboard_bp.route('/settings/export', methods=['POST'])
@login_required
def export_data():
    """Export user data"""
    try:
        # Get all user projects
        projects = Project.get_by_user(current_user.id)
        
        export_data = {
            'user': {
                'username': current_user.username,
                'email': current_user.email,
                'account_tier': current_user.account_tier,
                'tokens': current_user.tokens,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None
            },
            'projects': []
        }
        
        for project in projects:
            export_data['projects'].append({
                'id': project.id,
                'title': project.title,
                'repo_url': project.repo_url,
                'repo_owner': project.repo_owner,
                'repo_name': project.repo_name,
                'pitch_deck': project.pitch_deck,
                'created_at': project.created_at.isoformat() if project.created_at else None
            })
        
        from flask import make_response
        import json
        
        response = make_response(json.dumps(export_data, indent=2))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = 'attachment; filename=PitchPerfectAI-data-export.json'
        
        return response
    
    except Exception as e:
        return jsonify({'error': f'Failed to export data: {str(e)}'}), 500

@dashboard_bp.route('/settings/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    try:
        # Delete all user projects
        projects = Project.get_by_user(current_user.id)
        for project in projects:
            project.delete()
        
        # Delete user account using the User model's delete method
        if current_user.delete():
            # Logout user
            from flask_login import logout_user
            logout_user()
            return jsonify({'success': True, 'message': 'Account deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete user account'}), 500
    
    except Exception as e:
        return jsonify({'error': f'Failed to delete account: {str(e)}'}), 500


@dashboard_bp.route('/survey')
@login_required
def survey():
    """Display survey for waitlisted users"""
    if current_user.account_tier != 'waitlisted':
        flash('Survey is only available for waitlisted users.', 'info')
        return redirect(url_for('dashboard.index'))
    
    if current_user.survey_completed:
        flash('You have already completed the survey.', 'info')
        return redirect(url_for('dashboard.index'))
    
    from firebase_models import Survey
    active_survey = Survey.get_active()
    
    if not active_survey:
        flash('No survey is currently available.', 'info')
        return redirect(url_for('dashboard.index'))
    
    return render_template('dashboard/survey.html', survey=active_survey)


@dashboard_bp.route('/survey/submit', methods=['POST'])
@login_required
def submit_survey():
    """Submit survey responses"""
    if current_user.account_tier != 'waitlisted':
        return jsonify({'error': 'Survey is only available for waitlisted users'}), 403
    
    if current_user.survey_completed:
        return jsonify({'error': 'You have already completed the survey'}), 400
    
    try:
        from firebase_models import Survey, SurveyResponse
        
        active_survey = Survey.get_active()
        if not active_survey:
            return jsonify({'error': 'No active survey found'}), 404
        
        # Get responses from form
        responses = {}
        for i, question in enumerate(active_survey.questions):
            response_key = f'question_{i}'
            if response_key in request.form:
                responses[str(i)] = request.form[response_key]
        
        # Save survey response
        survey_response = SurveyResponse(
            survey_id=active_survey.id,
            user_id=current_user.id,
            responses=responses
        )
        
        if survey_response.save():
            # Mark user as having completed survey
            current_user.survey_completed = True
            current_user.save()
            
            return jsonify({
                'success': True,
                'message': 'Survey completed successfully! You can now export your pitch deck.',
                'redirect': url_for('dashboard.index')
            })
        else:
            return jsonify({'error': 'Error saving survey response. Please try again.'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Error submitting survey: {str(e)}'}), 500


# Admin routes for survey management
@dashboard_bp.route('/admin/surveys')
@login_required
@admin_required
def admin_surveys():
    """Admin survey management"""
    from firebase_models import Survey
    surveys = Survey.get_all()
    return render_template('dashboard/admin_surveys.html', surveys=surveys)


@dashboard_bp.route('/admin/surveys/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_new_survey():
    """Create new survey with AI-generated or manual questions"""
    if request.method == 'POST':
        try:
            survey_title = request.form.get('title', 'User Feedback Survey')
            creation_method = request.form.get('creation_method', 'ai')
            
            if creation_method == 'manual':
                # Handle manual survey creation
                questions = []
                form_data = request.form
                
                # Extract questions from form data
                question_indices = set()
                for key in form_data.keys():
                    if key.startswith('questions[') and key.endswith('][text]'):
                        # Extract index from questions[0][text] format
                        index = key.split('[')[1].split(']')[0]
                        question_indices.add(int(index))
                
                for i in sorted(question_indices):
                    question_text = form_data.get(f'questions[{i}][text]', '').strip()
                    question_type = form_data.get(f'questions[{i}][type]', 'text')
                    question_options = form_data.get(f'questions[{i}][options]', '').strip()
                    
                    if question_text:  # Only add non-empty questions
                        question_data = {
                            "question": question_text,
                            "type": question_type
                        }
                        
                        # Add options for multiple choice questions
                        if question_type in ['radio', 'checkbox'] and question_options:
                            options = [opt.strip() for opt in question_options.split('\n') if opt.strip()]
                            question_data["options"] = options
                        elif question_type == 'rating':
                            question_data["scale"] = 5
                            
                        questions.append(question_data)
                
                if not questions:
                    flash('Please add at least one question.', 'error')
                    return render_template('dashboard/admin_new_survey.html')
                    
            else:
                # AI generation
                import google.generativeai as genai
                import os
                
                # Configure Gemini AI
                genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
                model = genai.GenerativeModel('gemini-1.5-flash')
            
                # Generate survey questions using Gemini
                prompt = """
                Generate 8-10 survey questions for users of a pitch deck generation AI tool. 
                The questions should help us understand:
                1. User's business background and experience
                2. What they're looking for in a pitch deck tool
                3. Their pain points with current solutions
                4. Feature preferences and priorities
                5. Feedback on AI-generated content quality
                
                Return the questions as a JSON array of objects with this format:
                [
                    {"question": "What is your primary role?", "type": "multiple_choice", "options": ["Entrepreneur", "Startup Founder", "Business Analyst", "Other"]},
                    {"question": "How would you rate the quality of AI-generated content?", "type": "rating", "scale": 5},
                    {"question": "What features are most important to you?", "type": "text"}
                ]
                
                Question types can be: "text", "multiple_choice", "rating", "yes_no"
                """
                
                response = model.generate_content(prompt)
                
                # Parse the JSON response
                import json
                import re
                
                # Extract JSON from response
                json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if json_match:
                    questions_json = json_match.group()
                    questions = json.loads(questions_json)
                else:
                    # Fallback questions if Gemini fails
                    questions = [
                        {"question": "What is your primary role?", "type": "multiple_choice", "options": ["Entrepreneur", "Startup Founder", "Business Analyst", "Investor", "Other"]},
                        {"question": "How many pitch decks have you created before?", "type": "multiple_choice", "options": ["0", "1-3", "4-10", "10+"]},
                        {"question": "What's your biggest challenge in creating pitch decks?", "type": "text"},
                        {"question": "How important is AI-generated content quality to you?", "type": "rating", "scale": 5},
                        {"question": "Would you recommend this tool to others?", "type": "yes_no"},
                        {"question": "What features would you like to see added?", "type": "text"},
                        {"question": "How satisfied are you with the current tool?", "type": "rating", "scale": 5},
                        {"question": "What's your industry or business sector?", "type": "text"}
                    ]
            
            # Create and save survey
            from firebase_models import Survey
            
            # Deactivate existing surveys
            existing_surveys = Survey.get_all()
            for survey in existing_surveys:
                if survey.is_active:
                    survey.is_active = False
                    survey.save()
            
            new_survey = Survey(
                title=survey_title,
                questions=questions,
                is_active=True
            )
            
            if new_survey.save():
                flash('Survey created successfully with AI-generated questions!', 'success')
                return redirect(url_for('dashboard.admin_surveys'))
            else:
                flash('Failed to save survey', 'error')
        
        except Exception as e:
            flash(f'Failed to create survey: {str(e)}', 'error')
    
    return render_template('dashboard/admin_new_survey.html')


@dashboard_bp.route('/admin/surveys/<survey_id>/responses')
@login_required
@admin_required
def admin_survey_responses(survey_id):
    """View survey responses and analytics"""
    from firebase_models import Survey, SurveyResponse, User
    
    survey = Survey.get(survey_id)
    if not survey:
        flash('Survey not found', 'error')
        return redirect(url_for('dashboard.admin_surveys'))
    
    responses = SurveyResponse.get_all_by_survey(survey_id)
    
    # Get user details for responses
    response_data = []
    for response in responses:
        user = User.get(response.user_id)
        response_data.append({
            'response': {
                'id': response.id,
                'user_id': response.user_id,
                'responses': response.responses,
                'created_at': response.created_at.isoformat() if response.created_at else None
            },
            'user': {
                'id': user.id if user else None,
                'username': user.username if user else 'Unknown',
                'email': user.email if user else 'Unknown'
            }
        })
    
    # Generate analytics
    analytics = {
        'total_responses': len(responses),
        'question_analytics': {}
    }
    
    # Analyze each question
    for i, question in enumerate(survey.questions):
        question_responses = []
        for response in responses:
            if str(i) in response.responses:
                question_responses.append(response.responses[str(i)])
        
        analytics['question_analytics'][i] = {
            'question': {
                'question': question.get('question', ''),
                'type': question.get('type', ''),
                'options': question.get('options', [])
            },
            'responses': question_responses,
            'response_count': len(question_responses)
        }
        
        # Add specific analytics based on question type
        if question.get('type') == 'rating':
            if question_responses:
                ratings = [int(r) for r in question_responses if r.isdigit()]
                if ratings:
                    analytics['question_analytics'][i]['average_rating'] = sum(ratings) / len(ratings)
        
        elif question.get('type') == 'multiple_choice':
            from collections import Counter
            analytics['question_analytics'][i]['option_counts'] = dict(Counter(question_responses))
    
    return render_template('dashboard/admin_survey_responses.html', 
                         survey=survey, 
                         response_data=response_data,
                         analytics=analytics)


# Admin routes for coupon management
@dashboard_bp.route('/admin/coupons')
@login_required
@admin_required
def admin_coupons():
    """Admin coupon management"""
    from firebase_models import Coupon
    coupons = Coupon.get_all()
    return render_template('dashboard/admin_coupons.html', coupons=coupons)


@dashboard_bp.route('/admin/coupons/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_new_coupon():
    """Create new coupon"""
    if request.method == 'POST':
        try:
            from firebase_models import Coupon
            from datetime import datetime, timedelta
            
            code = request.form.get('code', '').upper()
            discount_type = request.form.get('discount_type', 'percentage')
            discount_value = float(request.form.get('discount_value', 0))
            applies_to = request.form.get('applies_to', 'all')
            max_uses = request.form.get('max_uses')
            expires_days = request.form.get('expires_days')
            
            # Validate required fields
            if not code:
                flash('Coupon code is required', 'error')
                return render_template('dashboard/admin_new_coupon.html')
            
            # Check if coupon code already exists
            existing_coupon = Coupon.get_by_code(code)
            if existing_coupon:
                flash('Coupon code already exists', 'error')
                return render_template('dashboard/admin_new_coupon.html')
            
            # Calculate expiration date
            expires_at = None
            if expires_days:
                expires_at = datetime.utcnow() + timedelta(days=int(expires_days))
            
            # Create coupon
            coupon = Coupon(
                code=code,
                discount_type=discount_type,
                discount_value=discount_value,
                applies_to=applies_to,
                max_uses=int(max_uses) if max_uses else None,
                expires_at=expires_at
            )
            
            if coupon.save():
                flash(f'Coupon "{code}" created successfully!', 'success')
                return redirect(url_for('dashboard.admin_coupons'))
            else:
                flash('Failed to create coupon', 'error')
        
        except Exception as e:
            flash(f'Failed to create coupon: {str(e)}', 'error')
    
    return render_template('dashboard/admin_new_coupon.html')

@dashboard_bp.route('/admin/coupons/<coupon_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_coupon(coupon_id):
    coupon = Coupon.get_by_id(coupon_id)
    if not coupon:
        flash('Coupon not found', 'error')
        return redirect(url_for('dashboard.admin_coupons'))
    
    if request.method == 'POST':
        try:
            # Update coupon details
            coupon.discount_type = request.form.get('discount_type')
            coupon.discount_value = float(request.form.get('discount_value'))
            coupon.applies_to = request.form.get('applies_to')
            coupon.max_uses = int(request.form.get('max_uses', 0)) if request.form.get('max_uses') else None
            
            # Handle expiration date
            expires_at = request.form.get('expires_at')
            if expires_at:
                coupon.expires_at = datetime.strptime(expires_at, '%Y-%m-%d')
            else:
                coupon.expires_at = None
            
            coupon.save()
            flash('Coupon updated successfully!', 'success')
            return redirect(url_for('dashboard.admin_coupons'))
            
        except Exception as e:
            flash(f'Error updating coupon: {str(e)}', 'error')
    
    return render_template('dashboard/admin_edit_coupon.html', coupon=coupon)

@dashboard_bp.route('/admin/surveys/<survey_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_survey(survey_id):
    survey = Survey.get(survey_id)
    if not survey:
        flash('Survey not found', 'error')
        return redirect(url_for('dashboard.admin_surveys'))
    
    if request.method == 'POST':
        try:
            survey.title = request.form.get('title')
            
            # Parse questions from form
            questions = []
            question_count = int(request.form.get('question_count', 0))
            
            for i in range(question_count):
                question_text = request.form.get(f'question_{i}_text')
                question_type = request.form.get(f'question_{i}_type')
                
                if question_text and question_type:
                    question = {
                        'text': question_text,
                        'type': question_type
                    }
                    
                    # Add options for multiple choice questions
                    if question_type == 'multiple_choice':
                        options = []
                        for j in range(5):  # Max 5 options
                            option = request.form.get(f'question_{i}_option_{j}')
                            if option:
                                options.append(option)
                        question['options'] = options
                    
                    questions.append(question)
            
            survey.questions = questions
            survey.save()
            
            flash('Survey updated successfully!', 'success')
            return redirect(url_for('dashboard.admin_surveys'))
            
        except Exception as e:
            flash(f'Error updating survey: {str(e)}', 'error')
    
    return render_template('dashboard/admin_edit_survey.html', survey=survey)

@dashboard_bp.route('/admin/user-management')
@login_required
@admin_required
def admin_user_management():
    try:
        users = User.get_all_users()
        return render_template('dashboard/admin_user_management.html', users=users)
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'error')
        return redirect(url_for('dashboard.admin'))

@dashboard_bp.route('/admin/user-management/<user_id>/change-plan', methods=['POST'])
@login_required
@admin_required
def admin_change_user_plan(user_id):
    try:
        user = User.get(user_id)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('dashboard.admin_user_management'))
        
        new_plan = request.form.get('new_plan')
        if new_plan not in ['free', 'basic', 'pro', 'waitlisted']:
            flash('Invalid plan selected', 'error')
            return redirect(url_for('dashboard.admin_user_management'))
        
        old_plan = user.account_tier
        user.account_tier = new_plan
        
        # Reset survey fields if changing to waitlisted
        if new_plan == 'waitlisted':
            user.survey_completed = False
            user.survey_export_used = False
        
        user.save()
        
        flash(f'User {user.username} plan changed from {old_plan} to {new_plan}', 'success')
        
    except Exception as e:
        flash(f'Error changing user plan: {str(e)}', 'error')
    
    return redirect(url_for('dashboard.admin_user_management'))

@dashboard_bp.route('/admin/survey-analytics')
@login_required
@admin_required
def admin_survey_analytics():
    try:
        surveys = Survey.get_all()
        analytics_data = []
        
        for survey in surveys:
            responses = SurveyResponse.get_all_by_survey(survey.id)
            
            # Calculate analytics
            total_responses = len(responses)
            completion_rate = 0
            avg_ratings = {}
            
            if total_responses > 0:
                # Calculate average ratings for rating questions
                for i, question in enumerate(survey.questions):
                    if question.get('type') == 'rating':
                        ratings = []
                        for response in responses:
                            # Use question index as key (stored as string)
                            answer = response.responses.get(str(i))
                            if answer and str(answer).isdigit():
                                ratings.append(int(answer))
                        
                        if ratings:
                            avg_ratings[question['question']] = sum(ratings) / len(ratings)
            
            analytics_data.append({
                'survey': survey,
                'total_responses': total_responses,
                'avg_ratings': avg_ratings,
                'responses': responses
            })
        
        return render_template('dashboard/admin_survey_analytics.html', analytics_data=analytics_data)
        
    except Exception as e:
        flash(f'Error loading survey analytics: {str(e)}', 'error')
        return redirect(url_for('dashboard.admin'))

@dashboard_bp.route('/out-of-tokens')
@login_required
def out_of_tokens():
    """Page shown when users are out of tokens"""
    try:
        # Get user's project count for stats
        user_projects = Project.get_by_user(current_user.id)
        user_projects_count = len(user_projects) if user_projects else 0
        
        # Check if there's an interrupted project in session
        interrupted_project_id = session.get('interrupted_project_id')
        interrupted_project = None
        if interrupted_project_id:
            interrupted_project = Project.get(interrupted_project_id)
            # Clear from session after retrieving
            session.pop('interrupted_project_id', None)
        
        return render_template('dashboard/out_of_tokens.html', 
                             user_projects_count=user_projects_count,
                             interrupted_project=interrupted_project)
    except Exception as e:
        flash(f'Error loading page: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))
