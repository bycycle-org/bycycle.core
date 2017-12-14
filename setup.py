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
        'boto3>=1.4.7',
        'Dijkstar>=2.3',
        'glineenc>=1.0',
        'psycopg2>=2.7.3.2',
        'pyproj>=1.9.5.1',
        'requests>=2.18.4',
        'runcommands>=1.0a26',
        'Shapely>=1.6.2',
        'SQLAlchemy>=1.1.15',
        'tangled>=1.0a12',
    ],
    extras_require={
        'dev': [
            'coverage>=4.4.2',
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
        'Programming Language :: Python :: 3.5',
    ],
)
