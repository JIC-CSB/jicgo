
import os
import sys
import shutil
import subprocess

import Tkinter as tk
import tkFileDialog

import yaml
import click


DATA_ROOT = '/Users/hartleym/data_repo'

__version__ = "0.0.1"


def load_project(fpath='project.yml'):

    with open('project.yml') as fh:
        project_data = yaml.load(fh)

    return project_data


@click.group()
def cli():
    pass


@cli.command()
def data():
    root = tk.Tk()
    root.withdraw()
    data_dir_path = tkFileDialog.askdirectory()

    project_data = load_project()
    project_data['dataset_path'] = data_dir_path

    with open('project.yml', 'w') as fh:
        fh.write(yaml.dump(project_data))


@cli.command()
def build():

    project_data = load_project()

    name = project_data['name']

    cwd = os.getcwd()

    docker_dir_path = os.path.join(cwd, 'docker', name)

    dockerfile_path = os.path.join(docker_dir_path, 'Dockerfile')

    if not os.path.isfile(dockerfile_path):
        print("Can't find Dockerfile at expected location: {}".format(
            dockerfile_path)
        )
        sys.exit(2)

    requirements_path = os.path.join(cwd, 'requirements.txt')

    shutil.copy(requirements_path, docker_dir_path)

    command = ['docker', 'build', '-t', name, docker_dir_path]

    print(' '.join(command))
    subprocess.call(command)

    project_data['container'] = name

    with open('project.yml', 'w') as fh:
        fh.write(yaml.dump(project_data))


@cli.command()
def run():

    project_data = load_project()

    container = project_data['container']

    if 'dataset_path' in project_data:
        dataset_path = project_data['dataset_path']
    elif 'dataset' in project_data:
        dataset = project_data['dataset']
        dataset_path = os.path.join(DATA_ROOT, dataset)
    else:
        print("Must specify dataset (try jicgo data)")
        sys.exit(2)

    if 'script' in project_data:
        script = project_data['script']
    else:
        script = 'analysis.py'

    command = ['docker', 'run', '-it', '--rm']

    cwd = os.getcwd()

    scripts_path = os.path.join(cwd, 'scripts')
    scripts_volume_mount = "{}:/scripts:ro".format(scripts_path)
    command += ['-v', scripts_volume_mount]

    output_path = os.path.join(cwd, 'output')
    output_volume_mount = "{}:/output".format(output_path)
    command += ['-v', output_volume_mount]

    data_volume_mount = "{}:/data:ro".format(dataset_path)
    command += ['-v', data_volume_mount]

    command += [container]

    command += ['python',
                os.path.join('/scripts', script),
                # '--debug',
                '/data',
                '/output']

    print(command)
    subprocess.call(command)




if __name__ == '__main__':
    main()
