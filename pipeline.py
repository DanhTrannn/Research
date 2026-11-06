"""Shared HTTP and small parsing helpers. Each schools/*.py owns its extraction flow."""
import json
import os
import re
import subprocess
import tempfile
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
BROWSER_MODE = 'auto'
BROWSER_HEADLESS = not bool(os.environ.get('DISPLAY'))
BROWSER_WAIT = 25
BROWSER_PROFILE = None
MANUAL_CHALLENGE_WAIT = 0
_BROWSER_START_LOCK = Lock()
DEFAULT_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36', 'Accept': 'text/html,application/xhtml+xml'}
MONEY = re.compile(r'\$\s*(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)(?![\d,])')
NEGATION = re.compile(r'\b(?:non[ -]?renewable|not renewable|cannot be renewed|not be renewed|one[ -]time|(?:first year|year 1) only)\b', re.I)
POSITIVE = re.compile(r'\b(?:renewable|renewed)\b', re.I)
MONTHS = r'January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec'
DATE = re.compile(r'\b(' + MONTHS + r')\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b', re.I)

def validate_html(status, body, content_type='text/html'):
    soup = BeautifulSoup(body, 'html.parser')
    title = text(soup.title).lower() if soup.title else ''
    raw = body.decode('utf-8', errors='replace') if isinstance(body, bytes) else body
    if status in (202, 401, 403, 429):
        return None, 'blocked'
    if status != 200:
        return None, 'http_error'
    if (title in {'just a moment...', 'access denied', 'attention required! | cloudflare'}
            or any(marker in raw.lower() for marker in (
                'awswaf.setup', 'aws-waf-token', '_cf_chl_opt', 'id="challenge-form"', 'cf-chl-'))):
        return None, 'blocked'
    if 'html' not in content_type.lower() or not soup.find(['h1', 'h2', 'h3', 'table']):
        return None, 'invalid_content'
    if re.search(r'\b(?:404|page not found|page cannot be found)\b', title):
        return None, 'not_found'
    if not re.search(r'scholarship|award|bursar|financial aid', text(soup), re.I):
        return None, 'unexpected_content'
    return soup, None

def compact(value):
    return re.sub(r'\s+', ' ', str(value)).strip()

def key(value):
    return re.sub(r'[^a-z0-9]+', ' ', str(value).lower()).strip()

def distinct(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result

def grade(raw, system='academic_average_percent'):
    """Parse a single explicit grade band, not every number in prose."""
    value = compact(raw).replace('–', '-').replace('−', '-')
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*%?\s*(?:-\s*(\d+(?:\.\d+)?)\s*%?|(\+))?', value)
    if not match and system == 'academic_average_percent':
        # Preserve credential qualifiers while recognizing an explicit 80%+.
        match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:-\s*(\d+(?:\.\d+)?)\s*%?|(\+))', value)
    if match:
        lower = float(match[1])
        upper = float(match[2]) if match[2] else None
        ceiling = 45 if system == 'international_baccalaureate' else 100
        if lower > ceiling or (upper is not None and (upper > ceiling or lower > upper)):
            match = None
    return {'system': system, 'min': float(match[1]) if match else None,
            'max': float(match[2]) if match and match[2] else None,
            'minimum_inclusive': True if match else None, 'raw': raw}

def renewal(evidence):
    negatives = [s for s in evidence if NEGATION.search(s)]
    positives = [s for s in evidence if POSITIVE.search(NEGATION.sub(' ', s))]
    value = None if bool(negatives) == bool(positives) else bool(positives)
    return {'is_renewable': value, 'conditions_text': distinct(positives + negatives)}

def date_value(raw):
    raw = compact(raw)
    iso = None
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw):
        try:
            iso = datetime.strptime(raw, '%Y-%m-%d').date().isoformat()
        except ValueError:
            pass
    else:
        match = DATE.search(raw)
        if match and match[3]:
            for fmt in ('%B %d %Y', '%b %d %Y'):
                try:
                    month = 'Sep' if match[1].lower() == 'sept' else match[1]
                    iso = datetime.strptime(f'{month} {match[2]} {match[3]}', fmt).date().isoformat()
                    break
                except ValueError:
                    continue
    return {'raw': raw, 'date': iso}

