"""Brock University: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import clean, fetch_html, export_school, run_school, main_content, selected_awards, table_records, values


class Crawler:
    name = 'Brock University'
    slug = 'brock_university'
    url = 'https://brocku.ca/safa/2026-international-students/'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        scholarships, entrance_tiers = [], []
        for table in main_content(soup).find_all('table'):
            for row in table_records(table):
                band = next((v for k,v in row.items() if k.startswith('admission average')), None)
                if band:
                    entrance_tiers.append(clean({'grade_text': band,
                        'total_value_text': next((v for k,v in row.items() if k.startswith('amount of award')), None),
                        'year_1_value_text': row.get('year 1'), 'renewal_value_text': row.get('renewals')}))
                    continue
                name = next((v for k,v in row.items() if k.startswith('awards ')), None)
                if name:
                    scholarships.append(clean({'name': name, 'value_text': row.get('value'),
                                               'values': values(row.get('value', '')),
                                               'eligibility': row.get('application instructions')}))
        if entrance_tiers:
            scholarships.insert(0, {'name': 'International Brock Scholars Award', 'tiers': entrance_tiers})
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
