
import os
import sys
import shlex
import shutil
import tempfile
import subprocess
import contextlib

import Tkinter as tk
import tkFileDialog

import yaml
import click

from jinja2 import Environment, PackageLoader

import dtoolcore

ENV = Environment(loader=PackageLoader('jicgo', 'templates'),
                  keep_trailing_newline=True)

DATA_ROOT = '/Users/hartleym/data_repo'

__version__ = "0.0.1"


def identifiers_where_overlay_is_true(dataset, overlay_name):

    overlay = dataset.get_overlay(overlay_name)

    selected = [identifier
                for identifier in dataset.identifiers
                if overlay[identifier]]

    return selected


class DockerAssist(object):

    def __init__(self, image_name, base_command):
        self.image_name = image_name
        self.base_command = base_command
        self.volume_mounts = []

    def add_volume_mount(self, outside, inside):
        self.volume_mounts.append((outside, inside))

    @property
    def command(self):
        command_string = ['docker', 'run', '--rm']

        for outside, inside in self.volume_mounts:
            command_string += ['-v', '{}:{}'.format(outside, inside)]

        command_string += [self.image_name]

        command_string += shlex.split(self.base_command)

        return command_string

    @property
    def command_string(self):
        return ' '.join(self.command)

    def run(self, extra_args):
        command = self.command + shlex.split(extra_args)

        subprocess.call(command)

    def show_run_command(self, extra_args):
        command = self.command + shlex.split(extra_args)

        print(command)

    def run_and_capture_stdout(self):
        return subprocess.check_output(self.command)


@contextlib.contextmanager
def tmp_dir_context():
    d = tempfile.mkdtemp()
    try:
        yield d
    finally:
        shutil.rmtree(d)


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
def prodbuild():

    project_data = load_project()
    name = "{}-prod".format(project_data['name'])

    with tmp_dir_context() as d:

        cwd = os.getcwd()
        requirements_path = os.path.join(cwd, 'requirements.txt')
        shutil.copy(requirements_path, d)

        scripts_path = os.path.join(cwd, 'scripts')
        tarfile_path = os.path.join(d, 'scripts.tar.gz')

        tar_command = ['tar', '-zvcf', tarfile_path, 'scripts']

        subprocess.call(tar_command)

        dockerfile_path = os.path.join(d, 'Dockerfile')
        with open(dockerfile_path, 'w') as fh:
            template = ENV.get_template("Dockerfile.j2")
            fh.write(template.render(project_data))

        command = ['docker', 'build', '-t', name, d]

        subprocess.call(command)


@cli.command()
def singularity():

    project_data = load_project()
    production_docker_name = "{}-prod".format(project_data['name'])
    singularity_name = project_data['name']
    singularity_image_dir = project_data['singularity_image_dir']
    singularity_image_dir = os.path.abspath(singularity_image_dir)

    if not os.path.isdir(singularity_image_dir):
        os.mkdir(singularity_image_dir)

    build_command = [
        'docker',
        'run',
        '-v',
        '/var/run/docker.sock:/var/run/docker.sock',
        '-v',
        '{}:/output'.format(singularity_image_dir),
        '--privileged',
        '-t',
        '--rm',
        'mcdocker2singularity',
        production_docker_name,
        singularity_name
    ]

    print(' '.join(build_command))
    subprocess.call(build_command)


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
def singbuild():

    analysis = Analysis()

    production_docker_name = analysis.name + '-prod'

    docker_dir_path = os.path.join('docker', 'packed-for-cluster')

    command = ['docker', 'build', '-t', production_docker_name, docker_dir_path]

    subprocess.call(command)

    singularity_image_dir = analysis.config['singularity_image_dir']
    singularity_image_dir = os.path.abspath(singularity_image_dir)

    if not os.path.isdir(singularity_image_dir):
        os.mkdir(singularity_image_dir)

    build_command = [
        'docker',
        'run',
        '-v',
        '/var/run/docker.sock:/var/run/docker.sock',
        '-v',
        '{}:/output'.format(singularity_image_dir),
        '--privileged',
        '-t',
        '--rm',
        'mcdocker2singularity',
        production_docker_name,
        analysis.name
    ]

    print(' '.join(build_command))
    subprocess.call(build_command)


