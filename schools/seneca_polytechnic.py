"""Seneca Polytechnic: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import (clean, distinct, explicit_currency, export_school,
                      fetch_html, main_content, run_school, text, values)


def extract_accordion_map(root):
    """Map normalized accordion header text to its panel container."""
    result = {}
    for item in root.find_all('div', class_='cmp-accordion__item'):
        button = item.find('button', class_='cmp-accordion__button')
        header = text(button) if button else text(item.find(['h2', 'h3', 'h4', 'span']))
        panel = item.find('div', class_='cmp-accordion__panel')
        if header and panel:
            result[header.strip().lower()] = panel
    return result


def extract_intro_paragraphs(root):
    """Extract introductory paragraphs before the accordion component."""
    paragraphs = []
    accordion = root.find('div', class_='cmp-accordion')
    for p in root.find_all('p'):
        if accordion and p.find_parent('div', class_='cmp-accordion'):
            continue
        content = text(p)
        if content and not any(skip in content.lower() for skip in ['quick links', 'find your program', 'campuses and locations']):
            paragraphs.append(content)
    return distinct(paragraphs)


def extract_intakes(paragraphs):
    """Find intake terms mentioned in paragraphs."""
    found = []
    pattern = re.compile(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b', re.I)
    for p in paragraphs:
        for match in pattern.findall(p):
            found.append(match)
    return distinct(found)


def extract_tiers(receive_panel, currency):
    """Extract tiered scholarship values based on program duration."""
    if not receive_panel:
        return []
    tiers = []
    tier_list = receive_panel.find('ul')
    if not tier_list:
        return []
    for li in tier_list.find_all('li', recursive=False):
        line = text(li)
        match = re.match(r'^(.*?)\s*-\s*\$([\d,]+(?:\.\d+)?)\s*(?:\((.*?)\))?$', line.strip())
        if not match:
            continue
        duration = match.group(1).strip()
        schedule = match.group(3).strip() if match.group(3) else None
        tier_text = f"${match.group(2)}" + (f" ({schedule})" if schedule else "")
        tier_data = {
            'program_duration': duration,
            'value_text': tier_text,
            'values': values(line, currency=currency),
            'disbursement_schedule': schedule,
        }
        tiers.append(clean(tier_data))
    return tiers


def extract_deadlines(receive_panel):
    """Extract deadlines for submitting SIN/ITN by intake term."""
    if not receive_panel:
        return []
    deadlines = []
    pattern = re.compile(r'^([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?)\s+for\s+(.*)$', re.I)
    for li in receive_panel.find_all('li'):
        line = text(li)
        match = pattern.search(line)
        if match:
            deadlines.append(clean({
                'date_text': match.group(1).strip(),
                'term': match.group(2).strip(),
                'raw': line,
            }))
    return distinct(deadlines)


def extract_eligibility(accordion_map):
    """Extract eligibility rules from relevant accordion panels."""
    eligibility = []
    for header, panel in accordion_map.items():
        if 'eligible' in header:
            for p in panel.find_all('p'):
                content = text(p)
                if content and not content.endswith(':') and 'pgwp' not in content.lower():
                    eligibility.append(content)
            for li in panel.find_all('li'):
                content = text(li)
                if content and content not in eligibility:
                    eligibility.append(content)
    return distinct(eligibility)


def extract_application_details(accordion_map):
    """Extract application method and required steps."""
    panel = next((p for h, p in accordion_map.items() if any(k in h for k in ['start', 'apply'])), None)
    steps = []
    method = 'automatic'
    if panel:
        for p in panel.find_all('p'):
            content = text(p)
            if 'automatically' in content.lower():
                method = 'automatic'
        for li in panel.find_all('li'):
            content = text(li)
            if content:
                steps.append(content)
    return method, distinct(steps)


def extract_payment_notes(receive_panel):
    """Extract disbursement, deposit, and refund rules."""
    if not receive_panel:
        return []
    notes = []
    keywords = ['deposited', 'non-refundable', 'overpayment', 'fees for the next semester']
    for p in receive_panel.find_all('p'):
        content = text(p)
        if any(kw in content.lower() for kw in keywords):
            notes.append(content)
    return distinct(notes)


def extract_policy_notes(accordion_map):
    """Extract deferral and award combination policies."""
    notes = []
    for header, panel in accordion_map.items():
        if any(k in header for k in ['combine', 'defer']):
            for p in panel.find_all('p'):
                content = text(p)
                if content and content not in notes:
                    notes.append(content)
    return distinct(notes)


class Crawler:
    name = 'Seneca Polytechnic'
    slug = 'seneca_polytechnic'
    url = 'https://www.senecapolytechnic.ca/international/entrance-scholarship-for-all-international-students.html'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        root = main_content(soup)
        h1 = root.find('h1')
        title = re.sub(r'\s*\*+$', '', text(h1)).strip() if h1 else 'International Entrance Scholarship'

        intro_paragraphs = extract_intro_paragraphs(root)
        currency = explicit_currency(' '.join(intro_paragraphs)) or 'CAD'

        value_text = None
        for p in intro_paragraphs:
            match = re.search(r'up to\s*\$[\d,]+', p, re.I)
            if match:
                value_text = match.group(0)
                break
        if not value_text and h1:
            match = re.search(r'up to\s*\$[\d,]+', text(h1), re.I)
            if match:
                value_text = match.group(0)

        intakes = extract_intakes(intro_paragraphs)
        accordion_map = extract_accordion_map(root)
        receive_panel = next((p for h, p in accordion_map.items() if 'receive' in h), None)

        tiers = extract_tiers(receive_panel, currency)
        deadlines = extract_deadlines(receive_panel)
        eligibility = extract_eligibility(accordion_map)
        app_method, app_steps = extract_application_details(accordion_map)
        payment_notes = extract_payment_notes(receive_panel)
        policy_notes = extract_policy_notes(accordion_map)

        emails = distinct(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text(root)))

        scholarship = clean({
            'name': title,
            'type': 'scholarship',
            'applicant_category': 'international',
            'eligible_stages': ['entrance'],
            'value_text': value_text,
            'values': values(value_text, currency=currency) if value_text else None,
            'intakes': intakes,
            'tiers': tiers,
            'eligibility': eligibility,
            'payment_notes': payment_notes,
            'notes': policy_notes,
            'application': clean({
                'method': app_method,
                'steps': app_steps,
                'deadlines': deadlines,
                'contact_emails': emails if emails else None,
            }),
        })

        return {'scholarships': [scholarship] if scholarship.get('name') else []}

    def export(self, metadata, data, output_dir=None):
        return export_school(self, metadata, data, output_dir)

    def run(self, output_dir=None, timeout=12):
        metadata, soup = self.crawl(timeout)
        data = {'scholarships': []}
        if soup is not None:
            try:
                data = self.extract(soup)
                if not data.get('scholarships'):
                    metadata['fetch_status'] = 'no_data'
            except Exception as exc:
                metadata['fetch_status'] = 'extraction_error'
                data = {'scholarships': [], 'notes': [str(exc)]}
        return self.export(metadata, data, output_dir)


if __name__ == '__main__':
    raise SystemExit(run_school(Crawler()))
