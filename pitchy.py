"""
Pitchy - AI assistant that helps users iterate on a project's pitch deck.

- review_pitch(): scores each section and suggests what to strengthen
- chat(): conversational help, optionally proposing a rewrite of one section
- replace_section(): applies a rewritten section to the pitch markdown
"""
import json
import re

from huggingface_client import generate_text, LAST_ERRORS

MAX_PITCH_CHARS = 12000
MAX_HISTORY = 10
MAX_MESSAGE_CHARS = 2000

PITCHY_PERSONA = (
    "You are Pitchy, a friendly, sharp pitch deck coach inside the Synoptic app. "
    "You have reviewed thousands of startup pitches and know what investors look for. "
    "Be specific, practical and encouraging; refer to the user's actual content. "
    "Never invent facts about the user's company: when data is missing, say what "
    "kind of evidence to add and give clearly labelled example figures."
)


class PitchyError(Exception):
    """Raised when no AI provider could produce a response."""


def split_sections(content):
    """Return [(heading, body)] for each '## ' section in the pitch markdown."""
    sections = []
    current = None
    for line in (content or '').splitlines():
        match = re.match(r'^##\s+(.+?)\s*$', line)
        if match and not line.startswith('###'):
            current = [match.group(1), []]
            sections.append(current)
        elif current is not None:
            current[1].append(line)
    return [(h, '\n'.join(b).strip()) for h, b in sections]


def _normalize(name):
    return re.sub(r'[^a-z0-9]+', ' ', (name or '').lower()).strip()


def replace_section(content, section, new_body):
    """
    Replace the body of the '## <section>' block (matched loosely by name).
    If the section doesn't exist, append it before a trailing '---' footer.
    Returns (new_content, heading_used).
    """
    new_body = re.sub(r'^\s*##\s+.*\n', '', new_body.strip(), count=1).strip()
    lines = (content or '').splitlines()
    target = _normalize(section)

    start = None
    heading = section
    for i, line in enumerate(lines):
        match = re.match(r'^##\s+(.+?)\s*$', line)
        if match and not line.startswith('###'):
            name = _normalize(match.group(1))
            if name == target or (target and (target in name or name in target)):
                start, heading = i, match.group(1)
                break

    if start is not None:
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if re.match(r'^##\s', lines[j]) or lines[j].strip() == '---':
                end = j
                break
        new_lines = lines[:start + 1] + [new_body, ''] + lines[end:]
        return '\n'.join(new_lines).strip() + '\n', heading

    # Append as a new section, keeping any trailing footer last
    footer_at = max((i for i, l in enumerate(lines) if l.strip() == '---'), default=None)
    block = [f'## {section}', new_body, '']
    if footer_at is not None:
        lines = lines[:footer_at] + block + lines[footer_at:]
    else:
        lines = lines + [''] + block
    return '\n'.join(lines).strip() + '\n', section


def _parse_json(text):
    """Extract the first JSON object from a model response."""
    if not text:
        return None
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    start, end = cleaned.find('{'), cleaned.rfind('}')
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return None


def _generate(prompt, stage):
    text = generate_text(prompt, stage, budget_seconds=45)
    if not text:
        raise PitchyError('; '.join(LAST_ERRORS) or 'unknown error')
    return text


def review_pitch(title, content):
    """
    Score each section of the pitch and suggest improvements.
    Returns {'summary': str, 'sections': [{'name', 'score', 'issue', 'suggestion'}]}
    sorted weakest first.
    """
    section_names = [h for h, _ in split_sections(content)]
    prompt = f"""{PITCHY_PERSONA}

Review this pitch deck for "{title}" the way an experienced seed investor would.

PITCH DECK (Markdown):
{(content or '')[:MAX_PITCH_CHARS]}

Existing sections: {', '.join(section_names) or 'none'}

Score each existing section from 1 (weak) to 5 (investor-ready). Also flag up to
two important MISSING sections investors expect (e.g. Traction, Team, Competition,
Financials, Go-to-Market) with score 0.

Respond with ONLY a JSON object, no prose, in exactly this shape:
{{"summary": "one or two sentences on the deck's overall strength and the single biggest gap",
  "sections": [
    {{"name": "section heading exactly as written (or the missing section's name)",
      "score": 3,
      "issue": "what is weak or missing, in one sentence",
      "suggestion": "the most valuable concrete improvement, in one or two sentences"}}
  ]}}"""

    data = _parse_json(_generate(prompt, 'PITCHY-REVIEW'))
    if not data or not isinstance(data.get('sections'), list):
        raise PitchyError('Review response was not valid JSON')

    sections = []
    for item in data['sections'][:12]:
        if not isinstance(item, dict) or not item.get('name'):
            continue
        try:
            score = max(0, min(5, int(item.get('score', 3))))
        except (TypeError, ValueError):
            score = 3
        sections.append({
            'name': str(item['name'])[:80],
            'score': score,
            'issue': str(item.get('issue', ''))[:400],
            'suggestion': str(item.get('suggestion', ''))[:600],
        })
    sections.sort(key=lambda s: s['score'])
    return {'summary': str(data.get('summary', ''))[:600], 'sections': sections}


def chat(title, content, history, message):
    """
    Answer a user message about their pitch.
    Returns {'reply': markdown str, 'rewrite': None | {'section': str, 'content': str}}
    """
    turns = []
    for turn in (history or [])[-MAX_HISTORY:]:
        if not isinstance(turn, dict):
            continue
        role = 'User' if turn.get('role') == 'user' else 'Pitchy'
        turns.append(f"{role}: {str(turn.get('content', ''))[:MAX_MESSAGE_CHARS]}")
    section_names = [h for h, _ in split_sections(content)]

    prompt = f"""{PITCHY_PERSONA}

You are helping the user improve the pitch deck for "{title}".

CURRENT PITCH DECK (Markdown):
{(content or '')[:MAX_PITCH_CHARS]}

Sections: {', '.join(section_names) or 'none'}

CONVERSATION SO FAR:
{chr(10).join(turns) or '(none)'}

User: {message[:MAX_MESSAGE_CHARS]}

Reply helpfully and concisely (under 180 words; short paragraphs or bullets).
If the user asks you to rewrite, improve, strengthen, expand or add a section,
ALSO provide the full replacement text for that ONE section so they can apply it.
The rewrite must be complete, investor-ready Markdown for the section body only
(no '## ' heading line), 2-4 paragraphs, and built on the existing content.

Respond with ONLY a JSON object, no prose, in exactly this shape:
{{"reply": "your message to the user (Markdown allowed)",
  "rewrite": null or {{"section": "exact heading of the section being replaced, or the new section's name",
                       "content": "the full new section body"}}}}"""

    text = _generate(prompt, 'PITCHY-CHAT')
    data = _parse_json(text)
    if not data or not data.get('reply'):
        # Model ignored the JSON format; use its text as the reply
        return {'reply': text.strip()[:4000], 'rewrite': None}

    rewrite = data.get('rewrite')
    if not (isinstance(rewrite, dict) and rewrite.get('section') and rewrite.get('content')):
        rewrite = None
    else:
        rewrite = {'section': str(rewrite['section'])[:80], 'content': str(rewrite['content'])[:8000]}
    return {'reply': str(data['reply'])[:4000], 'rewrite': rewrite}
