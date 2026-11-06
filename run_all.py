#!/usr/bin/env python3
"""Fetch, extract and normalize directly to one outputs/<school>.json file."""
import argparse
import importlib
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def discover_schools():
    return sorted(p.stem for p in (ROOT / 'schools').glob('*.py') if not p.name.startswith('_'))


def load_school(slug):
    return importlib.import_module(f'schools.{slug}').Crawler()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--school', '-s', help='School slug or unambiguous substring')
    parser.add_argument('--list', '-l', action='store_true')
    parser.add_argument('--workers', '-w', type=int, default=4)
    parser.add_argument('--timeout', type=float, default=12)
    parser.add_argument('--browser', choices=('auto', 'selenium', 'http'), default='auto',
                        help='auto: HTTP first, Selenium for blocked/JS pages')
    display = parser.add_mutually_exclusive_group()
    display.add_argument('--headed', action='store_true', help='Show Selenium Chrome (default when DISPLAY is available)')
    display.add_argument('--headless', action='store_true', help='Run Selenium Chrome without a visible window')
    parser.add_argument('--browser-wait', type=float, default=25, help='Seconds to wait for usable browser content')
    parser.add_argument('--browser-profile', type=Path,
                        help='Retain a dedicated Chrome profile for one school (never use your personal profile)')
    parser.add_argument('--manual-challenge-wait', type=float, default=0,
                        help='Seconds to allow manual verification in headed Chrome; 0 disables')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs')
    args = parser.parse_args(argv)
    if args.workers < 1 or args.timeout <= 0 or args.browser_wait <= 0:
        parser.error('--workers, --timeout and --browser-wait must be positive')
    if args.manual_challenge_wait < 0:
        parser.error('--manual-challenge-wait must be non-negative')
    import pipeline
    pipeline.BROWSER_MODE = args.browser
    pipeline.BROWSER_HEADLESS = args.headless or (not args.headed and not os.environ.get('DISPLAY'))
    pipeline.BROWSER_WAIT = args.browser_wait
    pipeline.BROWSER_PROFILE = args.browser_profile
    pipeline.MANUAL_CHALLENGE_WAIT = args.manual_challenge_wait
    if args.browser == 'http' and (args.browser_profile or args.manual_challenge_wait):
        parser.error('Profile and manual verification require --browser auto or selenium')
    if args.manual_challenge_wait and pipeline.BROWSER_HEADLESS:
        parser.error('Manual verification requires --headed')
    names = discover_schools()
    if args.list:
        print('\n'.join(names))
        return 0
    if args.school:
        target = args.school.lower().removesuffix('.py').removesuffix('.json')
        matches = [target] if target in names else [name for name in names if target in name]
        if len(matches) != 1:
            parser.error(f'School must match exactly one name: {matches}')
        names = matches
    if args.browser_profile and len(names) != 1:
        parser.error('--browser-profile requires --school matching one school')
    # Validate the target set before any HTTP request or file write.
    for name in names:
        path = args.output_dir / f'{name}.json'
        if path.exists():
            import json
            if json.loads(path.read_text()).get('schema_version') not in (3, 4):
                parser.error(f'{path}: contains legacy or unrelated data; choose another output directory')
    def run(name):
        try:
            result = load_school(name).run(args.output_dir, args.timeout)
            success = result['status'] == 'ok'
            print(f"[{'OK' if success else 'FAILED'}] {name}: {result['status']}")
            return success
        except Exception as exc:
            print(f'[FAILED] {name}: {type(exc).__name__}: {exc}')
            return False
    with ThreadPoolExecutor(max_workers=min(args.workers, len(names))) as pool:
        outcomes = list(pool.map(run, names))
    print(f'{sum(outcomes)}/{len(outcomes)} schools; output: {args.output_dir}')
    return 0 if all(outcomes) else 1


if __name__ == '__main__':
    raise SystemExit(main())
