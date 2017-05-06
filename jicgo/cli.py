
import os
import subprocess

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
def run():

    project_data = load_project()

    container = project_data['container']
    dataset = project_data['dataset']

    command = ['docker', 'run', '-it', '--rm']

    cwd = os.getcwd()

    scripts_path = os.path.join(cwd, 'scripts')
    scripts_volume_mount = "{}:/scripts:ro".format(scripts_path)
    command += ['-v', scripts_volume_mount]

    output_path = os.path.join(cwd, 'output')
    output_volume_mount = "{}:/output".format(output_path)
    command += ['-v', output_volume_mount]

    data_path = os.path.join(DATA_ROOT, dataset)
    data_volume_mount = "{}:/data:ro".format(data_path)
    command += ['-v', data_volume_mount]

    command += [container]

    command += ['python',
                '/scripts/analysis.py',
                '--debug',
                '--test',
                '/data',
                '/output']

    print(command)
    subprocess.call(command)




if __name__ == '__main__':
    main()
