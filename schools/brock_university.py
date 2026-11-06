"""Brock University: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from urllib.parse import urljoin
from pipeline import text, grade, MONEY, clean, fetch_html, export_school, run_school, main_content, table_records, values


class Crawler:
    name = 'Brock University'
    slug = 'brock_university'
    url = 'https://brocku.ca/safa/2026-international-students/'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        root = main_content(soup)
        scholarships, entrance_tiers = [], []
        for table in root.find_all('table'):
            for row in table_records(table):
                band = next((v for k,v in row.items() if k.startswith('admission average')), None)
                if band:
                    condition = grade(re.sub(r'\s+and above', '+', band, flags=re.I))
                    value_columns = {
                        'total_value': next((v for k,v in row.items() if k.startswith('amount of award')), ''),
                        'year_1_value': row.get('year 1', ''), 'renewal_value': row.get('renewals', '')}
                    tier = {'grade_text': band, 'min_average': condition['min'], 'max_average': condition['max']}
                    for field, raw in value_columns.items():
                        match = MONEY.search(raw)
                        if match:
                            amount = float(match[1].replace(',', ''))
                            tier[field] = {'max_amount' if field == 'total_value' else 'amount': amount}
                    entrance_tiers.append(clean(tier))
                    continue
                name = next((v for k,v in row.items() if k.startswith('awards ')), None)
                if name:
                    raw_value = row.get('value', '')
                    item = {'name': name, 'applicant_category': 'international', 'value_text': raw_value,
                            'values': values(raw_value), 'eligibility': row.get('application instructions')}
                    if re.search(r'variable.*domestic tuition', raw_value, re.I):
                        item['benefit_type'] = 'domestic_tuition_equivalent'
                        item['tuition_rate_basis'] = 'domestic'
                    keyword = 'ambassador' if 'ambassador' in name.lower() else 'future leaders' if 'future leaders' in name.lower() else None
                    if keyword:
                        link = next((a for a in root.find_all('a', href=True) if keyword in text(a).lower() and 'application' in text(a).lower()), None)
                        if link:
                            item['application'] = {'url': urljoin(self.url, link['href'])}
                            if 'closed' in text(link).lower():
                                item['application']['status'] = 'closed'
                    scholarships.append(clean(item))
        if entrance_tiers:
            notes = [text(p) for p in root.find_all(['p', 'td']) if re.search(r'renewable for up to|U.S.A.|annual approval', text(p), re.I)]
            heading = next((h for h in root.find_all('h2') if 'International Brock Scholars Award' in text(h)), None)
            link = heading.find('a', href=True) if heading else None
            scholarships.insert(0, clean({'name': 'International Brock Scholars Award',
                'applicant_category': 'international',
                'application': {'method': 'automatic'} if any('awards are automatic' in text(p).lower() for p in root.find_all('p')) else {},
                'renewable': True if any('renewable' in note.lower() for note in notes) else None, 'renewal_conditions': notes,
                'terms_url': urljoin(self.url, link['href']) if link else None,
                'tiers': entrance_tiers}))
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
