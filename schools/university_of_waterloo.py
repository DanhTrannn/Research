"""University of Waterloo: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import (award, clean, export_school, fetch_html, main_content, run_school,
                      scope_filter, sections, table_records, values)


class Crawler:
    name = 'University of Waterloo'
    slug = 'university_of_waterloo'
    url = 'https://uwaterloo.ca/future-students/financing/international-scholarships'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        scholarships = []

        # Main $10,000 International Student Entrance Scholarship.
        section = next(sections(soup, r'International Student Entrance Scholarship$'), None)
        if section is not None:
            name, paragraphs = section
            cut = next((index for index, paragraph in enumerate(paragraphs)
                        if re.search(r'^Questions about the scholarship', paragraph, re.I)),
                       len(paragraphs))
            item = award(name, paragraphs[:cut], type='scholarship',
                         applicant_category='international', international_eligible=True,
                         eligible_stages=['entrance'], application={'method': 'automatic'},
                         source_url=self.url)
            item['value_text'] = '$10,000 ($5,000 per term)'
            item['values'] = [
                clean({'min_amount': 10000, 'max_amount': 10000, 'payment_basis': 'per_year'}),
                clean({'min_amount': 5000, 'max_amount': 5000, 'payment_basis': 'per_term',
                       'max_payments': 2}),
            ]
            item['renewable'] = False
            scholarships.append(item)

        # Additional international scholarships table.
        for table in main_content(soup).find_all('table'):
            records = table_records(table)
            if not records or 'scholarship' not in records[0] or 'value' not in records[0]:
                continue
            for row in records:
                name = row.get('scholarship', '')
                if not name or 'Black students' in name:
                    continue
                value_text = row.get('value', '')
                item_values = values(value_text)
                if len(item_values) == 2 and re.search(r'\bto\b', value_text, re.I):
                    item_values = [clean({'min_amount': item_values[0].get('min_amount'),
                                          'max_amount': item_values[1].get('max_amount'),
                                          'payment_basis': 'unknown'})]
                application = row.get('application required?', row.get('application required', ''))
                item = clean({
                    'name': name,
                    'type': 'scholarship',
                    'applicant_category': 'international',
                    'international_eligible': True,
                    'eligible_stages': ['entrance'],
                    'programs': row.get('programs or eligibility'),
                    'value_text': value_text,
                    'values': item_values,
                    'application': {'method': 'automatic' if re.search(r'\bno\b', application, re.I)
                                    else 'application_required'},
                    'source_url': self.url,
                })
                if 'India' in name:
                    item['eligible_countries'] = ['India']
                scholarships.append(item)

        return {'scholarships': scope_filter(scholarships),
                'notes': ['Only the dedicated international scholarship page is used; '
                          'general faculty entrance scholarships not listed there are excluded. '
                          'The Black-student scholarship is excluded because it is not international-specific.']}

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
