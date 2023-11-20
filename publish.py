import asyncio
from collections import defaultdict
from pathlib import Path
from shutil import copy2

import aiohttp
from jinja2 import Template

CLASSIFIER = 'Programming Language :: Python :: {}'
VERSIONS_3 = ['3', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10']
VERSIONS_2 = ['2', '2.6', '2.7']
LIMIT = 250


async def get_most_dowloaded_projects(session):
    url = 'https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.json'
    async with session.get(url) as resp:
        data = await resp.json()
        return data['rows'], data['last_update']


async def get_pypi_data(project, session):
    url = f'https://pypi.org/pypi/{project}/json'
    async with session.get(url) as resp:
        return await resp.json()


async def get_project_data(project, session):
    data = await get_pypi_data(project['project'], session)
    project['url'] = data['info'].get('home_page')
    # sometimes empty, sometimes None
    requires_python = data['info']['requires_python'] or ''

    project['python2'] = any(
        CLASSIFIER.format(v) in data['info']['classifiers']
        for v in VERSIONS_2
    ) or '>=2' in requires_python
    for v in VERSIONS_3:
        project[f'python{v}'] = CLASSIFIER.format(v) in data['info']['classifiers']

    project['python3'] = any(
        CLASSIFIER.format(v) in data['info']['classifiers']
        for v in VERSIONS_3
    ) or '>=3' in requires_python

    project['download_count'] = '{:,d}'.format(
        project['download_count']
    ).replace(',', '&thinsp;')

    return project


async def main():
    out = Path("build")
    out.mkdir(exist_ok=True)

    async with aiohttp.ClientSession() as session:
        projects, last_update = await get_most_dowloaded_projects(session)
        futures = [get_project_data(p, session) for p in projects[:LIMIT]]
        projects = await asyncio.gather(*futures)

    summary = defaultdict(int)
    for p in projects:
        if p['python2'] and p['python3']:
            summary['both'] += 1
        elif p['python3'] and not p['python2']:
            summary['python3-only'] += 1
        elif p['python2'] and not p['python3']:
            summary['python2-only'] += 1
        else:
            summary['missing_info'] += 1

    with open('template.html') as f:
        template = Template(f.read())

    with (out / 'index.html').open('w') as f:
        f.write(template.render(
            projects=projects[:LIMIT],
            limit=LIMIT,
            summary=summary,
            last_update=last_update,
        ))

    copy2("style.css", out)


if __name__ == '__main__':
    asyncio.run(main())
