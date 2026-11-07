"""Confederation College: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from urllib.parse import urljoin
from pipeline import (DATE, MONEY, clean, date_value, export_school, fetch_html,
                      main_content, run_school, text, values)

TYPE_LABELS = {'scholarship', 'bursary', 'grant', 'award'}
STATUS_LABELS = {'open', 'closed', 'upcoming', 'coming soon'}


def scholarship_cards(root):
    """Find award cards by their type badge, never the page-level section heading."""
    cards = []
    seen = set()
    for badge in root.find_all('span'):
        if text(badge).lower() not in TYPE_LABELS:
            continue
        node = badge
        card = None
        for _ in range(5):
            node = node.parent
            if node is None or node.name in ('main', 'body', 'html'):
                break
            if node.name != 'div':
                continue
            heading = node.find(['h2', 'h3'])
            if heading is not None and re.search(r'\bDeadline\s*:', text(node), re.I):
                card = node
                break
        if card is None or id(card) in seen:
            continue
        seen.add(id(card))
        cards.append((card.find(['h2', 'h3']), card))
    return cards


def card_labels(card):
    return [text(span) for span in card.find_all('span') if text(span)]


def card_value_text(card):
    # Prefer the amount line that is a direct child of the card.
    candidates = [text(div) for div in card.find_all('div', recursive=False)]
    candidates += [text(div) for div in card.find_all('div')]
    for value in candidates:
        if MONEY.search(value) and 'deadline' not in value.lower():
            return value
    return None


def card_deadline_text(card):
    for div in card.find_all('div', recursive=False):
        match = re.match(r'^Deadline\s*:\s*(.+)$', text(div), re.I)
        if match:
            return match[1].strip()
    match = re.search(r'\bDeadline\s*:\s*(\S.*)$', text(card), re.I)
    return match[1].strip() if match else None


def card_description(card):
    paragraphs = [text(p) for p in card.select('details p')]
    if not paragraphs:
        paragraphs = [text(p) for p in card.find_all('p')]
    description = re.sub(r'\s+([.,;:!?])', r'\1', ' '.join(paragraphs))
    return re.sub(r'\s+', ' ', description).strip() or None


def card_application(card, page_url, status, deadline):
    link = next((anchor for anchor in card.find_all('a', href=True)
                 if re.search(r'\bapply\b|learn more', text(anchor), re.I)), None)
    application = {'method': 'application_required'}
    if link:
        application['url'] = urljoin(page_url, link['href'])
    if status:
        application['status'] = status
    if deadline:
        application['deadlines'] = [date_value(deadline)]
    return application


class Crawler:
    name = 'Confederation College'
    slug = 'confederation_college'
    url = 'https://www.confederationcollege.ca/international-education/scholarships/'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        root = main_content(soup)
        scholarships = []
        for heading, card in scholarship_cards(root):
            labels = card_labels(card)
            lowered = [label.lower() for label in labels]
            status = next((label for label in lowered if label in STATUS_LABELS), None)
            item_type = next((label for label in lowered if label in TYPE_LABELS), None)
            funding = next((label for label in lowered if label in {'internal', 'external'}), None)
            audience = next((label for label in labels
                             if re.search(r'\b(?:international|domestic)\b', label, re.I)), None)
            applicant_category = None
            if audience:
                applicant_category = ('international' if 'international' in audience.lower()
                                      else 'domestic')
            value_text = card_value_text(card)
            deadline_text = card_deadline_text(card)
            card_text = text(card)
            scholarships.append(clean({
                'name': text(heading),
                'type': item_type,
                'applicant_category': applicant_category,
                'funding_source': funding,
                'eligible_stages': ['entrance'] if re.search(r'\bentrance award\b', card_text, re.I) else None,
                'value_text': value_text,
                'values': values(value_text) if value_text else [],
                'description': card_description(card),
                'application': card_application(card, self.url, status, deadline_text),
            }))

        page_deadline_text = None
        for paragraph in root.find_all('p'):
            match = re.match(r'^Application deadline\s*:\s*(.+)$', text(paragraph), re.I)
            if match:
                page_deadline_text = match[1].strip()
                break

        periods = []
        notes = []
        if page_deadline_text:
            parsed = DATE.search(page_deadline_text)
            term = f'{parsed[1]} {parsed[3]}' if parsed and parsed[3] else None
            periods.append(clean({
                'group': 'International Awards for New Students',
                'term': term,
                'deadline': date_value(page_deadline_text),
            }))
            if any('exact date to be confirmed' in
                   (item.get('application', {}).get('deadlines', [{}])[0].get('raw', ''))
                   for item in scholarships):
                notes.append(f'Award cards list {term or "the published intake"} with the exact '
                             f'date to be confirmed; the page-level application deadline is '
                             f'{page_deadline_text}.')
        return clean({'scholarships': scholarships, 'application_periods': periods, 'notes': notes})

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
