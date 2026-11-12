"""Humber Polytechnic: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import (award, clean, distinct, export_school, fetch_html, main_content,
                      run_school, scope_filter, table_records, text, tier, values)


def find_heading(root, pattern):
    return next((h for h in root.find_all(['h2', 'h3', 'h4'])
                 if re.search(pattern, text(h), re.I)), None)


def section_paragraphs(heading):
    """Text between this heading and the next heading of any level."""
    result = []
    for node in heading.next_elements:
        if getattr(node, 'name', None) and re.fullmatch(r'h[1-6]', node.name):
            break
        if getattr(node, 'name', None) in ('p', 'li') and not node.find(['p', 'li']):
            value = text(node)
            if value:
                result.append(value)
    return distinct(result)


def merged_paragraphs(root, title_pattern, detail_pattern=None):
    paragraphs = []
    heading = find_heading(root, title_pattern)
    if heading is not None:
        paragraphs += section_paragraphs(heading)
    if detail_pattern:
        detail = find_heading(root, detail_pattern)
        if detail is not None:
            paragraphs += section_paragraphs(detail)
    return distinct(paragraphs)


def add_values(item, value_text, basis, amounts):
    item['value_text'] = value_text
    item['values'] = [clean({'min_amount': amount, 'max_amount': amount,
                             'payment_basis': basis}) for amount in amounts]
    return item


class Crawler:
    name = 'Humber Polytechnic'
    slug = 'humber_polytechnic'
    url = 'https://humber.ca/international/admissions-financial-aid/scholarships-bursaries'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        root = main_content(soup)
        scholarships = []

        # International entrance scholarship, with its separate details section.
        paragraphs = merged_paragraphs(
            root, r'^International Onshore Scholarship$', r'^International Onshore Scholarship Details$')
        paragraphs = [p for p in paragraphs if not re.search(r'\$1,500 tuition reduction', p, re.I)]
        item = award('International Onshore Scholarship', paragraphs, type='scholarship',
                     applicant_category='international', international_eligible=True,
                     eligible_stages=['entrance'], application={'method': 'automatic'})
        add_values(item, '$1,000 one-time entrance scholarship', 'one_time', [1000])
        scholarships.append(item)

        # Direct-entry award for diploma/advanced-diploma applicants.
        paragraphs = merged_paragraphs(
            root, r'^Diploma & Advanced Diploma Direct Early Admission Awards$',
            r'^Diploma Direct Early Admission Awards$')
        item = award('Diploma & Advanced Diploma Direct Early Admission Awards', paragraphs,
                     type='scholarship', applicant_category='international',
                     international_eligible=True, eligible_stages=['entrance'],
                     application={'method': 'automatic'})
        add_values(item, '$1,500 tuition reduction', 'one_time', [1500])
        scholarships.append(item)

        # Degree entrance scholarships use a grade/amount table.
        paragraphs = merged_paragraphs(root, r"^Bachelor.s Degree Entrance Scholarships$")
        item = award("Bachelor's Degree Entrance Scholarships", paragraphs, type='scholarship',
                     applicant_category='international', international_eligible=True,
                     eligible_stages=['entrance'], application={'method': 'automatic'})
        requirements = find_heading(root, r"^Bachelor.s Degree Scholarship Requirements$")
        tiers = []
        if requirements is not None:
            table = requirements.find_next('table')
            parent_text = text(table.parent) if table.parent is not None else ''
            condition = re.search(
                r'Renewable scholarships will be reissued.*?Bachelor.s degree\.',
                parent_text, re.I)
            conditions = [condition.group(0)] if condition else []
            for row in table_records(table):
                amount = row.get('amount', '')
                grade_text = row.get('required gpa', '')
                renewable = row.get('renewable', '')
                if not amount.startswith('$') or not grade_text:
                    continue
                grade_text = re.sub(r'\s*or higher', '+', grade_text, flags=re.I)
                tier_item = tier(grade_text, amount)
                if renewable.lower().startswith('yes'):
                    tier_item['renewable'] = True
                    tier_item['renewal_conditions'] = conditions
                elif 'one time' in renewable.lower():
                    tier_item['renewable'] = False
                tiers.append(tier_item)
        item['tiers'] = tiers
        item['value_text'] = 'Grade-based tiers from $1,500 to $4,000'
        scholarships.append(item)

        # EAP graduates entering a degree.
        paragraphs = merged_paragraphs(root, r"^Bachelor.s Degree Scholarships for EAP Graduates$")
        item = award("Bachelor's Degree Scholarships for EAP Graduates", paragraphs,
                     type='scholarship', applicant_category='international',
                     international_eligible=True, eligible_stages=['entrance'],
                     application={'method': 'automatic'})
        add_values(item, '$1,500 one-time scholarship', 'one_time', [1500])
        item['renewable'] = False
        scholarships.append(item)

        # Transfer entrance scholarship.
        paragraphs = merged_paragraphs(root, r"^Degree Transfer Scholarships .*$")
        item = award('Degree Transfer Scholarships', paragraphs, type='scholarship',
                     applicant_category='international', international_eligible=True,
                     eligible_stages=['transfer_entrance'], application={'method': 'automatic'})
        item['value_text'] = '$1,500 for a certificate program; $2,500 for a diploma program'
        item['values'] = [clean({'min_amount': amount, 'max_amount': amount,
                                 'payment_basis': 'one_time'}) for amount in (1500, 2500)]
        scholarships.append(item)

        # New international Bachelor of Commerce students.
        paragraphs = merged_paragraphs(root, r"^Senior Dean.s Bachelor of Commerce Award$")
        item = award("Senior Dean's Bachelor of Commerce Award", paragraphs, type='award',
                     applicant_category='international', international_eligible=True,
                     eligible_stages=['entrance'], application={'method': 'automatic'})
        item['value_text'] = '$10,000 total ($2,500 per semester for four semesters)'
        item['values'] = [
            clean({'min_amount': 10000, 'max_amount': 10000, 'payment_basis': 'total_degree'}),
            clean({'min_amount': 2500, 'max_amount': 2500, 'payment_basis': 'per_term',
                   'max_payments': 4}),
        ]
        scholarships.append(item)

        # International pathway scholarship.
        paragraphs = merged_paragraphs(root, r'^LanguageCert University and College Pathways Scholarship$')
        item = award('LanguageCert University and College Pathways Scholarship', paragraphs,
                     type='scholarship', applicant_category='international',
                     international_eligible=True, eligible_stages=['entrance'],
                     application={'method': 'application_required'})
        add_values(item, '$1,000 scholarship', 'one_time', [1000])
        scholarships.append(item)

        return {'scholarships': scope_filter(scholarships),
                'notes': ['Only international entrance scholarships and admission awards are exported; '
                          'the President\'s International Entrance Award is excluded because it is a bursary, '
                          'and EAP/current-student awards and external awards are excluded.']}

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
