from setuptools import setup, PEP420PackageFinder

find_packages = PEP420PackageFinder.find


setup(
    name='bycycle.core',
    version='0.6.dev5',
    description='byCycle core model and services',
    long_description='byCycle model, geocoding, and routing/directions.',
    author='Wyatt Baldwin',
    author_email='wyatt@bycycle.org',
    keywords='bicycle bike cycle geocoder trip planner route finder directions',
    url='http://bycycle.org/',
    download_url='https://github.com/bycycle-org/bycycle.core',
    license='GPLv3',
    packages=find_packages(include=['bycycle', 'bycycle.core', 'bycycle.core.*']),
    include_package_data=True,
    install_requires=[
        'Dijkstar>=2.4.0',
        'mercantile>=1.0.4',
        'psycopg2-binary>=2.8.2',
        'pyproj>=2.1.3',
        'requests>=2.21.0',
        'runcommands>=1.0a35',
        'Shapely>=1.6.4',
        'SQLAlchemy>=1.3.3',
        'tangled>=1.0a12',
    ],
    extras_require={
        'dev': [
            'coverage',
            'pgcli',
        ],
    },
    entry_points="""
    [console_scripts]
    bycycle = bycycle.core.__main__:bycycle.console_script

    """,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
)