def money_values(raw, header='', currency=None):
    """Recognize explicit value statements without computing missing totals."""
    raw = compact(raw)
    found = list(MONEY.finditer(raw))
    if not found:
        return []
    values = []
    def claim(amount, basis, fragment, maximum_only=False, minimum_only=False, payments=None):
        return {'kind': 'money', 'currency': currency,
                'min_amount': None if maximum_only else amount,
                'max_amount': None if minimum_only else amount,
                'payment_basis': basis, 'max_payments': payments, 'evidence_text': fragment}
    consumed = set()
    # Example: $40,000 ($10,000 x 4 years). Keep two distinct bases.
    schedule = re.search(r'\$\s*([\d,]+(?:\.\d+)?)\s*[x×]\s*(\d+)\s*years?', raw, re.I)
    if schedule:
        values.append(claim(float(schedule[1].replace(',', '')), 'per_year', schedule[0], payments=int(schedule[2])))
        consumed.update(m.start() for m in found if schedule.start() <= m.start() < schedule.end())
    ranged = re.search(r'\$\s*([\d,]+(?:\.\d+)?)\s*[-–]\s*\$\s*([\d,]+(?:\.\d+)?)', raw)
    if ranged and len(found) == 2:
        lower, upper = (float(ranged[i].replace(',', '')) for i in (1, 2))
        if lower <= upper:
            value = claim(lower, 'unknown', raw)
            value['max_amount'] = upper
            if re.search(r'\bper year\b|/\s*year', raw, re.I):
                value['payment_basis'] = 'per_year'
            elif re.search(r'\bper term\b|/\s*term', raw, re.I):
                value['payment_basis'] = 'per_term'
            elif re.search(r'\bone[ -]time\b', raw, re.I):
                value['payment_basis'] = 'one_time'
            return [value]
    for index, match in enumerate(found):
        if match.start() in consumed:
            continue
        # Only text up to the next amount belongs to this amount's basis.
        tail = raw[match.end():found[index + 1].start() if index + 1 < len(found) else len(raw)]
        head = raw[max(0, match.start() - 25):match.start()]
        basis = 'unknown'
        if re.search(r'\bper term\b|/\s*term', tail, re.I):
            basis = 'per_term'
        elif re.search(r'\bper year\b|/\s*year', tail, re.I):
            basis = 'per_year'
        elif re.search(r'\b(?:one[ -]time|year 1 only|first year only)\b', tail, re.I):
            basis = 'one_time'
        elif len(found) == 1 and re.search(r'\bone[ -]time\b', raw, re.I):
            basis = 'one_time'
        elif re.search(r'over (?:the course of )?(?:a )?(?:four[ -]year degree|\d+ years)|total', tail, re.I):
            basis = 'total_degree'
        elif index == 0 and re.search(r'scholarship total|maximum.*over.*years', header, re.I):
            basis = 'total_degree'
        value = claim(float(match[1].replace(',', '')), basis, raw,
                      maximum_only=bool(re.search(r'up to\s*(?:CAN\s*)?$', head, re.I)),
                      minimum_only=bool(re.search(r'from\s*$', head, re.I)))
        values.append(value)
    return distinct(values)

def explicit_currency(text):
    if re.search(r'\bCAD\b|Canadian dollars|CAN\s*\$', text, re.I):
        return 'CAD'
    if re.search(r'\bUSD\b|US\s*\$', text, re.I):
        return 'USD'
    return None

def text(tag):
    return re.sub(r'\s+', ' ', tag.get_text(' ', strip=True)).strip()

def now():
    return datetime.now(timezone.utc).isoformat()