def run_script_in_project(project_data):

    container = project_data['container']

    # if 'dataset_path' in project_data:
    #     dataset_path = project_data['dataset_path']
    # elif 'dataset' in project_data:
    #     dataset = project_data['dataset']
    #     dataset_path = os.path.join(DATA_ROOT, dataset)
    # else:
    #     print("Must specify dataset (try jicgo data)")
    #     sys.exit(2)

    input_dataset_uri = project_data['input_dataset'].split(':')[1]
    output_dataset_uri = project_data['output_dataset'].split(':')[1]
    resource_dataset_uri = project_data['resource_dataset'].split(':')[1]

    script = project_data['script']

    cwd = os.getcwd()
    output_path = os.path.join(cwd, 'output')

    scripts_path = os.path.join(cwd, 'scripts')

    identifier = project_data['sample_identifier']

    base_command = "python /scripts/{} --dataset-uri disk:/data --identifier {} --resource-uri disk:/resource --output-uri disk:/output".format(
        script,
        identifier
    )

    input_dataset = dtoolcore.DataSet.from_uri(project_data['input_dataset'])
    resource_dataset = dtoolcore.DataSet.from_uri(project_data['resource_dataset'])
    output_dataset = dtoolcore.ProtoDataSet.from_uri(project_data['output_dataset'])

    click.secho("Running analysis:      ", nl=False)
    click.secho("{}".format(project_data['name']), fg='green')
    click.secho("Script:                ", nl=False)
    click.secho("{}".format(script), fg='yellow')
    click.secho("Input dataset:         ", nl=False)
    click.secho("{} ({})".format(input_dataset.name, project_data['input_dataset']), fg='cyan')
    click.secho("Resource dataset:      ", nl=False)
    click.secho("{} ({})".format(resource_dataset.name, project_data['resource_dataset']), fg='cyan')
    click.secho("Output dataset:        ", nl=False)
    click.secho("{} ({})".format(output_dataset.name, project_data['output_dataset']), fg='cyan')
    click.secho("Processing identifier: ", nl=False)
    click.secho("{} ({})".format(identifier, input_dataset.item_properties(identifier)['relpath']), fg='yellow')

    runner = DockerAssist(container, base_command)
    runner.add_volume_mount(input_dataset_uri, '/data')
    runner.add_volume_mount(resource_dataset_uri, '/resource')
    runner.add_volume_mount(output_dataset_uri, '/output')
    runner.add_volume_mount(scripts_path, '/scripts')

    runner.run()
    # print(runner.command)


@cli.command()
def test():

    project_data = load_project()

    test_script = project_data['test']

    run_script_in_project(test_script, project_data)


class Analysis(object):

    def __init__(self, analysis_file='analysis.yml'):

        with open(analysis_file) as fh:
            self.config = yaml.load(fh)

            self._input_dataset = None
            self._output_dataset = None

    @property
    def name(self):
        return self.config['name']

    @property
    def input_dataset(self):
        if self._input_dataset is None:
            self._input_dataset = dtoolcore.DataSet.from_uri(
                self.config['input_dataset_uri']
            )
        return self._input_dataset

    @property
    def output_dataset(self):
        if self._output_dataset is None:
            self._output_dataset = dtoolcore.ProtoDataSet.from_uri(
                self.config['output_dataset_uri']
            )
        return self._output_dataset

    @property
    def input_path(self):
        return self.config['input_dataset_uri'].split(':')[1]

    @property
    def output_path(self):
        return self.config['output_dataset_uri'].split(':')[1]

    def summary(self):

        click.secho("Analysis name:         ", nl=False)
        click.secho("{}".format(self.name), fg='green')
        # click.secho("Script:                ", nl=False)
        # click.secho("{}".format(script), fg='yellow')
        click.secho("Input dataset:         ", nl=False)
        click.secho("{} ({})".format(
            self.input_dataset.name,
            self.config['input_dataset_uri']
            ), fg='cyan')
        # click.secho("Resource dataset:      ", nl=False)
        # click.secho("{} ({})".format(resource_dataset.name, project_data['resource_dataset']), fg='cyan')
        click.secho("Output dataset:        ", nl=False)
        click.secho("{} ({})".format(
            self.output_dataset.name,
            self.config['output_dataset_uri']
            ), fg='cyan')

    def run(self):

        # run_script_in_project(self.config)

        cwd = os.getcwd()

        runner = DockerAssist(self.config['container'], self.base_command)
        runner.add_volume_mount(self.input_path, '/data')
        runner.add_volume_mount(self.output_path, '/output')
        runner.add_volume_mount(os.path.join(cwd, 'scripts'), '/scripts')

        runner.run(self.config['sample_identifier'])

    # FIXME - should be in a separate class, probably
    @property
    def base_command(self):
        command = ['python']
        command += ['/scripts/{}'.format(self.config['script'])]
        command += ['--dataset-uri', 'disk:/data']
        command += ['--output-uri', 'disk:/output']
        command += ['--identifier']

        return ' '.join(command)


def generate_rendered_job(analysis, template, identifier):

    cluster_config = analysis.config['runners']['cluster']

    job = {}
    job.update(cluster_config)

    command = 'python /scripts/{}'.format(analysis.config['script'])
    job['command'] = command
    job['identifier'] = identifier

    return template.render(job)


@cli.command()
def cluster():

    analysis = Analysis()

    identifiers = identifiers_where_overlay_is_true(
        analysis.input_dataset,
        'is_jpeg'
    )

    template = ENV.get_template("singularity_job.sh.j2")
    slurm_template = ENV.get_template("slurm_script_multiple.slurm.j2")

    jobs = [generate_rendered_job(analysis, template, i) for i in identifiers]

    params = {
        "partition": "rg-mh",
        "jobmem": "2048",
        "jobs": jobs
    }

    print(slurm_template.render(params))


@cli.command()
def run():

    analysis = Analysis()
    analysis.summary()

    print(analysis.base_command)

    analysis.run()

    # analysis.run()
    # project_data = load_project()

    # if 'script' in project_data:
    #     script = project_data['script']
    # else:
    #     script = 'analysis.py'

    # run_script_in_project(script, project_data)


if __name__ == '__main__':
    main()
