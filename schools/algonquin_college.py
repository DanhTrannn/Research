"""Algonquin College: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import fetch_html, export_school, run_school, main_content, table_records, clean


class Crawler:
    name = 'Algonquin College'
    slug = 'algonquin_college'
    url = 'https://www.algonquincollege.com/financial-aid/awards-bursaries-scholarships/'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        scholarships = []
        for table in main_content(soup).find_all('table'):
            for row in table_records(table):
                if not row.get('award name'):
                    continue
                scholarships.append(clean({'name': row['award name'], 'type': row.get('fund type'),
                    'eligibility': row.get('description'), 'campus': row.get('campus'),
                    'international_eligible': {'yes': True, 'no': False}.get(row.get('open to international', '').lower()),
                    'terms': row.get('term'),
                    'application': {'required_flag': {'yes': True, 'no': False}.get(row.get('application required', '').lower()),
                                    'instructions': row.get('application form')}}))
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
