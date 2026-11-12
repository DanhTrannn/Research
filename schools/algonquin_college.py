"""Algonquin College: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import fetch_html, export_school, run_school, main_content, table_records, clean, scope_filter

ENTRANCE = re.compile(
    r'\b(?:entering (?:level 0?1|first year)|level 0?1\b|'
    r'new (?:student|first-year)|incoming|entrance|grade 12|high school|'
    r'first year (?:full-time )?(?:international )?students?)\b',
    re.I,
)


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
                fund_type = row.get('fund type', '')
                eligibility = row.get('description', '')
                if 'scholarship' not in fund_type.lower():
                    continue
                if row.get('open to international', '').lower() != 'yes':
                    continue
                if not ENTRANCE.search(eligibility):
                    continue
                international_only = bool(re.search(r'\binternational (?:student|students)\b', eligibility, re.I))
                scholarships.append(clean({
                    'name': row['award name'],
                    'type': 'scholarship',
                    'applicant_category': 'international' if international_only else 'all',
                    'international_eligible': True,
                    'eligible_stages': ['entrance'],
                    'eligibility': eligibility,
                    'campus': row.get('campus'),
                    'terms': row.get('term'),
                    'application': {
                        'required_flag': {'yes': True, 'no': False}.get(row.get('application required', '').lower()),
                        'instructions': row.get('application form'),
                    },
                }))
        return {'scholarships': scope_filter(scholarships),
                'notes': ['Only international-eligible entrance scholarships are exported; '
                          'domestic-only, bursary, award and continuing rows are excluded.']}

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
