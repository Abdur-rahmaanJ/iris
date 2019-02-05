# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os

# import mozlog
# import mozversion
# from mozdownload import FactoryScraper, errors as download_errors
# from mozinstall import install, get_binary
# from mozrunner import FirefoxRunner, errors as runner_errors
import pytest

from src.base.target import *
from src.core.api.enums import Channels
from src.core.api.errors import APIHelperError
from src.core.api.os_helpers import OSHelper
from src.core.util.path_manager import PathManager
from targets.firefox.parse_args import parse_args
from targets.firefox.testrail.testcase_results import TestRailTests

logger = logging.getLogger(__name__)


class Target(BaseTarget):

    test_run_object_list = []

    def __init__(self):
        BaseTarget.__init__(self)
        self.target_name = 'Firefox'




        # path = self.get_test_candidate()
        # if path is None:
        #     raise ValueError
        #
        # self.path = path
        # self.channel = self.get_firefox_channel(path)
        # self.version = self.get_firefox_version(path)
        # self.build_id = self.get_firefox_build_id(path)
        # self.locale = parse_args().locale
        # self.latest_version = self.get_firefox_latest_version(path)

    @staticmethod
    def get_local_firefox_path():
        """Checks if Firefox is installed on your machine."""
        paths = {
            'osx': ['/Applications/Firefox.app/Contents/MacOS/firefox',
                    '/Applications/Firefox Developer Edition.app/Contents/MacOS/firefox',
                    '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'],
            'win': ['C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe',
                    'C:\\Program Files (x86)\\Firefox Developer Edition\\firefox.exe',
                    'C:\\Program Files (x86)\\Nightly\\firefox.exe',
                    'C:\\Program Files\\Mozilla Firefox\\firefox.exe',
                    'C:\\Program Files\\Firefox Developer Edition\\firefox.exe',
                    'C:\\Program Files\\Nightly\\firefox.exe'],
            'linux': ['/usr/bin/firefox',
                      '/usr/lib/firefox/firefox']
        }
        for path in paths[OSHelper.get_os()]:
            if os.path.exists(path):
                return path
        return None

    def get_test_candidate(self):
        """Download and extract a build candidate.

        Build may either refer to a Firefox release identifier, package, or build directory.
        :param: build: str with firefox build
        :return: Installation path for the Firefox App
        """

        if parse_args().firefox == 'local':
            candidate = self.get_local_firefox_path()
            if candidate is None:
                logger.critical(
                    'Firefox not found. Please download if from https://www.mozilla.org/en-US/firefox/new/')
        else:
            try:
                locale = 'ja-JP-mac' if parse_args().locale == 'ja' and OSHelper.is_mac() else parse_args().locale
                type, scraper_details = self.get_scraper_details(parse_args().firefox, Channels,
                                                                 os.path.join(
                                                                     PathManager.get_working_dir(), 'cache'),
                                                                 locale)
                scraper = FactoryScraper(type, **scraper_details)

                firefox_dmg = scraper.download()
                install_folder = install(src=firefox_dmg,
                                         dest=PathManager.get_current_run_dir())

                return get_binary(install_folder, 'Firefox')
            except download_errors.NotFoundError:
                logger.critical(
                    'Specified build (%s) has not been found. Closing Iris ...' % parse_args().firefox)
        return None

    def get_scraper_details(self, version, channels, destination, locale):
        """Generate scraper details from version.

        :param version: Can be a Firefox version (ex: 55.0, 55.0b3, etc.) or one of the following options:
                        beta, release, esr, local
        :param channels: A list of channels supported by Iris
        :param destination: Destination path where the Firefox installer will be saved
        :param locale: Firefox locale used
        :return: Scraper type followed by a dictionary that contains the version, destination and locale
        """
        if version in channels:
            version = self.map_latest_release_options(version)

            if version == 'nightly':
                return 'daily', {'branch': 'mozilla-central',
                                 'destination': destination,
                                 'locale': locale}
            else:
                return 'candidate', {'version': version,
                                     'destination': destination,
                                     'locale': locale}
        else:
            if '-dev' in version:
                return 'candidate', {'application': 'devedition',
                                     'version': version.replace('-dev', ''),
                                     'destination': destination,
                                     'locale': locale}

            elif not any(c.isalpha() for c in version) or any(x in version for x in ('b', 'esr')):
                return 'candidate', {'version': version,
                                     'destination': destination,
                                     'locale': locale}
            else:
                logger.warning(
                    'Version not recognized. Getting latest nightly build ...')
                return 'daily', {'branch': 'mozilla-central',
                                 'destination': destination,
                                 'locale': locale}

    @staticmethod
    def map_latest_release_options(release_option):
        """Overwrite Iris release options to be compatible with mozdownload."""
        if release_option == 'beta':
            return 'latest-beta'
        elif release_option == 'release':
            return 'latest'
        elif release_option == 'esr':
            return 'latest-esr'
        else:
            return 'nightly'

    def get_firefox_channel(self, build_path):
        """Returns Firefox channel from application repository.

        :param build_path: Path to the binary for the application or Android APK
        file.
        """

        if build_path is None:
            return None

        fx_channel = self.get_firefox_info(
            build_path)['application_repository']
        if 'beta' in fx_channel:
            return 'beta'
        elif 'release' in fx_channel:
            return 'release'
        elif 'esr' in fx_channel:
            return 'esr'
        else:
            return 'nightly'

    @staticmethod
    def get_firefox_info(build_path):
        """Returns the application version information as a dict with the help of
        mozversion library.

        :param build_path: Path to the binary for the application or Android APK
        file.
        """
        if build_path is None:
            return None

        mozlog.commandline.setup_logging('mozversion', None, {})
        return mozversion.get_version(binary=build_path)

    def get_firefox_version(self, build_path):
        """Returns application version string from the dictionary generated by
        mozversion library.

        :param build_path: Path to the binary for the application or Android APK
        file.
        """
        if build_path is None:
            return None
        return self.get_firefox_info(build_path)['application_version']

    def get_firefox_build_id(self, build_path):
        """Returns build id string from the dictionary generated by mozversion
        library.

        :param build_path: Path to the binary for the application or Android APK
        file.
        """
        if build_path is None:
            return None

        return self.get_firefox_info(build_path)['platform_buildid']

    def get_firefox_latest_version(self, binary):
        """Returns Firefox latest available version."""

        if binary is None:
            return None

        channel = self.get_firefox_channel(binary)
        latest_type, latest_scraper_details = self.get_latest_scraper_details(
            channel)
        latest_path = FactoryScraper(
            latest_type, **latest_scraper_details).filename

        latest_version = self.get_version_from_path(latest_path)
        logger.info('Latest available version for %s channel is: %s' %
                    (channel, latest_version))

        return latest_version

    def get_latest_scraper_details(self, channel):
        """Generate scraper details for the latest available Firefox version based on the channel provided as input."""
        channel = self.map_latest_release_options(channel)
        if channel == 'nightly':
            return 'daily', {'branch': 'mozilla-central'}
        else:
            return 'candidate', {'version': channel}

    @staticmethod
    def get_version_from_path(path):
        """Extracts a Firefox version from a path.

        Example:
        for input: '/Users/username/workspace/iris/firefox-62.0.3-build1.en-US.mac.dmg' output is '62.0.3'
        """
        new_str = path[path.find('-') + 1: len(path)]
        return new_str[0:new_str.find('-')]

    @staticmethod
    def firefox_session(path, profile=None, url=None, args=None, show_crash_reporter=False):
        """Launch the app with optional args for profile, windows, URI, etc.

        :param path: Firefox path.
        :param profile: Firefox profile.
        :param url: URL to be loaded.
        :param args: Optional list of arguments.
        :param show_crash_reporter: Enable or disable Firefox Crash Reporting tool.
        :return: List of Firefox flags.
        """
        if args is None:
            args = []

        if profile is None:
            raise APIHelperError('No profile name present, aborting run.')

        args.append('-foreground')
        args.append('-no-remote')

        if url is not None:
            args.append('-new-tab')
            args.append(url)

        process_args = {'stream': None}
        logger.debug('Creating Firefox runner ...')
        try:
            runner = FirefoxRunner(binary=path, profile=profile,
                                   cmdargs=args, process_args=process_args, show_crash_reporter=show_crash_reporter)
            logger.debug('Firefox runner successfully created.')
            logger.debug('Running Firefox with command: "%s"' %
                         ','.join(runner.command))
            return runner
        except runner_errors.RunnerNotStartedError:
            raise APIHelperError('Error creating Firefox runner.')

    #
    # def pytest_sessionstart(self, session):
    #     session.results = dict()
    #     print('\n\n** Firefox testing session {} started **\n'.format(session.name))

    @pytest.hookimpl(tryfirst=True, hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):

        outcome = yield
        report = outcome.get_result()

        if report.when == "call":
            test_case_instance = item.instance


            test_object_result = TestRailTests(test_case_instance.meta,
                                               test_case_instance.test_suite_id, test_case_instance.test_case_id,
                                               test_case_instance.blocked_by, test_case_instance.test_results)

            self.test_run_object_list.append(test_object_result)


        # item.session.results[item] = report

    def pytest_sessionfinish(self, session, exitstatus):
        """ called after whole test run finished, right before returning the exit status to the system.
            :param _pytest.main.Session session: the pytest session object
            :param int exitstatus: the status which pytest will return to the system
        """
        print("\n\n** Firefox App: Test session {} complete **\n".format(session.name))

        # print_result_footer(session, exitstatus)

        # if parse_args().email:
        #     submit_email_report(self.test_run_object_list)
        #
        # if parse_args().report:
        #     report_test_results(self.test_run_object_list)

