import aiohttp
from jinja2 import Template
import asyncio

CLASSIFIER = 'Programming Language :: Python :: {}'
VERSIONS_3 = ['3', '3.3', '3.4', '3.5', '3.6', '3.7']
VERSIONS_2 = ['2', '2.6', '2.7']
LIMIT = 250


async def get_most_dowloaded_projects(session):
    url = 'https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.json'
    async with session.get(url) as resp:
        data = await resp.json()
        return data['rows']


async def get_pypi_data(project, session):
    url = f'https://pypi.org/pypi/{project}/json'
    async with session.get(url) as resp:
        return await resp.json()


async def get_project_data(project, session):
    data = await get_pypi_data(project['project'], session)
    project['python2'] = any(
        CLASSIFIER.format(v) in data['info']['classifiers']
        for v in VERSIONS_2
    )
    for v in VERSIONS_3:
        project[f'python{v}'] = CLASSIFIER.format(v) in data['info']['classifiers']

    project['python3'] = any(
        CLASSIFIER.format(v) in data['info']['classifiers']
        for v in VERSIONS_3
    )

    project['download_count'] = '{:,d}'.format(
        project['download_count']
    ).replace(',', '&thinsp;')

    return project


async def main():
    async with aiohttp.ClientSession() as session:
        projects = await get_most_dowloaded_projects(session)
        futures = [get_project_data(p, session) for p in projects[:LIMIT]]
        projects = await asyncio.gather(*futures)

    summary = {}
    summary['both'] = sum(p['python2'] and p['python3'] for p in projects)
    summary['python3-only'] = sum(p['python3'] and not p['python2'] for p in projects)
    summary['python2-only'] = sum(p['python2'] and not p['python3'] for p in projects)

    with open('template.html') as f:
        template = Template(f.read())

    with open('index.html', 'w') as f:
        f.write(template.render(
            projects=projects[:LIMIT], limit=LIMIT, summary=summary
        ))


if __name__ == '__main__':
    asyncio.run(main())
