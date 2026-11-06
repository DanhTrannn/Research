"""Lakehead University: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import fetch_html, export_school, run_school, main_content, table_records, tier, explicit_currency, text_blocks, text, application_info


class Crawler:
    name = 'Lakehead University'
    slug = 'lakehead_university'
    url = 'https://www.lakeheadu.ca/international/future/scholarships-awards'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        root = main_content(soup)
        table = next((t for t in root.find_all('table') if 'Academic Average' in text(t)), None)
        if table is None:
            return {'scholarships': []}
        # Match the reference number in each tier to the actual numbered footnote.
        footnotes = {}
        for tag in text_blocks(root):
            statement = text(tag)
            match = re.match(r'^(\d+)\s+(?:Renewable|Non-renewable)', statement, re.I)
            if match:
                footnotes[match[1]] = statement
        tiers = []
        for row in table_records(table):
            grade_text = next(v for k, v in row.items() if k.startswith('academic average'))
            value_text = next(v for k, v in row.items() if k.startswith('scholarship total'))
            marker = re.search(r'\)\s*(\d+)\s*$', value_text)
            conditions = [footnotes[marker[1]]] if marker and marker[1] in footnotes else []
            item = tier(grade_text, value_text, conditions, currency=explicit_currency(text(table)),
                        header='Scholarship Total', ib_average=row.get('ib average'))
            # The same first-year-only sum is repeated in parentheses, not two benefits.
            if re.search(r'Year 1 only', value_text, re.I):
                item['values'] = [v for v in item['values'] if v['payment_basis'] == 'one_time']
            tiers.append(item)
        heading = table.find_previous(re.compile(r'^h[1-6]$'))
        name = re.split('Automatically', text(heading))[0].strip() if heading else 'International Undergraduate Entrance Scholarships'
        return {'scholarships': [{'name': name, 'type': 'scholarship', 'applicant_category': 'international',
                                 'application': application_info([text(heading)]) if heading else {}, 'tiers': tiers}]}

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
