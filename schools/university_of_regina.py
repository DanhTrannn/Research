"""University of Regina: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from urllib.parse import urljoin, urlparse
from pipeline import (fetch_html, export_school, run_school, schedule_tables, text, award,
                      values, clean, date_value, scope_filter)


class Crawler:
    name = 'University of Regina'
    slug = 'university_of_regina'
    url = 'https://www.uregina.ca/cost-aid/funding/undergraduate-scholarships/index.html'

    def crawl(self, timeout=12):
        metadata, overview = fetch_html(self.url, timeout)
        if overview is None:
            return metadata, None
        pages = {'overview': overview}
        self.related_error = None
        # Follow exactly the official international entrance link, not the entire site.
        link = next((a for a in overview.find_all('a', href=True)
                     if 'Entrance Awards for International Students' in text(a)), None)
        if link:
            url = urljoin(self.url, link['href'])
            if urlparse(url).hostname == urlparse(self.url).hostname:
                child_meta, child = fetch_html(url, timeout)
                if child is not None:
                    pages['international'] = (url, child)
                else:
                    self.related_error = f'International award page unavailable: {child_meta["fetch_status"]} ({url})'
        if 'international' not in pages and not self.related_error:
            self.related_error = 'International entrance link was not found or was not an official same-host URL.'
        return metadata, pages

    def extract(self, pages):
        overview = pages['overview']
        scholarships = []

        if 'international' in pages:
            url, soup = pages['international']
            distinction = {'name': 'International Student of Distinction Scholarship',
                           'type': 'scholarship', 'applicant_category': 'international',
                           'international_eligible': True, 'eligible_stages': ['entrance'],
                           'source_url': url, 'tiers': []}
            for heading in soup.select('.uor-accordionHeading'):
                name = text(heading)
                if name == 'International Entrance Scholarship' or re.match(r'^International Student of Distinction Scholarship: Tier \d+$', name):
                    panel = heading.find_parent(class_='uor-accordionItem')
                    value_heading = panel.find('h3')
                    if value_heading is None:
                        continue
                    paragraphs = [text(p) for p in panel.find_all(['p', 'li']) if not p.find(['p', 'li'])]
                    item = award(name, paragraphs, type='scholarship', applicant_category='international',
                                 international_eligible=True, eligible_stages=['entrance'], source_url=url)
                    item['eligibility'] = [text(li) for li in panel.find_all('li')]
                    # Parse the award heading only: never treat a deposit/tuition example as a benefit.
                    item.pop('description', None)
                    item['value_texts'] = [text(value_heading)]
                    item['values'] = values(text(value_heading), header='Scholarship Total' if 'x' in text(value_heading) else '')
                    if 'Distinction Scholarship:' in name:
                        item.pop('source_url', None)
                        item.pop('applicant_category', None)
                        item.pop('type', None)
                        item['benefit_type'] = 'housing_and_meal_plan' if 'Meal Plan' in text(value_heading) else 'housing'
                        item['approximate_value'] = True
                        distinction['tiers'].append(item)
                    else:
                        scholarships.append(item)
            if distinction['tiers']:
                for heading in soup.find_all('h3'):
                    label = text(heading)
                    if label not in ('Application Deadlines', 'Housing Deadlines'):
                        continue
                    table = heading.find_next('table')
                    if table is None or table.find_parent(class_='uor-accordionItem') is not heading.find_parent(class_='uor-accordionItem'):
                        continue
                    deadlines = []
                    for row in table.find_all('tr'):
                        cells = [text(c) for c in row.find_all(['th', 'td'])]
                        if len(cells) == 2 and re.match(r'^(Fall|Winter|Spring)', cells[0]):
                            deadlines.append({'term': cells[0], **date_value(cells[1])})
                    if deadlines:
                        if label == 'Application Deadlines':
                            distinction['application'] = {'deadlines': deadlines}
                        else:
                            distinction['housing_deadlines'] = deadlines
                notice = next((text(b) for b in soup.find_all('blockquote')
                               if 'International Student of Distinction' in text(b) and 'filled' in text(b)), None)
                if notice:
                    distinction['availability_notice'] = notice
                scholarships.append(distinction)
        notes = [self.related_error] if getattr(self, 'related_error', None) else []
        notes.append('Only international entrance scholarships are exported; '
                     'the Family Scholarship and International Undergraduate Student Bursary are excluded.')
        return clean({'scholarships': scope_filter(scholarships),
                      'application_periods': schedule_tables(overview, r'^Entrance Award Deadlines$'),
                      'notes': notes})

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
