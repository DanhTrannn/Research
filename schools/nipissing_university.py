"""Nipissing University: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import text_blocks, text, fetch_html, export_school, run_school, main_content, table_records, clean


class Crawler:
    name = 'Nipissing University'
    slug = 'nipissing_university'
    url = 'https://www.nipissingu.ca/studentsupports/student-financial-services/student-awards-and-financial-aid/guaranteed-entrance-scholarships'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        scholarships = []
        for table in main_content(soup).find_all('table'):
            rows = table_records(table)
            if not rows or not any('scholarship average' in k for k in rows[0]):
                continue
            tiers = []
            for row in rows:
                band = next(v for k, v in row.items() if 'scholarship average' in k)
                tiers.append(clean({'grade_text': band, 'year_1': next((v for k,v in row.items() if k.startswith('year 1')), None),
                                    'total_value': next((v for k,v in row.items() if k.startswith('total scholarship value')), None),
                                    'renewal_average': row.get('renewable average')}))
            scholarships.append({'name': 'Guaranteed Entrance Scholarships', 'tiers': tiers,
                                 'notes': [text(p) for p in text_blocks(main_content(soup)) if re.search(r'free tuition|24 credits|renewal requirements', text(p), re.I)]})
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