def fetch_html(url, timeout=12):
    """HTTP status is independent of process success. Blocked pages yield no DOM."""
    if BROWSER_MODE == 'selenium':
        return fetch_selenium(url, timeout)
    metadata = {'requested_url': url, 'attempted_at': now(), 'attempts': [],
                'http_status': None, 'fetch_status': 'unavailable'}
    for client in ('requests', 'curl'):
        try:
            if client == 'requests':
                response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
                status, body, final_url = response.status_code, response.content, response.url
                content_type = response.headers.get('Content-Type', '')
            else:
                marker = b'\n__SCHOLARSHIP_HTTP_META__'
                response = subprocess.run([
                    'curl', '--silent', '--show-error', '--location', '--max-time', str(timeout),
                    '--proto', '=https', '--proto-redir', '=https', '-A', DEFAULT_HEADERS['User-Agent'],
                    '--write-out', '\n__SCHOLARSHIP_HTTP_META__%{http_code}\t%{url_effective}\t%{content_type}', url,
                ], capture_output=True, timeout=timeout + 2)
                if response.returncode:
                    raise OSError(f'curl exit {response.returncode}')
                body, trailer = response.stdout.rsplit(marker, 1)
                code, final_url, content_type = trailer.decode('utf-8').split('\t', 2)
                status = int(code)
            soup, error = validate_html(status, body, content_type)
            metadata.update(http_status=status, final_url=final_url, fetch_status=error or 'ok', transport=client)
            metadata['attempts'].append({'client': client, 'http_status': status, 'error': error, 'final_url': final_url})
            if soup is not None:
                metadata.update(fetched_at=now())
                return metadata, soup
        except (requests.RequestException, subprocess.TimeoutExpired, OSError, ValueError) as exc:
            metadata['attempts'].append({'client': client, 'error': str(exc)})
            metadata['fetch_status'] = 'network_error'
    if BROWSER_MODE == 'auto' and metadata['fetch_status'] in ('blocked', 'network_error', 'invalid_content', 'unexpected_content'):
        browser_metadata, soup = fetch_selenium(url, timeout)
        browser_metadata['attempts'] = metadata['attempts'] + browser_metadata['attempts']
        return browser_metadata, soup
    return metadata, None


def fetch_selenium(url, timeout=12):
    """Render JS; optionally retain a dedicated profile for manual verification."""
    metadata = {'requested_url': url, 'attempted_at': now(), 'attempts': [],
                'http_status': None, 'fetch_status': 'browser_error', 'transport': 'selenium'}
    try:
        from selenium import webdriver
        from selenium.common.exceptions import TimeoutException, WebDriverException
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError:
        metadata['error'] = 'Selenium is missing; install requirements.txt with this Python interpreter.'
        return metadata, None
    driver = None
    if BROWSER_PROFILE is not None:
        Path(BROWSER_PROFILE).mkdir(parents=True, exist_ok=True, mode=0o700)
    profile_context = (nullcontext(str(Path(BROWSER_PROFILE).resolve())) if BROWSER_PROFILE is not None
                       else tempfile.TemporaryDirectory(prefix='scholarship-browser-'))
    with profile_context as profile:
        try:
            options = webdriver.ChromeOptions()
            options.page_load_strategy = 'eager'
            if BROWSER_HEADLESS:
                options.add_argument('--headless=new')
            if getattr(os, 'geteuid', lambda: -1)() == 0 or Path('/.dockerenv').exists():
                options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1440,1000')
            options.add_argument(f'--user-data-dir={profile}')
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            # Selenium Manager shares a driver cache; serialize its startup in a batch run.
            with _BROWSER_START_LOCK:
                driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(timeout)
            try:
                driver.get(url)
            except TimeoutException:
                pass  # DOM may already be usable; still apply the bounded explicit wait.
            responses = {}
            challenge_announced = False
            def ready(browser):
                nonlocal challenge_announced
                # Log status for the main document, not for images, JS, or challenge iframes.
                frame_id = browser.execute_cdp_cmd('Page.getFrameTree', {})['frameTree']['frame']['id']
                for entry in browser.get_log('performance'):
                    event = json.loads(entry['message'])['message']
                    params = event.get('params', {})
                    if (event.get('method') == 'Network.responseReceived' and params.get('type') == 'Document'
                            and params.get('frameId') == frame_id):
                        response = params['response']
                        responses[response['url'].split('#', 1)[0]] = int(response['status'])
                final_url = browser.current_url
                status = responses.get(final_url.split('#', 1)[0])
                if status is None:
                    # Chrome exposes the navigation response too; zero means unknown.
                    status = browser.execute_script('return performance.getEntriesByType("navigation")[0]?.responseStatus || null')
                metadata.update(final_url=final_url, http_status=status)
                if status is None:
                    metadata['fetch_status'] = 'network_status_unavailable'
                    return False
                soup, error = validate_html(status, browser.page_source)
                metadata['fetch_status'] = error or 'ok'
                if error == 'blocked' and MANUAL_CHALLENGE_WAIT and not challenge_announced:
                    print(f'[ACTION] {url}: complete verification in the open Chrome window. '
                          f'Waiting up to {max(BROWSER_WAIT, MANUAL_CHALLENGE_WAIT):g}s; '
                          'do not close Chrome.', flush=True)
                    challenge_announced = True
                if soup is not None and browser.execute_script('return document.readyState') in ('interactive', 'complete'):
                    return soup
                return False
            try:
                soup = WebDriverWait(driver, max(BROWSER_WAIT, MANUAL_CHALLENGE_WAIT), poll_frequency=1).until(ready)
            except TimeoutException:
                metadata['attempts'].append({'client': 'selenium', 'http_status': metadata['http_status'],
                                             'error': metadata['fetch_status']})
                return metadata, None
            metadata['fetched_at'] = now()
            metadata['attempts'].append({'client': 'selenium', 'http_status': metadata['http_status'], 'error': None})
            return metadata, soup
        except (WebDriverException, OSError) as exc:
            metadata['fetch_status'] = 'browser_error'
            metadata['error'] = str(exc).splitlines()[0][:250]
            return metadata, None
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except WebDriverException:
                    pass


