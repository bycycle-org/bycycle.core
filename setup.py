from setuptools import setup, find_packages


setup(
    name='bycycle.core',
    version='0.6.dev0',
    description='byCycle core model and services',
    long_description='byCycle model, routing, and geocoding.',
    license='GPLv3',
    author='Wyatt Baldwin, byCycle.org',
    author_email='wyatt@bycycle.org',
    keywords='bicycle bike cycle trip planner geocoder',
    url='http://bycycle.org/',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    packages=find_packages(),
    zip_safe=False,
    install_requires=[
        'Dijkstar>=2.2',
        'glineenc>=1.0',
        'psycopg2>=2.5.3',
        'pyproj>=1.9.3',
        'requests>=2.3.0',
        'Shapely>=1.3.3',
        'SQLAlchemy>=0.9.7',
        'tangled>=0.1a7',
    ],
    extras_require={
        'dev': [
            'coverage>=3.7.1',
        ],
    },
    entry_points="""
    [console_scripts]
    bycycle = bycycle.core.scripts.main:main
    bycycle-fetch = bycycle.core.scripts.fetch:fetch
    bycycle-import = bycycle.core.scripts.importer:do_import
    bycycle-graph = bycycle.core.scripts.graph:make_graph

    """,
)
