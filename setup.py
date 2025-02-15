from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    requirements = f.read().splitlines()

setup(
    name='doc_organizer',
    version='0.1.0',
    packages=find_packages(),
    install_requires=requirements,
    python_requires='>=3.10',
    entry_points={
        'console_scripts': [
            'doc-organizer=doc_organizer.classifier:main',
        ],
    },
)