def clean(value):
    """Drop empty optional fields, preserving meaningful False and zero values."""
    if isinstance(value, dict):
        cleaned = {k: clean(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v is not None and v != '' and v != [] and v != {}}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def main_content(soup):
    soup = BeautifulSoup(str(soup), 'html.parser')
    for tag in soup.select('script, style, nav, footer, aside, form, blockquote, [role=navigation], .testimonial'):
        tag.decompose()
    return soup.find('main') or soup.find(id='content') or soup.find('article') or soup.body or soup


def text_blocks(root):
    tags = ['p', 'li', 'td', 'th', 'small', 'div', 'section']
    selected = set()
    result = []
    for tag in root.find_all(tags + ['sup']):
        if not tag.find(tags) and text(tag) and not any(id(p) in selected for p in tag.parents):
            result.append(tag)
            selected.add(id(tag))
    return result


def sections(soup, pattern):
    """Only sections explicitly selected by the school; include their subheadings."""
    root = main_content(soup)
    block_ids = {id(t) for t in text_blocks(root)}
    for heading in root.find_all(re.compile(r'^h[1-6]$')):
        name = text(heading)
        if not re.search(pattern, name, re.I):
            continue
        level, paragraphs = int(heading.name[1]), []
        for node in heading.next_elements:
            node_name = getattr(node, 'name', None)
            if node_name and re.fullmatch(r'h[1-6]', node_name):
                if int(node_name[1]) <= level:
                    break
                paragraphs.append(text(node))
            elif id(node) in block_ids:
                paragraphs.append(text(node))
        yield name, distinct(paragraphs)


def table_records(table):
    rows = [[text(c) for c in row.find_all(['td', 'th'], recursive=False)]
            for row in table.find_all('tr') if row.find_parent('table') is table]
    rows = [r for r in rows if r]
    if not rows:
        return []
    headers = rows[0]
    return [{key(h): row[i] if i < len(row) else '' for i, h in enumerate(headers)} for row in rows[1:]]


def values(raw, currency=None, header=''):
    return [clean({k: v for k, v in value.items() if k not in ('kind', 'evidence_text')})
            for value in money_values(raw, header, currency or explicit_currency(raw))]


def application_info(paragraphs):
    result = {}
    combined = ' '.join(paragraphs)
    if re.search(r'automatic scholarship|automatically (?:awarded|considered)|automatic consideration', combined, re.I):
        result['method'] = 'automatic'
    deadlines = []
    for paragraph in paragraphs:
        if re.search(r'deadline|apply by|application (?:is )?required by', paragraph, re.I) and not re.search(r'tuition|disbursement|SOLUS', paragraph, re.I):
            deadlines.extend(date_value(m[0]) for m in DATE.finditer(paragraph))
    result['deadlines'] = distinct(deadlines)
    return clean(result)


def award(name, paragraphs, **extra):
    """School-selected award text only; never scan all page dollars for a range."""
    paragraphs = distinct(paragraphs)
    value_texts = [p for p in paragraphs if MONEY.search(p) and re.search(
        r'^Value of award:|^\$|scholarship valued at|entrance scholarship of|could receive|receive up to|valued at', p, re.I)]
    criteria = [p for p in paragraphs if re.search(
        r'admission average|minimum|eligible|eligibility|full.time|study permit|citizen|resident|course load|GPA', p, re.I)
        and not re.search(r'number of awards|^to be eligible', p, re.I)]
    renewal_data = renewal(paragraphs)
    count = next((re.match(r'Number of awards:\s*(\d+|Unlimited)', p, re.I) for p in paragraphs if p.lower().startswith('number of awards:')), None)
    description = next((p for p in paragraphs if len(p) > 35 and p not in criteria and p not in value_texts
                        and re.search(r'\b(?:scholarship|bursary|award)\b', p, re.I)
                        and not re.search(r'notified|portal|email|refund|SOLUS', p, re.I)
                        and not p.lower().startswith(('number of awards:', 'frequency of the award:'))), None)
    return clean({'name': name, 'description': description, 'value_texts': value_texts,
                  'values': [v for p in value_texts for v in values(p)],
                  'eligibility': criteria, 'renewable': renewal_data['is_renewable'],
                  'renewal_conditions': renewal_data['conditions_text'],
                  'number_of_awards': int(count[1]) if count and count[1].isdigit() else None,
                  'unlimited_awards': True if count and count[1].lower() == 'unlimited' else None,
                  'application': application_info(paragraphs), **extra})


def selected_awards(soup, pattern, **extra):
    return [award(name, paragraphs, **extra) for name, paragraphs in sections(soup, pattern)]


def tier(grade_text, value_text, conditions=(), currency=None, header='', **extra):
    condition = grade(grade_text)
    state = renewal([grade_text, value_text, *conditions])
    return clean({'grade_text': grade_text,
                  'min_average': condition['min'], 'max_average': condition['max'],
                  'value_text': value_text, 'values': values(value_text, currency, header),
                  'renewable': state['is_renewable'], 'renewal_conditions': list(conditions), **extra})


def schedule_tables(soup, pattern):
    periods = []
    for table in main_content(soup).find_all('table'):
        heading = table.find_previous(re.compile(r'^h[1-6]$'))
        label = text(heading) if heading else ''
        if not re.search(pattern, label, re.I):
            continue
        for row in table_records(table):
            opening = row.get('application available') or row.get('application opens') or row.get('open')
            closing = row.get('deadline date') or row.get('application closes') or row.get('close deadline')
            if opening is None or closing is None:
                continue
            periods.append(clean({'group': label, 'term': row.get('semester') or row.get('ceremony') or row.get('term'),
                                  'opens': date_value(opening), 'deadline': date_value(closing),
                                  'results': row.get('results available') or row.get('notified of award')}))
    return periods


def export_school(crawler, metadata, extracted, output_dir=None):
    """Only the compact public fields are written; no raw DOM/debug/source copies."""
    document = clean({'schema_version': 4, 'school': {'name': crawler.name, 'slug': crawler.slug},
                      'source_url': metadata.get('final_url') or crawler.url,
                      'fetched_at': metadata.get('fetched_at') or metadata.get('attempted_at'),
                      'status': metadata['fetch_status'], 'http_status': metadata.get('http_status'),
                      'transport': metadata.get('transport'),
                      'data_status': 'needs_review' if metadata['fetch_status'] == 'ok' else 'unavailable'})
    document['scholarships'] = clean(extracted.get('scholarships', []))
    if extracted.get('application_periods'):
        document['application_periods'] = clean(extracted['application_periods'])
    notes = extracted.get('notes', []) + ([metadata['error']] if metadata.get('error') else [])
    if notes:
        document['notes'] = notes
    path = (Path(output_dir) if output_dir is not None else ROOT / 'outputs') / f'{crawler.slug}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        previous = json.loads(path.read_text(encoding='utf-8'))
        previous_slug = previous.get('school', {}).get('slug')
        if previous.get('schema_version') not in (3, 4) or previous_slug != crawler.slug:
            raise ValueError(f'{path}: not an output of this school')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=f'.{path.name}.', suffix='.tmp', delete=False) as handle:
            temporary = handle.name
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary:
            os.unlink(temporary)
    return document


def run_school(crawler):
    from run_all import main
    import sys
    return main(['--school', crawler.slug, *sys.argv[1:]])
