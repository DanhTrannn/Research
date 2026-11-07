"""Fanshawe College: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from urllib.parse import urljoin
from pipeline import (MONTHS, MONEY, clean, distinct, export_school, fetch_html,
                      main_content, run_school, table_records, text, values)

INTAKE = re.compile(r'\b(?:' + MONTHS + r')\.?\s+20\d{2}\b', re.I)
SCENARIO_LABEL = re.compile(r'^(.*?)\s*\$')
SCENARIO_TOTAL = re.compile(r'\(\s*\$([\d,]+(?:\.\d+)?)\s*total\s*\)', re.I)


def scholarship_details(root):
    """Only the three scholarship accordions before the FAQ heading."""
    heading = next((h for h in root.find_all('h2')
                    if text(h) == 'Scholarship Opportunities for New Students!'), None)
    if heading is None:
        return []
    result = []
    for sibling in heading.next_siblings:
        name = getattr(sibling, 'name', None)
        if name == 'h2':
            break
        if name == 'details' and sibling.summary:
            result.append(sibling)
    return result


def list_item_text(item):
    """Text belonging to one list item, excluding its nested lists."""
    parts = []
    for child in item.children:
        if getattr(child, 'name', None) in ('ul', 'ol'):
            continue
        parts.append(text(child) if getattr(child, 'name', None) else str(child))
    return re.sub(r'\s+', ' ', ' '.join(parts)).strip()


def list_items(node):
    """Direct list items plus their nested sub-items, without duplicating parent text."""
    result = []
    for item in node.find_all('li', recursive=False):
        value = list_item_text(item)
        if value:
            result.append(value)
        for nested in item.find_all(['ul', 'ol'], recursive=False):
            result.extend(list_items(nested))
    return result


def details_sections(details):
    """Map each h3 in an accordion to its paragraphs, bullets, and tables."""
    wrapper = details.find('div', class_='details-wrapper') or details
    result = {}
    current = None
    for child in wrapper.children:
        name = getattr(child, 'name', None)
        if name == 'h3':
            title = text(child)
            current = (result.setdefault(title, {'paragraphs': [], 'bullets': [], 'tables': []})
                       if title else None)
        elif current is None:
            continue
        elif name == 'p':
            value = text(child)
            if value:
                current['paragraphs'].append(value)
        elif name in ('ul', 'ol'):
            current['bullets'].extend(list_items(child))
        elif name == 'table':
            records = table_records(child)
            if records:
                current['tables'].append(records)
    for section in result.values():
        section['bullets'] = distinct(section['bullets'])
        section['paragraphs'] = distinct(section['paragraphs'])
    return result


def section_bullets(sections, title):
    return sections.get(title, {}).get('bullets', [])


def section_paragraphs(sections, title):
    return sections.get(title, {}).get('paragraphs', [])


def first_paragraph(sections, title, skip=()):
    for paragraph in section_paragraphs(sections, title):
        if any(paragraph.lower().startswith(prefix.lower()) for prefix in skip):
            continue
        return paragraph
    return None


def intake_terms(details):
    return distinct(match.group(0).replace('.', '') for match in INTAKE.finditer(text(details)))


def application_form(details, page_url):
    for anchor in details.find_all('a', href=True):
        href = anchor['href']
        if href.lower().endswith('.pdf') and re.search(r'application form', text(anchor), re.I):
            return urljoin(page_url, href)
    for anchor in details.find_all('a', href=True):
        if anchor['href'].lower().endswith('.pdf'):
            return urljoin(page_url, anchor['href'])
    return None


def spousal_application(sections, details, page_url):
    return clean({
        'method': 'application_required',
        'url': application_form(details, page_url),
        'documents': [
            'Marriage certificate or Statutory Declaration of Common-Law Union',
            'Spousal Scholarship application form',
        ],
        'notes': section_bullets(sections, 'Application Process'),
    })


def academic_tiers(sections):
    tiers = []
    tables = sections.get('Scholarship Amount', {}).get('tables', [])
    for records in tables:
        for row in records:
            program_type = row.get('program type')
            value_text = row.get('scholarship amount')
            if not program_type or not value_text:
                continue
            if re.search(r'\bup to\b', value_text, re.I):
                match = MONEY.search(value_text)
                tier_values = ([{'max_amount': float(match[1].replace(',', '')),
                                 'payment_basis': 'unknown'}]
                               if match else [])
            else:
                tier_values = values(value_text)
            tiers.append(clean({'program_type': program_type,
                                'value_text': value_text,
                                'values': tier_values}))
    return tiers


def academic_scholarship(details, page_url):
    sections = details_sections(details)
    overview = section_paragraphs(sections, 'Overview')
    overview_bullets = section_bullets(sections, 'Overview')
    process = section_bullets(sections, 'Scholarship Application & Award Process')
    payment_notes = [bullet for bullet in overview_bullets
                     if re.search(r'tuition|deposit|term 1', bullet, re.I)]
    payment_notes += [bullet for bullet in process
                      if re.search(r'tuition|deducted|web-advisor', bullet, re.I)]
    application_notes = [bullet for bullet in process
                         if not re.search(r'tuition|deducted|web-advisor', bullet, re.I)]
    notes = [bullet for bullet in overview_bullets if re.search(r'online', bullet, re.I)]
    notes.append('The Combined Admission amount is up to $2,500 (EAP $500 + PS $2,000); '
                 'it is a combined total, not an additional award.')
    return clean({
        'name': text(details.summary),
        'type': 'scholarship',
        'applicant_category': 'international',
        'eligible_stages': ['entrance'],
        'tiers': academic_tiers(sections),
        'description': first_paragraph(sections, 'Overview'),
        'eligibility': section_bullets(sections, 'Eligibility Criteria'),
        'intakes': intake_terms(details),
        'payment_notes': distinct(payment_notes),
        'notes': distinct(notes),
        'application': {'method': 'automatic', 'notes': application_notes},
    })


def spousal_one_year(details, page_url):
    sections = details_sections(details)
    overview = section_paragraphs(sections, 'Overview')
    value_text = next((paragraph for paragraph in overview
                       if re.match(r'^Maximum\s*:', paragraph, re.I)), None)
    amount = MONEY.search(value_text) if value_text else None
    item_values = ([clean({'currency': 'CAD',
                           'max_amount': float(amount[1].replace(',', '')),
                           'payment_basis': 'unknown'})]
                   if amount else [])
    amount_bullets = section_bullets(sections, 'Scholarship Amount')
    eligibility = section_bullets(sections, 'Eligibility Criteria')
    eligibility += [paragraph for paragraph in overview
                    if re.match(r'^Note\s*:', paragraph, re.I)]
    return clean({
        'name': text(details.summary),
        'type': 'scholarship',
        'applicant_category': 'international',
        'eligible_stages': ['entrance'],
        'program_duration': '1 year',
        'value_text': value_text,
        'values': item_values,
        'description': first_paragraph(sections, 'Overview', skip=('Maximum:', 'Note:')),
        'eligible_regions': first_paragraph(sections, 'Eligible Regions'),
        'eligibility': eligibility,
        'conditions': [bullet for bullet in amount_bullets
                       if re.search(r'not be eligible|may still qualify', bullet, re.I)],
        'intakes': intake_terms(details),
        'payment_notes': [bullet for bullet in amount_bullets
                          if re.search(r'applied|tuition|deposit|web-advisor', bullet, re.I)],
        'withdrawal_policy': section_bullets(sections, 'Withdrawal & Refund Policy'),
        'application': spousal_application(sections, details, page_url),
    })


def spousal_two_year_tiers(sections):
    tiers = []
    for records in sections.get('Overview', {}).get('tables', []):
        for row in records:
            for cell in row.values():
                if not cell:
                    continue
                scenario = SCENARIO_LABEL.match(cell)
                label = scenario[1].strip() if scenario else None
                per_term = MONEY.search(cell)
                amount = float(per_term[1].replace(',', '')) if per_term else None
                total = SCENARIO_TOTAL.search(cell)
                total_amount = float(total[1].replace(',', '')) if total else None
                if amount is None:
                    tier_values = values(cell, 'CAD')
                elif re.search(r'term 1 and term 2', cell, re.I):
                    tier_values = [
                        {'currency': 'CAD', 'min_amount': amount, 'max_amount': amount,
                         'payment_basis': 'per_term', 'max_payments': 2},
                        {'currency': 'CAD', 'min_amount': total_amount,
                         'max_amount': total_amount, 'payment_basis': 'total_degree'},
                    ]
                elif re.search(r'term 1 only', cell, re.I):
                    tier_values = [{'currency': 'CAD', 'min_amount': amount,
                                    'max_amount': amount, 'payment_basis': 'one_time'}]
                else:
                    tier_values = values(cell, 'CAD')
                tiers.append(clean({'scenario': label,
                                    'value_text': cell,
                                    'values': tier_values}))
    return tiers


def spousal_two_year(details, page_url):
    sections = details_sections(details)
    conditions = section_bullets(sections, 'Conditions')
    return clean({
        'name': text(details.summary),
        'type': 'scholarship',
        'applicant_category': 'international',
        'eligible_stages': ['entrance'],
        'program_duration': '2 years',
        'tiers': spousal_two_year_tiers(sections),
        'description': first_paragraph(sections, 'Overview'),
        'eligible_regions': first_paragraph(sections, 'Eligible Regions'),
        'eligibility': section_bullets(sections, 'Eligibility Criteria'),
        'conditions': conditions,
        'intakes': intake_terms(details),
        'payment_notes': [bullet for bullet in conditions
                          if re.search(r'automatic|applied|web-advisor', bullet, re.I)],
        'withdrawal_policy': section_bullets(sections, 'Withdrawal & Refund Policy'),
        'notes': ['Scenario 1 and Scenario 2 are alternatives; their values are not cumulative.'],
        'application': spousal_application(sections, details, page_url),
    })


class Crawler:
    name = 'Fanshawe College'
    slug = 'fanshawe_college'
    url = ('https://www.fanshawec.ca/international/applicants/'
           'international-entrance-scholarships/academic-entrance-scholarships')

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        root = main_content(soup)
        scholarships = []
        for details in scholarship_details(root):
            name = text(details.summary).lower()
            if 'academic entrance' in name:
                scholarships.append(academic_scholarship(details, self.url))
            elif 'spousal' in name and '1 year' in name:
                scholarships.append(spousal_one_year(details, self.url))
            elif 'spousal' in name and ('2-year' in name or '2 year' in name):
                scholarships.append(spousal_two_year(details, self.url))
        notes = [
            'The page lists eligible start intakes, not application deadlines; '
            'no exact application deadline is published.',
            'Scholarship amounts are applied to tuition accounts; they are not cash payments.',
        ]
        return clean({'scholarships': scholarships, 'notes': notes})

    def export(self, metadata, data, output_dir=None):
        return export_school(self, metadata, data, output_dir)

    def run(self, output_dir=None, timeout=12):
        metadata, soup = self.crawl(timeout)
        data = {'scholarships': []}
        if soup is not None:
            try:
                data = self.extract(soup)
                if not data.get('scholarships') and not data.get('application_periods'):
                    metadata['fetch_status'] = 'no_data'
            except Exception as exc:
                metadata['fetch_status'] = 'extraction_error'
                data = {'scholarships': [], 'notes': [str(exc)]}
        return self.export(metadata, data, output_dir)


if __name__ == '__main__':
    raise SystemExit(run_school(Crawler()))
