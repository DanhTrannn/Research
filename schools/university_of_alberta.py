"""University of Alberta: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import fetch_html, export_school, run_school, selected_awards


class Crawler:
    name = 'University of Alberta'
    slug = 'university_of_alberta'
    url = 'https://www.ualberta.ca/en/admissions/tuition-and-scholarships/international-entrance-scholarships/index.html'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        return {'scholarships': selected_awards(soup,
            r'^(International Admission Scholarship|Regional Excellence Scholarship|President.s International Distinction Scholarship|Chan Pang Kuen Memorial International Distinction Scholarship|International Leader Scholarship|May Quon Undergraduate Scholarship|Cora Martinson International Scholarship)$',
            type='scholarship', applicant_category='international',
            international_eligible=True, eligible_stages=['entrance'])}

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
