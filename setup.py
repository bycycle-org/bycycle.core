from setuptools import setup, PEP420PackageFinder

find_packages = PEP420PackageFinder.find


setup(
    name='bycycle.core',
    version='0.6.dev1',
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
        'Programming Language :: Python :: 3.5',
    ],
    packages=find_packages(include=['bycycle', 'bycycle.core', 'bycycle.core.*']),
    include_package_data=True,
    install_requires=[
        'boto3>=1.4.4',
        'Dijkstar>=2.2',
        'glineenc>=1.0',
        'psycopg2>=2.7.1',
        'pyproj>=1.9.5.1',
        'requests>=2.13.0',
        'runcommands>=1.0a26',
        'Shapely>=1.6.2',
        'SQLAlchemy>=1.1.9',
        'tangled>=0.1a9',
    ],
    extras_require={
        'dev': [
            'coverage>=4.3.4',
        ],
    },
    entry_points="""
    [console_scripts]
    bycycle = bycycle.core.__main__:bycycle.console_script

    """,
)
