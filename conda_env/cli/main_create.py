from __future__ import print_function
from argparse import RawDescriptionHelpFormatter
import os
import textwrap
import sys

from conda.cli import common
from conda.cli import install as cli_install
from conda.misc import touch_nonadmin

from ..env import from_file
from ..installers.base import get_installer, InvalidInstaller
from .. import exceptions
from .. import specs

description = """
Create an environment based on an environment file
"""

example = """
examples:
    conda env create
    conda env create vader/deathstar
    conda env create -f=/path/to/environment.yml
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'create',
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )
    p.add_argument(
        '-f', '--file',
        action='store',
        help='environment definition file (default: environment.yml)',
        default='environment.yml',
    )
    p.add_argument(
        '-n', '--name',
        action='store',
        help='environment definition [Deprecated]',
        default=None,
        dest='old_name'
    )
    p.add_argument(
        '-q', '--quiet',
        action='store_false',
        default=False,
    )
    p.add_argument(
        'name',
        help='environment definition',
        action='store',
        default=None,
        nargs='?'
    )
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):

    name = None
    if args.old_name:
        print("--name is deprecated. Use the following command instead:\n"
              "    conda env create {}".format(args.old_name), file=sys.stderr)
        name = args.old_name
    elif args.name:
        name = args.name

    try:
        spec = specs.detect(name=name, filename=args.file,
                            directory=os.getcwd())
        env = spec.environment
        # FIXME conda code currently requires args to have a name or prefix
        args.name = env.name
    except exceptions.EnvironmentFileNotFound as e:
        common.error_and_exit(str(e), json=args.json)

    prefix = common.get_prefix(args, search=False)
    cli_install.check_prefix(prefix, json=args.json)

    # TODO, add capability
    # common.ensure_override_channels_requires_channel(args)
    # channel_urls = args.channel or ()

    for installer_type, pkg_specs in env.dependencies.items():
        try:
            installer = get_installer(installer_type)
            installer.install(prefix, pkg_specs, args, env)
        except InvalidInstaller:
            sys.stderr.write(textwrap.dedent("""
                Unable to install package for {0}.

                Please double check and ensure you dependencies file has
                the correct spelling.  You might also try installing the
                conda-env-{0} package to see if provides the required
                installer.
                """).lstrip().format(installer_type)
            )
            return -1

    touch_nonadmin(prefix)
    if not args.json:
        cli_install.print_activate(args.name if args.name else prefix)
