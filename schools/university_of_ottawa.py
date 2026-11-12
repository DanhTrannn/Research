"""University of Ottawa: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import fetch_html, export_school, run_school, selected_awards


class Crawler:
    name = 'University of Ottawa'
    slug = 'university_of_ottawa'
    url = 'https://www.uottawa.ca/study/fees-financial-support/international-english-scholarship'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        scholarships = selected_awards(soup, r'^International English (Admission|Academic Excellence) Scholarship$',
                                      type='scholarship', applicant_category='international',
                                      international_eligible=True, eligible_stages=['entrance'],
                                      study_level='undergraduate')
        # Preserve the published schedule statements without multiplying instalments.
        for item in scholarships:
            if 'Admission' in item['name']:
                item['notes'] = ['The published per-term amount, degree total and maximum instalments must be checked against the full terms; do not multiply them automatically.']
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
