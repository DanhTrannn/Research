"""MacEwan University: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import fetch_html, export_school, run_school, sections, award, date_value


class Crawler:
    name = 'MacEwan University'
    slug = 'macewan_university'
    url = 'https://www.macewan.ca/apply-enrol/fees-finances/scholarships-awards-bursaries/entrance-scholarships/'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        scholarships = []
        for name, paragraphs in sections(soup, r'^(Canadian/domestic|International).*Chancellor.s Scholarship Series'):
            item = award(name, paragraphs, type='scholarship_series',
                         applicant_category='international' if name.startswith('International') else 'domestic')
            # A Chancellor's renewal rule must not become a series-wide boolean.
            item.pop('renewable', None)
            item['tiers'] = [{'grade_text': p} for p in paragraphs if re.match(r'^\d+(?:\.\d+)?\s*[-–]', p)]
            deadlines = []
            for paragraph in paragraphs:
                match = re.match(r'^(Fall|Winter)\s*[-–]\s*(.+)$', paragraph)
                if match:
                    deadlines.append({'term': match[1], **date_value(match[2])})
            if deadlines:
                item.setdefault('application', {})['deadlines'] = deadlines
            scholarships.append(item)
        return {'scholarships': scholarships}

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
