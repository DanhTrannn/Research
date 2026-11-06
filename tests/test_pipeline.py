"""Regression coverage for the single-step, per-school pipeline."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bs4 import BeautifulSoup
from pipeline import ROOT, PageParser, fetch_html, grade, money_values, date_value, renewal, application
from run_all import discover_schools, load_school, main


def soup(html):
    return BeautifulSoup(html, 'html.parser')


def resolve(document, pointer):
    result = document
    for token in pointer.lstrip('/').split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        result = result[int(token)] if isinstance(result, list) else result[token]
    return result


class PipelineTests(unittest.TestCase):
    def test_all_13_school_modules_load_without_network(self):
        with patch('pipeline.requests.get', side_effect=AssertionError('network at import')):
            names = discover_schools()
            self.assertEqual(len(names), 13)
            for name in names:
                self.assertEqual(load_school(name).slug, name)

    def test_existing_outputs_are_self_contained(self):
        paths = sorted((ROOT / 'outputs').glob('*.json'))
        self.assertEqual(len(paths), 13)
        for path in paths:
            data = json.loads(path.read_text())
            self.assertEqual(data['schema_version'], 3)
            self.assertEqual(data['school']['slug'], path.stem)
            self.assertEqual(data['summary']['named_award_entries'], len(data['scholarships']))
            def check(value):
                if isinstance(value, dict):
                    if 'json_pointer' in value:
                        self.assertEqual(value['file'], f'outputs/{path.name}')
                        self.assertIsNotNone(resolve(data, value['json_pointer']))
                    for child in value.values():
                        check(child)
                elif isinstance(value, list):
                    for child in value:
                        check(child)
            check(data)

    def test_lakehead_preserves_three_independent_tiers(self):
        data = json.loads((ROOT / 'outputs/lakehead_university.json').read_text())
        tiers = data['scholarship_groups'][0]['tiers']
        self.assertEqual(len(tiers), 3)
        self.assertEqual([t['renewal']['is_renewable'] for t in tiers], [True, True, False])
        self.assertEqual(tiers[0]['values'][0]['currency'], 'CAD')

    def test_ibu_costs_are_not_award_values(self):
        data = json.loads((ROOT / 'outputs/ibu_university.json').read_text())
        self.assertEqual(data['scholarships'], [])
        self.assertEqual(data['cost_breakdowns'][0]['components'][0]['dollar_tokens'], [69000])

    def test_full_table_and_spans_are_preserved(self):
        html = '<h1>Scholarships</h1><table><tr><th>Grade</th><th>Value</th></tr>'
        html += '<tr><td rowspan="2">A</td><td>$100</td></tr><tr><td>$200</td></tr>'
        html += ''.join(f'<tr><td>{i}</td><td>$300</td></tr>' for i in range(7)) + '</table>'
        table = PageParser().extract_tables(soup(html))[0]
        self.assertEqual(table['rows_count'], 9)
        self.assertEqual(table['grid'][2], ['A', '$200'])

    def test_bot_page_is_rejected_even_with_http_200(self):
        document, error = PageParser.validate_html(200, b'<title>Just a moment...</title><h1>Scholarships</h1>')
        self.assertIsNone(document)
        self.assertEqual(error, 'blocked')

    def test_passive_cloudflare_script_is_allowed(self):
        document, error = PageParser.validate_html(200, b'<title>Scholarships</title><h1>Scholarships</h1><script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>')
        self.assertIsNotNone(document)
        self.assertIsNone(error)

    def test_curl_exit_zero_does_not_mean_http_success(self):
        response = SimpleNamespace(status_code=403, content=b'blocked', url='https://example.org', headers={'Content-Type': 'text/html'})
        curl = SimpleNamespace(returncode=0, stdout=b'blocked\n__SCHOLARSHIP_HTTP_META__403\thttps://example.org\ttext/html')
        with patch('pipeline.requests.get', return_value=response), patch('pipeline.subprocess.run', return_value=curl):
            metadata, document = fetch_html('https://example.org')
        self.assertIsNone(document)
        self.assertEqual(metadata['http_status'], 403)
        self.assertEqual(metadata['fetch_status'], 'blocked')

    def test_single_school_run_writes_only_one_final_file(self):
        html = '<html><title>Scholarships</title><main><h1>Scholarships</h1><h2>Test Scholarship</h2><p>Value of award: CAD $2,000 per year</p><p>This scholarship is renewable each year.</p></main></html>'
        metadata = {'http_status': 200, 'fetch_status': 'ok', 'attempts': []}
        with tempfile.TemporaryDirectory() as temp, patch('pipeline.fetch_html', return_value=(metadata, soup(html))):
            self.assertEqual(main(['--school', 'humber', '--output-dir', temp]), 0)
            self.assertEqual([p.name for p in Path(temp).iterdir()], ['humber_polytechnic.json'])
            result = json.loads(Path(temp, 'humber_polytechnic.json').read_text())
            self.assertTrue(result['crawl']['success'])
            self.assertEqual(result['scholarships'][0]['benefit']['values'][0]['min_amount'], 2000)
            self.assertEqual(result['source']['input_kind'], 'live_http')

    def test_failure_overwrites_old_result_with_explicit_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp, 'humber_polytechnic.json')
            target.write_text('{"schema_version":3,"old_success":true}')
            with patch('pipeline.fetch_html', return_value=({'http_status':403,'fetch_status':'blocked','attempts':[]}, None)):
                self.assertEqual(main(['--school', 'humber', '--output-dir', temp]), 1)
            result = json.loads(target.read_text())
            self.assertFalse(result['crawl']['success'])
            self.assertEqual(result['scholarships'], [])
            self.assertNotIn('old_success', result)

    def test_invalid_selection_does_not_start_http(self):
        with patch('pipeline.fetch_html') as fetch, self.assertRaises(SystemExit):
            main(['--school', 'university'])
        fetch.assert_not_called()

    def test_unrelated_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp, 'humber_polytechnic.json'); target.write_text('{"keep":true}')
            with patch('pipeline.fetch_html') as fetch, self.assertRaises(SystemExit):
                main(['--school','humber','--output-dir',temp])
            fetch.assert_not_called()
            self.assertEqual(json.loads(target.read_text()), {'keep': True})

class ValueTests(unittest.TestCase):
    def test_explicit_total_and_annual_values_stay_separate(self):
        values = money_values('$40,000 ($10,000 x 4 years) 1', 'Scholarship Total (Canadian dollars)', 'CAD')
        self.assertEqual({(v['min_amount'], v['payment_basis']) for v in values}, {(40000, 'total_degree'), (10000, 'per_year')})
        self.assertEqual(next(v for v in values if v['payment_basis'] == 'per_year')['max_payments'], 4)

    def test_per_term_and_total_do_not_create_90000(self):
        values = money_values('Value of award: $7,500 per term ($60,000 over the course of a four-year degree)')
        self.assertEqual([(v['min_amount'], v['payment_basis']) for v in values], [(7500, 'per_term'), (60000, 'total_degree')])
        self.assertTrue(all(v['currency'] is None for v in values))

    def test_up_to_has_no_invented_minimum(self):
        value = money_values('One valued at up to $7,500 for one year')[0]
        self.assertIsNone(value['min_amount'])
        self.assertEqual(value['max_amount'], 7500)

    def test_one_time_before_amount_applies_to_single_value(self):
        self.assertEqual(money_values('A one-time University President scholarship valued at $2,000.')[0]['payment_basis'], 'one_time')

    def test_grade_band_and_ib_are_distinct(self):
        self.assertEqual(grade('80.0% - 89.9%')['max'], 89.9)
        self.assertEqual(grade('35+', 'international_baccalaureate')['system'], 'international_baccalaureate')
        self.assertEqual(grade('One Time 80%+ Diploma')['min'], 80)
        self.assertIsNone(grade('Read policy')['min'])

    def test_grade_range_must_be_valid_for_its_system(self):
        for raw, system in [('90-80%', 'academic_average_percent'),
                            ('101%+', 'academic_average_percent'),
                            ('46+', 'international_baccalaureate')]:
            with self.subTest(raw=raw):
                self.assertIsNone(grade(raw, system)['min'])
                self.assertIsNone(grade(raw, system)['max'])

    def test_money_range_preserves_explicit_payment_basis(self):
        value = money_values('$1,000 - $2,000 per year')[0]
        self.assertEqual((value['min_amount'], value['max_amount'], value['payment_basis']),
                         (1000, 2000, 'per_year'))

    def test_renewal_negation_and_mixed(self):
        self.assertIs(renewal(['This award is not renewable.'])['is_renewable'], False)
        self.assertIsNone(renewal(['A is renewable.', 'B is non-renewable.'])['is_renewable'])

    def test_year_is_never_inferred_from_capture(self):
        self.assertIsNone(date_value('December 15')['date'])
        self.assertEqual(date_value('March 17, 2027')['date'], '2027-03-17')
        self.assertIsNone(date_value('February 31, 2027')['date'])

    def test_no_application_flag_does_not_mean_automatic(self):
        result = application([], {'application required': 'No', 'application form': 'Apply in ACSIS each term'})
        self.assertIs(result['application_required_flag'], False)
        self.assertEqual(result['method'], 'unknown')
        self.assertEqual(result['instructions_text'], 'Apply in ACSIS each term')

    def test_tuition_payment_deadline_is_not_application_deadline(self):
        self.assertEqual(application(['The second disbursement is before the January tuition deadline'], {})['deadlines'], [])


if __name__ == '__main__':
    unittest.main()
