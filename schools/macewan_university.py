"""MacEwan University: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
import requests
from pipeline import (DEFAULT_HEADERS, MONEY, award, clean, date_value, distinct,
                      export_school, fetch_html, grade, main_content, run_school,
                      scope_filter, sections, text)

SERIES_PATTERN = r'^International.*Chancellor.s Scholarship Series'
DETAIL_URL = 'https://www.macewan.ca/data/psft/sab/{}.json'


def fetch_json(url, timeout=12):
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.json()


def sabid_from_url(href):
    match = re.search(r'[?&]sabid=([^&]+)', href, re.I)
    if not match:
        return None
    value = match[1].strip()
    if value.lower().startswith('sab_'):
        value = value[4:]
    return value or None


def detail_url(sabid):
    return DETAIL_URL.format(sabid)


def series_headings(root):
    return [heading for heading in root.find_all('h2')
            if re.search(SERIES_PATTERN, text(heading), re.I)]


def degree_row(heading):
    """The first Degree programs card row that belongs to this series heading."""
    for row in heading.find_all_next('div', class_='row-padded'):
        if row.find_previous('h2') is not heading:
            break
        header = row.find('h4')
        if header is not None and text(header) == 'Degree programs':
            return row
    return None


def card_data(card):
    name_tag = card.find('p', class_='highlight')
    grade_tag = card.find('h5')
    if name_tag is None or grade_tag is None:
        return None
    links = {}
    for anchor in card.find_all('a', href=True):
        term = text(anchor).title()
        if term not in ('Fall', 'Winter'):
            continue
        sabid = sabid_from_url(anchor['href'])
        if sabid:
            links[term] = sabid
    return {'name': text(name_tag), 'grade_text': text(grade_tag), 'links': links}


def fetch_details(cards, timeout):
    details = {}
    errors = 0
    sabids = distinct(sabid for card in cards for sabid in card['links'].values())
    for sabid in sabids:
        try:
            details[sabid] = fetch_json(detail_url(sabid), timeout)
        except Exception:
            errors += 1
    return details, errors


def amount_from(detail):
    if not detail:
        return None
    award_data = detail.get('award') or {}
    amount = award_data.get('award-amount')
    if amount is None:
        match = MONEY.search(award_data.get('award-amount-description') or '')
        amount = float(match[1].replace(',', '')) if match else None
    return float(amount) if amount is not None else None


def grade_band(value):
    """Read the percentage range even when AGPA wording follows it."""
    match = re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%', value)
    if not match:
        return None, None
    return float(match[1]), float(match[2])


def build_tier(card, details, renewal):
    values = []
    for term in ('Fall', 'Winter'):
        sabid = card['links'].get(term)
        amount = amount_from(details.get(sabid)) if sabid else None
        if amount is None:
            continue
        values.append(clean({'term': term, 'min_amount': amount, 'max_amount': amount,
                             'payment_basis': 'one_time'}))
    parsed = grade(card['grade_text'])
    band_min, band_max = grade_band(card['grade_text'])
    min_average = parsed.get('min') or band_min
    max_average = parsed.get('max') or band_max
    if min_average is None:
        fall_detail = details.get(card['links'].get('Fall')) or details.get(card['links'].get('Winter'))
        detail_min = ((fall_detail or {}).get('award') or {}).get('min-highschool-average')
        min_average = float(detail_min) if detail_min is not None else None
    tier = clean({
        'name': card['name'],
        'grade_text': card['grade_text'],
        'min_average': min_average,
        'max_average': max_average,
        'values': values,
        'value_text': '; '.join(f'{value["term"]}: ${value["max_amount"]:,.0f}'
                                for value in values) or None,
    })
    if renewal and 'chancellor' in card['name'].lower():
        tier['renewable'] = True
        tier['renewal_conditions'] = renewal
    return tier


def clean_eligibility(paragraphs):
    result = []
    for paragraph in paragraphs:
        value = paragraph.strip()
        if not value:
            continue
        if value.lower().startswith('awarded to '):
            continue
        if re.fullmatch(r'(?:Chancellor|President|Provost|Dean)[’\']?s? Scholarship', value, re.I):
            continue
        if re.fullmatch(r'\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?%?(?:\s*or AGPA.*)?',
                        value, re.I):
            continue
        if re.search(r'\bcontinuing\b|automatically renewed', value, re.I):
            continue
        result.append(value)
    return distinct(result)


def deadlines_from(paragraphs):
    deadlines = []
    for paragraph in paragraphs:
        match = re.match(r'^(Fall|Winter)\s*[-–]\s*(.+)$', paragraph)
        if match:
            deadlines.append({'term': match[1], **date_value(match[2])})
    return deadlines


class Crawler:
    name = 'MacEwan University'
    slug = 'macewan_university'
    url = ('https://www.macewan.ca/apply-enrol/fees-finances/'
           'scholarships-awards-bursaries/entrance-scholarships/')

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup, timeout=12):
        root = main_content(soup)
        paragraphs_by_name = dict(sections(soup, SERIES_PATTERN))
        scholarships = []
        errors = 0
        for heading in series_headings(root):
            name = text(heading)
            paragraphs = paragraphs_by_name.get(name, [])
            category = 'international' if 'international' in name.lower() else 'domestic'
            base = award(name, paragraphs, type='scholarship_series',
                         applicant_category=category)
            renewal = [paragraph for paragraph in base.get('renewal_conditions', [])
                       if re.search(r'automatically renewed', paragraph, re.I)]
            row = degree_row(heading)
            cards = [card for card in (card_data(card) for card in
                                       row.select('div.textflow-block.col-md-3'))
                     if card] if row is not None else []
            details, series_errors = fetch_details(cards, timeout)
            errors += series_errors
            scholarships.append(clean({
                'name': name,
                'type': 'scholarship_series',
                'applicant_category': category,
                'eligible_stages': ['entrance'],
                'description': text(heading.find_next_sibling('p')) or base.get('description'),
                'eligibility': clean_eligibility(base.get('eligibility', [])),
                'tiers': [build_tier(card, details, renewal) for card in cards],
                'intakes': ['Fall', 'Winter'],
                'payment_notes': distinct(paragraph for paragraph in paragraphs
                                          if re.search(r'\bdisbursed\b', paragraph, re.I)),
                'application': {
                    'method': 'automatic',
                    'deadlines': deadlines_from(paragraphs),
                    'notes': ['Automatically considered when you apply for admission by the '
                              'scholarship deadline and are offered admission.'],
                },
            }))
        notes = [
            "The entrance page lists grade tiers and deadlines; dollar amounts are read from "
            "MacEwan's linked award detail data.",
            'Fall and Winter entrance awards are separate intake amounts; do not add them.',
            'Award values are subject to change and are not guaranteed.',
            'Continuing scholarships are outside this entrance-scholarship output.',
        ]
        if errors:
            notes.append('Some award detail records could not be read; amounts may be incomplete.')
        notes.append('Only the International Chancellor\'s Scholarship Series is exported; '
                     'the domestic series is out of scope.')
        return clean({'scholarships': scope_filter(scholarships), 'notes': notes})

    def export(self, metadata, data, output_dir=None):
        return export_school(self, metadata, data, output_dir)

    def run(self, output_dir=None, timeout=12):
        metadata, soup = self.crawl(timeout)
        data = {'scholarships': []}
        if soup is not None:
            try:
                data = self.extract(soup, timeout)
                if not data.get('scholarships') and not data.get('application_periods'):
                    metadata['fetch_status'] = 'no_data'
            except Exception as exc:
                metadata['fetch_status'] = 'extraction_error'
                data = {'scholarships': [], 'notes': [str(exc)]}
        return self.export(metadata, data, output_dir)


if __name__ == '__main__':
    raise SystemExit(run_school(Crawler()))
