"""
Deck length plans shared by pitch generation and the PowerPoint export.

A plan's `total` is the exact number of slides in the exported deck:
cover + (agenda) + one slide per section + (closing).
"""

SLIDE_COUNTS = (4, 8, 12, 20)
DEFAULT_SLIDE_COUNT = 12

PLANS = {
    4: {
        'agenda': False, 'closing': False, 'words': 110,
        'sections': ['Problem', 'Solution', 'Market & The Ask'],
    },
    8: {
        'agenda': False, 'closing': True, 'words': 100,
        'sections': ['Problem', 'Solution', 'Market Opportunity', 'Business Model',
                     'Competition', 'The Ask'],
    },
    12: {
        'agenda': True, 'closing': True, 'words': 90,
        'sections': ['Problem', 'Solution', 'Product', 'Market Opportunity', 'Business Model',
                     'Competition', 'Go-to-Market', 'Traction & Milestones', 'The Ask'],
    },
    20: {
        'agenda': True, 'closing': True, 'words': 70,
        'sections': ['Problem', 'Why Now', 'Solution', 'Product', 'How It Works',
                     'Market Opportunity', 'Target Customers', 'Business Model', 'Competition',
                     'Competitive Advantage', 'Go-to-Market', 'Traction & Milestones', 'Roadmap',
                     'Team', 'Financial Projections', 'Use of Funds', 'The Ask'],
    },
}

for _n, _plan in PLANS.items():
    _plan['total'] = _n
    assert 1 + _plan['agenda'] + len(_plan['sections']) + _plan['closing'] == _n


def normalize_slide_count(value):
    """Map any stored/requested value to a supported slide count."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SLIDE_COUNT
    if n in PLANS:
        return n
    # Older preferences (10, 15) map to the nearest supported length
    return min(SLIDE_COUNTS, key=lambda c: (abs(c - n), c))


def get_plan(value):
    return PLANS[normalize_slide_count(value)]


def user_slide_count(user):
    prefs = getattr(user, 'preferences', None) or {}
    return normalize_slide_count(prefs.get('slide_count', DEFAULT_SLIDE_COUNT))
