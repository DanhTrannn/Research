"""Fleming College: crawl -> extract current international entry award -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import clean, fetch_html, export_school, run_school, main_content, text, values


class Crawler:
    name = 'Fleming College'
    slug = 'fleming_college'
    url = 'https://flemingcollege.ca/scholarships-for-international-students'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        root = main_content(soup)
        heading = next((h for h in root.find_all(['h2', 'h3'])
                        if text(h) == 'Scholarships for International Students'), None)
        if heading is None:
            return {'scholarships': []}
        # BeautifulSoup's tag traversal excludes the retired awards inside HTML comments.
        paragraphs = [text(p) for p in heading.parent.find_all('p')]
        intro = next((p for p in paragraphs if 'receive an Entry Scholarship' in p), '')
        amount = re.search(r'up to\s*\$[\d,]+(?:\.\d+)?', intro, re.I)
        if not amount:
            return {'scholarships': []}
        credentials = re.search(r'applying to a Fleming (.+?) program for', intro)
        programs = re.split(r',\s*(?:or\s+)?|\s+or\s+', credentials[1]) if credentials else []
        intakes = re.findall(r'\b(?:Fall|Winter|Summer|Spring)\s+\d{4}\b', intro)
        once = any('receive this award only once' in p for p in paragraphs)
        amounts = values(amount[0])
        if once:
            for value in amounts:
                value['payment_basis'] = 'one_time'
        sentences = [s for p in paragraphs for s in re.split(r'(?<=[.!?])\s+', p)]
        contact = next((a['href'][7:].split('?', 1)[0] for a in heading.parent.select('a[href^="mailto:"]')), None)
        return {'scholarships': [clean({
            'name': 'Entry Scholarship', 'type': 'scholarship',
            'applicant_category': 'international', 'eligible_stages': ['entrance'],
            'programs': programs, 'intakes': intakes,
            'value_text': amount[0], 'values': amounts,
            'renewable': False if once else None,
            'eligibility': [s for s in sentences if 'only once' in s or 'confirmation letter' in s],
            'availability': next((p for p in paragraphs if 'based on availability' in p), None),
            'payment_notes': [s for s in sentences if 'deposited directly' in s],
            'application': {'contact_email': contact},
        })]}

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
