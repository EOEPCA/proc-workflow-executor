from setuptools import setup, find_packages
import os


def package_files(where):
    paths = []
    for directory in where:
        for (path, directories, filenames) in os.walk(directory):
            for filename in filenames:
                paths.append(os.path.join(path, filename).replace('src/workflow_executor/', ''))
    return paths


extra_files = package_files(['src/workflow_executor/assets'])
#print(extra_files)

console_scripts = []

console_scripts.append('workflow-executor=workflow_executor.client:main')
console_scripts.append('workflow-executor-server=workflow_executor.fastapiserver:main')
#print(find_packages(where='src'))

setup(entry_points={'console_scripts': console_scripts},
      packages=find_packages(where='src'),
      package_dir={'': 'src'},
      package_data={'': extra_files})