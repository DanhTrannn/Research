"""International Business University (IBU): crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from datetime import datetime, timezone
from pipeline import fetch_html, export_school, run_school, selected_awards, values, explicit_currency, text, clean, distinct


class Crawler:
    name = 'International Business University (IBU)'
    slug = 'ibu_university'
    url = 'https://ibu.ca/admission/undergraduate-admissions/undergraduate-tuition-fees/entrance-scholarships/'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        scholarships = selected_awards(soup, r'^(Entrance Scholarships for Academic Achievement|General Entrance Scholarships)$', applicant_category='domestic', type='scholarship_group')
        # Read the associated tab panel, not the adjacent tab label or all page dollars.
        for tab in soup.select('[role="tab"][aria-controls]'):
            panel = soup.find(id=tab['aria-controls'])
            if panel is None or not re.search(r'bursary', text(tab), re.I):
                continue
            paragraphs = [text(p) for p in panel.find_all('p')]
            benefits = []
            for table in panel.select('table.tuition-table'):
                for tr in table.find_all('tr'):
                    cells = [text(c) for c in tr.find_all(['td', 'th'])]
                    if len(cells) > 1 and re.match(r'^Less:.*Scholarship', cells[0], re.I):
                        benefits.append({'label': re.sub(r'^Less:\s*', '', cells[0]), 'value_text': cells[1],
                                         'values': values(cells[1], explicit_currency(text(panel)))})
            validity = next((p for p in paragraphs if 'valid until' in p.lower()), None)
            expired = re.search(r'end of (20\d\d)', validity or '')
            scholarships.append(clean({'name': text(tab), 'type': 'bursary', 'applicant_category': 'international',
                'programs': next((p for p in paragraphs if p.startswith('Applicable Programs:')), None),
                'eligible_countries': distinct(text(c) for c in panel.select('table.country-table td') if text(c)),
                'benefits': benefits, 'validity_text': validity,
                'expired': int(expired[1]) < datetime.now(timezone.utc).year if expired else None,
                'conditions': [text(li) for li in panel.find_all('li')]}))
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
