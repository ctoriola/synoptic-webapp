"""
Deck length plans shared by pitch generation and the PowerPoint export.

The slide count is the number of content slides: one per pitch section, exactly
what the user sees on the project page. The PowerPoint export adds a cover and a
closing slide (and an agenda for longer decks) around them.
"""

SLIDE_COUNTS = (4, 6, 10)
DEFAULT_SLIDE_COUNT = 6

PLANS = {
    4: {
        'agenda': False, 'words': 110,
        'sections': ['Problem', 'Solution', 'Market Opportunity', 'The Ask'],
    },
    6: {
        'agenda': False, 'words': 100,
        'sections': ['Problem', 'Solution', 'Market Opportunity', 'Business Model',
                     'Competition', 'The Ask'],
    },
    10: {
        'agenda': True, 'words': 85,
        'sections': ['Problem', 'Solution', 'Product', 'Market Opportunity', 'Business Model',
                     'Competition', 'Go-to-Market', 'Traction & Milestones', 'Team', 'The Ask'],
    },
}

for _n, _plan in PLANS.items():
    _plan['total'] = _n
    _plan['closing'] = True
    assert len(_plan['sections']) == _n


def normalize_slide_count(value):
    """Map any stored/requested value to a supported slide count."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SLIDE_COUNT
    if n in PLANS:
        return n
    # Older preferences (8, 12, 15, 20) map to the nearest supported length
    return min(SLIDE_COUNTS, key=lambda c: (abs(c - n), c))


def get_plan(value):
    return PLANS[normalize_slide_count(value)]


def user_slide_count(user):
    prefs = getattr(user, 'preferences', None) or {}
    return normalize_slide_count(prefs.get('slide_count', DEFAULT_SLIDE_COUNT))
