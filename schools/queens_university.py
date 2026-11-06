"""Queen's University: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import fetch_html, export_school, run_school, sections


class Crawler:
    name = "Queen's University"
    slug = 'queens_university'
    url = 'https://www.queensu.ca/registrar/financial-aid'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        scholarships = []
        for name, paragraphs in sections(soup, r'^Queen.s General Bursary$'):
            scholarships.append({'name': name, 'type': 'bursary',
                                 'payment_notes': [p for p in paragraphs if re.search(r'disbursement|late December|course load', p, re.I)]})
        return {'scholarships': scholarships,
                'notes': ['Financial aid overview: payment dates are not scholarship application deadlines. No award amount was established on this page.']}

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
