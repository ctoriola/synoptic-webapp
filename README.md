# Synoptic - AI Pitch Deck Generator

Synoptic is a web application that automatically generates investor-ready pitch decks from any project using AI. Provide project details, upload documentation, or connect your GitHub account to let our AI analyze your project and create comprehensive pitch presentations.

## Features

- **Multiple Input Methods**: Describe your project, upload documentation, or connect GitHub repositories
- **AI-Powered Analysis**: Uses Google's Gemini AI to analyze repository content and generate pitch decks
- **Multiple Export Formats**: Export your pitch decks as PowerPoint (PPTX), Word (DOCX), or PDF
- **User Authentication**: Secure login with GitHub OAuth integration
- **Token-Based Usage**: Fair usage system with different account tiers
- **Documentation Generation**: Generate technical documentation and user guides
- **Admin Dashboard**: Administrative tools for user and project management

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
