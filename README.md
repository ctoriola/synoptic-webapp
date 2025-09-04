# PitchPerfectAI - AI Pitch Deck Generator

Transform any project into professional, investor-ready pitch decks using advanced AI. PitchPerfectAI analyzes your project details and automatically generates comprehensive presentations that showcase your technology, market opportunity, and business potential.

## 🚀 Key Features

### **AI-Powered Pitch Deck Generation**
- **Multiple Input Methods**: Project descriptions, uploaded documents (PDF, DOC, MD), or GitHub repositories
- **Advanced AI Analysis**: Google Gemini AI understands your project context and business model
- **Investor-Ready Output**: 13-slide comprehensive pitch decks with all essential elements
- **Professional Export**: PowerPoint (PPTX), Word (DOCX), and PDF formats

### **Flexible Project Input**
- **Text Descriptions**: Detailed project descriptions with business context
- **Document Upload**: Support for various file formats (TXT, MD, DOC, DOCX, PDF)
- **GitHub Integration**: Quick-start with repository analysis for developers
- **Multiple Pitch Styles**: Investor pitch, product demo, or partnership proposals

### **User Experience**
- **Secure Authentication**: GitHub OAuth integration with optional account creation
- **Token-Based System**: Fair usage with Free, Pro, and Enterprise tiers
- **Project Management**: Save, organize, and manage multiple pitch decks
- **Admin Dashboard**: Comprehensive management tools for administrators

## Technology Stack

- **Backend**: Python Flask with Firebase integration
- **Frontend**: HTML, CSS (Tailwind), JavaScript
- **AI**: Google Gemini AI for content generation
- **Authentication**: GitHub OAuth
- **Database**: Firebase Firestore
- **Deployment**: Supports Vercel, Netlify, and AWS deployment

## Getting Started

### Prerequisites

- Python 3.8+
- Firebase project
- Google AI API key
- GitHub OAuth app

### Installation

1. Clone the repository:
```bash
git clone https://github.com/ctoriola/synoptic-webapp.git
cd synoptic-webapp
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Configure Firebase:
   - Follow instructions in `FIREBASE_SETUP.md`

5. Set up GitHub OAuth:
   - Follow instructions in `GITHUB_OAUTH_SETUP.md`

6. Run the application:
```bash
python app.py
```

## Configuration

The application requires several environment variables:

- `SECRET_KEY`: Flask secret key
- `GOOGLE_API_KEY`: Google AI API key
- `GITHUB_CLIENT_ID`: GitHub OAuth client ID
- `GITHUB_CLIENT_SECRET`: GitHub OAuth client secret
- Firebase configuration variables

See `.env.example` for a complete list.

## Deployment

The application supports multiple deployment platforms:

- **Vercel**: See `vercel.json` configuration
- **Netlify**: See `netlify.toml` configuration  
- **AWS**: See `AWS_RDS_SETUP.md` for database setup

## Usage

1. **Sign Up/Login**: Create an account or login with GitHub
2. **Describe Your Project**: Provide project details or upload documentation
3. **Optional GitHub Integration**: Connect repositories for quick-start
4. **Generate Pitch Deck**: AI analyzes your project and creates a pitch deck
5. **Export**: Download in your preferred format (PPTX, DOCX, PDF)

## Features in Detail

### AI Pitch Deck Generation
- Analyzes project descriptions, documentation, and uploaded files
- Generates comprehensive 13-slide investor pitch deck
- Includes problem statement, solution, market opportunity, and more

### Documentation Tools
- Technical documentation generation
- User guide creation
- Export capabilities for all generated content

### Account Management
- Token-based usage system
- Multiple account tiers (Free, Pro, Enterprise)
- Usage tracking and limits

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please open an issue on GitHub or contact the development team.
