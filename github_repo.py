"""
Collect what we need from a GitHub repository to write a pitch about it:
metadata, README (or manifest files when there is none) and languages.
"""
import json
import os
import re

import requests

API = 'https://api.github.com'
TIMEOUT = 8
README_CHARS = 6000
MANIFESTS = ('package.json', 'pyproject.toml', 'requirements.txt', 'Cargo.toml', 'go.mod',
             'composer.json', 'Gemfile', 'pom.xml', 'build.gradle', 'pubspec.yaml')


class RepoError(Exception):
    """A problem the user can act on (bad URL, no access, rate limit)."""


def parse_repo(value):
    """Accept 'owner/name' or any github.com URL; return (owner, name)."""
    text = (value or '').strip()
    text = re.sub(r'^(https?://)?(www\.)?github\.com/', '', text, flags=re.I)
    text = re.sub(r'^git@github\.com:', '', text, flags=re.I)
    parts = [p for p in re.split(r'[/?#]', text) if p]
    if len(parts) < 2:
        raise RepoError('Enter a repository as owner/name or paste its GitHub URL.')
    owner, name = parts[0], re.sub(r'\.git$', '', parts[1])
    if not re.fullmatch(r'[A-Za-z0-9-]{1,39}', owner) or not re.fullmatch(r'[A-Za-z0-9._-]{1,100}', name):
        raise RepoError('That doesn\'t look like a valid GitHub repository.')
    return owner, name


def _headers(token, accept='application/vnd.github+json'):
    headers = {'Accept': accept, 'User-Agent': 'Synoptic-PitchPerfect', 'X-GitHub-Api-Version': '2022-11-28'}
    token = token or os.getenv('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers


def _get(path, token, accept='application/vnd.github+json'):
    try:
        return requests.get(f'{API}{path}', headers=_headers(token, accept), timeout=TIMEOUT)
    except requests.RequestException as e:
        raise RepoError(f'Could not reach GitHub ({e.__class__.__name__}). Please try again.')


def _clean_readme(text):
    """Strip badges, images, HTML and link noise so the model sees the prose."""
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    text = re.sub(r'\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)', '', text)  # linked badges
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)            # images / badges
    text = re.sub(r'\[\s*\]\([^)]*\)', '', text)                  # empty links left behind
    text = re.sub(r'<img[^>]*>', '', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)                          # other HTML tags
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)         # links -> text
    text = re.sub(r'```.*?```', '[code sample omitted]', text, flags=re.S)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _manifest_summary(owner, name, token):
    """When there's no README, summarise top-level files and dependency manifests."""
    r = _get(f'/repos/{owner}/{name}/contents', token)
    if r.status_code != 200 or not isinstance(r.json(), list):
        return ''
    entries = r.json()
    lines = ['Top-level files: ' + ', '.join(sorted(e['name'] for e in entries)[:40])]
    for entry in entries:
        if entry.get('name') in MANIFESTS and entry.get('type') == 'file':
            f = _get(f'/repos/{owner}/{name}/contents/{entry["path"]}', token, 'application/vnd.github.raw')
            if f.status_code != 200:
                continue
            body = f.text
            if entry['name'] == 'package.json':
                try:
                    pkg = json.loads(body)
                    body = json.dumps({k: pkg.get(k) for k in ('name', 'description', 'keywords')
                                       if pkg.get(k)}) + '\nDependencies: ' + ', '.join(
                        list((pkg.get('dependencies') or {}).keys())[:25])
                except ValueError:
                    pass
            lines.append(f'{entry["name"]}:\n{body[:1200]}')
        if len(lines) > 5:
            break
    return '\n\n'.join(lines)


def fetch_repo_context(value, token=None):
    """
    Return {'owner', 'name', 'title', 'url', 'context'} for a repository.
    Raises RepoError with a user-facing message on failure.
    """
    owner, name = parse_repo(value)
    r = _get(f'/repos/{owner}/{name}', token)
    if r.status_code == 404:
        raise RepoError(f'Repository {owner}/{name} was not found, or it is private and your '
                        'GitHub account hasn\'t granted access. Connect GitHub with repository access and try again.')
    if r.status_code in (401, 403):
        if r.headers.get('X-RateLimit-Remaining') == '0':
            raise RepoError('GitHub\'s rate limit was reached. Please wait a few minutes and try again.')
        raise RepoError('GitHub refused access to this repository. Reconnect GitHub with repository access and try again.')
    if r.status_code != 200:
        raise RepoError(f'GitHub returned an error ({r.status_code}). Please try again.')
    meta = r.json()
    owner, name = meta['owner']['login'], meta['name']  # canonical casing / renamed repos

    parts = [f'Repository: {meta["full_name"]}']
    if meta.get('description'):
        parts.append(f'Description: {meta["description"]}')
    if meta.get('topics'):
        parts.append('Topics: ' + ', '.join(meta['topics']))
    if meta.get('homepage'):
        parts.append(f'Website: {meta["homepage"]}')
    parts.append(f'Stars: {meta.get("stargazers_count", 0)}, forks: {meta.get("forks_count", 0)}')

    langs = _get(f'/repos/{owner}/{name}/languages', token)
    if langs.status_code == 200 and langs.json():
        total = sum(langs.json().values()) or 1
        parts.append('Languages: ' + ', '.join(f'{k} {v * 100 // total}%' for k, v in
                                                 sorted(langs.json().items(), key=lambda kv: -kv[1])[:6]))

    readme = _get(f'/repos/{owner}/{name}/readme', token, 'application/vnd.github.raw')
    if readme.status_code == 200 and readme.text.strip():
        parts.append('README:\n' + _clean_readme(readme.text)[:README_CHARS])
    else:
        summary = _manifest_summary(owner, name, token)
        if summary:
            parts.append('No README. ' + summary)
        elif not meta.get('description'):
            raise RepoError(f'{owner}/{name} has no README, description or recognisable project files '
                            'to base a pitch on. Add a README and try again.')

    title = re.sub(r'[-_]+', ' ', meta['name']).strip()
    title = title[:1].upper() + title[1:]
    return {'owner': owner, 'name': meta['name'], 'title': title, 'url': meta['html_url'],
            'private': meta.get('private', False), 'context': '\n\n'.join(parts)}
