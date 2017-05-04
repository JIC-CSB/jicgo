
import os
import subprocess

import yaml


DATA_ROOT = '/Users/hartleym/data_repo'


def do_some_magic():

    with open('project.yml') as fh:
        project_data = yaml.load(fh)

    container = project_data['container']
    dataset = project_data['dataset']

    print(container)
    print(dataset)

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

    command += ['python', '/scripts/analysis.py', '--debug', '--test', '/data', '/output']

    print(command)
    subprocess.call(command)




def main():
    do_some_magic()


if __name__ == '__main__':
    main()
