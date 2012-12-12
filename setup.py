from setuptools import setup, find_packages


setup(
    name='bycycle.core',
    version='0.5a2',
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
        'Programming Language :: Python :: 2.7',
    ],
    packages=find_packages(),
    zip_safe=False,
    install_requires=(
        'glineenc>=1.0',
        'Shapely>=1.2.16',
        'pyproj>=1.9.2',
        'psycopg2>=2.4.5',
        'SQLAlchemy>=0.8.0b1',
        'Dijkstar>=2.0b3',
    ),
    entry_points="""
    [console_scripts]
    bycycle-integrate = bycycle.core.scripts.integrate:main
    bycycle-matrix = bycycle.core.scripts.matrix:main
    """,
)
