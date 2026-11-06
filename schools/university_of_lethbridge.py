"""University of Lethbridge: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import fetch_html, export_school, run_school, main_content, table_records, tier, date_value, clean


class Crawler:
    name = 'University of Lethbridge'
    slug = 'university_of_lethbridge'
    url = 'https://www.ulethbridge.ca/ross/student-finance/awards'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        scholarships = []
        for table in main_content(soup).find_all('table'):
            for row in table_records(table):
                description = row.get('type of award')
                if not description:
                    continue
                name = re.split(r'Calculated using|Applied for admission|Requirements vary', description)[0].strip(' -')
                item = {'name': name, 'type': 'award_group', 'eligibility': description,
                        'application': {'opens': date_value(row.get('application opens', '')),
                                        'deadline': date_value(row.get('application closes', ''))},
                        'results': row.get('notified of award')}
                if name.startswith('Grade 11 Merit'):
                    item['tiers'] = []
                    for match in re.finditer(r'(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?%)\s*(and higher)?\s*-\s*(\$[\d,]+)', description):
                        band = match[1] + ('+' if match[2] else '')
                        item['tiers'].append(tier(band, match[3]))
                scholarships.append(clean(item))
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
