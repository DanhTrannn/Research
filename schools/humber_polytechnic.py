"""Humber Polytechnic: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import fetch_html, export_school, run_school, main_content, selected_awards, table_records, schedule_tables, tier, text, renewal, application_info


class Crawler:
    name = 'Humber Polytechnic'
    slug = 'humber_polytechnic'
    url = 'https://humber.ca/study-at-humber/pay-fees/scholarships-bursaries'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        # Only grade/amount tables and two named bursaries; omit FAQ and fee tables.
        scholarships = []
        root = main_content(soup)
        conditions = [text(p) for p in root.find_all('p') if re.search(r'renewable each year.*maintain', text(p), re.I)]
        for table in root.find_all('table'):
            rows = table_records(table)
            if not rows or set(rows[0]) != {'average', 'amount'}:
                continue
            heading = table.find_previous(re.compile(r'^h[1-6]$'))
            name = text(heading) if heading else 'Degree entrance scholarships'
            introduction = table.find_previous('p')
            scholarships.append({'name': name, 'type': 'scholarship',
                                 'application': application_info([text(introduction)]) if introduction else {},
                                 'tiers': [tier(row['average'], row['amount'],
                                                conditions if renewal([row['amount']])['is_renewable'] is True else ())
                                           for row in rows]})
        scholarships += selected_awards(soup, r'^(Students In and From Care .* Bursary|Global Learning Bursary)$', type='bursary')
        return {'scholarships': scholarships, 'application_periods': schedule_tables(soup, r'.*')}

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
