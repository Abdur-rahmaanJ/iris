# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


import json
import time

from src.core.api.enums import Alignment
from src.core.api.errors import APIHelperError
from src.core.api.errors import FindError
from src.core.api.finder.finder import wait, exists
from src.core.api.finder.image_search import image_find
from src.core.api.finder.pattern import Pattern
from src.core.api.keyboard.key import *
from src.core.api.keyboard.key import Key
from src.core.api.keyboard.keyboard import type, key_up, key_down
from src.core.api.keyboard.keyboard_api import paste
from src.core.api.keyboard.keyboard_util import get_clipboard
from src.core.api.location import Location
from src.core.api.mouse.mouse import click, hover, Mouse
from src.core.api.os_helpers import OSHelper, OSPlatform
from src.core.api.screen.region import Region
from src.core.api.screen.screen import Screen
from src.core.api.settings import Settings
from src.core.util.arg_parser import get_core_args
from src.core.util.logger_manager import logger
from targets.firefox.firefox_ui.content_blocking import ContentBlocking
from targets.firefox.firefox_ui.helpers.keyboard_shortcuts import new_tab, close_tab, edit_select_all, edit_copy
from targets.firefox.firefox_ui.helpers.keyboard_shortcuts import select_location_bar
from targets.firefox.firefox_ui.library_menu import LibraryMenu
from targets.firefox.firefox_ui.nav_bar import NavBar
from targets.firefox.firefox_ui.window_controls import MainWindow, AuxiliaryWindow

INVALID_GENERIC_INPUT = 'Invalid input'
INVALID_NUMERIC_INPUT = 'Expected numeric value'
args = get_core_args()


def access_bookmarking_tools(option):
    """Access option from 'Bookmarking Tools'.

    :param option: Option from 'Bookmarking Tools'.
    :return: None.
    """

    bookmarking_tools_pattern = LibraryMenu.BookmarksOption.BOOKMARKING_TOOLS
    open_library_menu(LibraryMenu.BOOKMARKS_OPTION)

    try:
        wait(bookmarking_tools_pattern, 10)
        logger.debug('Bookmarking Tools option has been found.')
        click(bookmarking_tools_pattern)
    except FindError:
        raise APIHelperError(
            'Can\'t find the Bookmarking Tools option, aborting.')
    try:
        wait(option, 15)
        logger.debug('%s option has been found.' % option)
        click(option)
    except FindError:
        raise APIHelperError('Can\'t find the %s option, aborting.' % option)


def change_preference(pref_name, value):
    """Change the value for a specific preference.

    :param pref_name: Preference to be changed.
    :param value: Preference's value after the change.
    :return: None.
    """
    try:
        new_tab()
        navigate('about:config')
        time.sleep(Settings.DEFAULT_UI_DELAY)

        type(Key.SPACE)
        time.sleep(Settings.DEFAULT_UI_DELAY)

        type(Key.ENTER)
        time.sleep(Settings.DEFAULT_UI_DELAY)

        paste(pref_name)
        time.sleep(Settings.DEFAULT_UI_DELAY)
        type(Key.TAB)
        time.sleep(Settings.DEFAULT_UI_DELAY)
        type(Key.TAB)
        time.sleep(Settings.DEFAULT_UI_DELAY)

        try:
            retrieved_value = copy_to_clipboard()
        except Exception:
            raise APIHelperError(
                'Failed to retrieve preference value.')

        if retrieved_value == value:
            logger.debug('Flag is already set to value:' + value)
            return None
        else:
            type(Key.ENTER)
            dialog_box_pattern = Pattern('preference_dialog_icon.png')
            try:
                wait(dialog_box_pattern, 3)
                paste(value)
                type(Key.ENTER)
            except FindError:
                pass

        close_tab()
    except Exception:
        raise APIHelperError(
            'Could not set value: %s to preference: %s' % (value, pref_name))


def copy_to_clipboard():
    """Return the value copied to clipboard."""
    time.sleep(Settings.DEFAULT_UI_DELAY)
    edit_select_all()
    time.sleep(Settings.DEFAULT_UI_DELAY)
    edit_copy()
    time.sleep(Settings.DEFAULT_UI_DELAY)
    value = get_clipboard()
    time.sleep(Settings.DEFAULT_UI_DELAY)
    logger.debug("Copied to clipboard: %s" % value)
    return value


def close_content_blocking_pop_up():
    """Closes the content blocking pop up"""

    pop_up_region = Screen().new_region(0, 50, Screen.SCREEN_WIDTH / 2, Screen.SCREEN_HEIGHT / 2)

    try:
        pop_up_region.wait(ContentBlocking.POP_UP_ENABLED, 5)
        logger.debug('Content blocking is present on the page and can be closed.')
        pop_up_region.click(ContentBlocking.CLOSE_CB_POP_UP)
    except FindError:
        logger.debug('Couldn\'t find the Content blocking pop up.')
        pass


def close_window_control(window_type):
    """Click on close window control.

    :param window_type: Type of window that need to be closed.
    :return: None.
    """
    find_window_controls(window_type)

    if window_type == 'auxiliary':
        if OSHelper.is_mac():
            hover(AuxiliaryWindow.RED_BUTTON_PATTERN)
            click(AuxiliaryWindow.HOVERED_RED_BUTTON)
        else:
            click(AuxiliaryWindow.CLOSE_BUTTON)
    else:
        if OSHelper.is_mac():
            hover(MainWindow.UNHOVERED_MAIN_RED_CONTROL)
            click(MainWindow.HOVERED_MAIN_RED_CONTROL)
        else:
            click(MainWindow.CLOSE_BUTTON)


def click_hamburger_menu_option(option):
    """Click on a specific option from the hamburger menu.

    :param option: Hamburger menu option to be clicked.
    :return: The region created starting from the hamburger menu pattern.
    """
    hamburger_menu_pattern = NavBar.HAMBURGER_MENU
    try:
        wait(hamburger_menu_pattern, 10)
        logger.debug('Hamburger menu found.')
    except FindError:
        raise APIHelperError(
            'Can\'t find the "hamburger menu" in the page, aborting test.')
    else:
        click(hamburger_menu_pattern)
        time.sleep(Settings.DEFAULT_UI_DELAY)
        try:
            region = create_region_from_image(hamburger_menu_pattern)
            region.click(option)
            return region
        except FindError:
            raise APIHelperError(
                'Can\'t find the option in the page, aborting test.')


def click_window_control(button, window_type='auxiliary'):
    """Click window with options: close, minimize, maximize, restore, full_screen.

    :param button: Auxiliary or main window options.
    :param window_type: Type of window that need to be controlled.
    :return: None.
    """
    if button == 'close':
        close_window_control(window_type)
    elif button == 'minimize':
        minimize_window_control(window_type)
    elif button == 'maximize':
        maximize_window_control(window_type)
    elif button == 'restore':
        restore_window_control(window_type)
    elif button == 'full_screen':
        full_screen_control(window_type)
    else:
        raise APIHelperError('Button option is not supported.')


def confirm_firefox_launch(image=None):
    """Waits for firefox to exist by waiting for the iris logo to be present.
    :param image: Pattern to confirm Firefox launch
    :return: None.
    """
    if image is None:
        image = Pattern('iris_logo.png')

    try:
        wait(image, 60)
    except Exception:
        raise APIHelperError('Can\'t launch Firefox - aborting test run.')


def create_region_from_image(image):
    """Create region starting from a pattern.

    :param image: Pattern used to create a region.
    :return: None.
    """
    try:
        from src.core.api.rectangle import Rectangle
        from src.core.api.enums import Alignment
        m = image_find(image)
        if m:
            sync_pattern = Pattern('sync_hamburger_menu.png')
            sync_width, sync_height = sync_pattern.get_size()
            sync_image = image_find(sync_pattern)
            top_left = Rectangle(sync_image.x, sync_image.y, sync_width, sync_width). \
                apply_alignment(Alignment.TOP_RIGHT)
            if OSHelper.is_mac():
                exit_pattern = Pattern('help_hamburger_menu.png')
            else:
                exit_pattern = Pattern('exit_hamburger_menu.png')
            exit_width, exit_height = exit_pattern.get_size()
            exit_image = image_find(exit_pattern)
            bottom_left = Rectangle(exit_image.x, exit_image.y, exit_width, exit_height). \
                apply_alignment(Alignment.BOTTOM_RIGHT)

            x0 = top_left.x + 2
            y0 = top_left.y
            height = bottom_left.y - top_left.y
            width = Screen().width - top_left.x - 2
            region = Region(x0, y0, width, height)
            return region
        else:
            raise APIHelperError('No matching found.')
    except FindError:
        raise APIHelperError('Image not present.')


def find_window_controls(window_type):
    """Find window controls for main and auxiliary windows.

    :param window_type: Controls for a specific window type.
    :return: None.
    """
    if window_type == 'auxiliary':
        Mouse().move(Location(1, 300))
        if OSHelper.is_mac():
            try:
                wait(AuxiliaryWindow.RED_BUTTON_PATTERN.similar(0.9), 5)
                logger.debug('Auxiliary window control found.')
            except FindError:
                raise APIHelperError('Can\'t find the auxiliary window controls, aborting.')
        else:
            if OSHelper.is_linux():
                Mouse().move(Location(80, 0))
            try:
                wait(AuxiliaryWindow.CLOSE_BUTTON, 5)
                logger.debug('Auxiliary window control found.')
            except FindError:
                raise APIHelperError(
                    'Can\'t find the auxiliary window controls, aborting.')

    elif window_type == 'main':
        if OSHelper.is_mac():
            try:
                wait(MainWindow.MAIN_WINDOW_CONTROLS.similar(0.9), 5)
                logger.debug('Main window controls found.')
            except FindError:
                raise APIHelperError('Can\'t find the Main window controls, aborting.')
        else:
            try:
                if OSHelper.is_linux():
                    reset_mouse()
                wait(MainWindow.CLOSE_BUTTON, 5)
                logger.debug('Main window control found.')
            except FindError:
                raise APIHelperError(
                    'Can\'t find the Main window controls, aborting.')
    else:
        raise APIHelperError('Window Type not supported.')


def full_screen_control(window_type):
    """Click on full screen window mode (Applicable only for MAC system).

    :param window_type: Type of window that need to be maximized in full screen mode.
    :reurn: None.
    """
    if OSHelper.is_mac():
        find_window_controls(window_type)

        if window_type == 'auxiliary':
            width, height = AuxiliaryWindow.AUXILIARY_WINDOW_CONTROLS.get_size()
            click(AuxiliaryWindow.AUXILIARY_WINDOW_CONTROLS.target_offset(width - 10, height / 2),
                  align=Alignment.TOP_LEFT)
        else:
            width, height = MainWindow.MAIN_WINDOW_CONTROLS.get_size()
            click(MainWindow.MAIN_WINDOW_CONTROLS.target_offset(width - 10, height / 2), align=Alignment.TOP_LEFT)
    else:
        raise APIHelperError('Full screen mode applicable only for MAC')


def repeat_key_down(num):
    """Repeat DOWN keystroke a given number of times.

    :param num: Number of times to repeat DOWN key stroke.
    :return: None.
    """
    for i in range(num):
        type(Key.DOWN)


def repeat_key_down_until_image_found(image_pattern, num_of_key_down_presses=10, delay_between_presses=3):
    """
    Press the Key Down button until specified image pattern is found.

    :param image_pattern: Image Pattern to search.
    :param num_of_key_down_presses: Number of presses of the Key Down button.
    :param delay_between_presses: Number of seconds to wait between the Key Down presses
    :return: Boolean. True if image pattern found during Key Down button pressing, False otherwise
    """

    if not isinstance(image_pattern, Pattern):
        raise ValueError(INVALID_GENERIC_INPUT)

    pattern_found = False

    for _ in range(num_of_key_down_presses):
        pattern_found = exists(image_pattern)
        if pattern_found:
            break

        type(Key.DOWN)
        time.sleep(delay_between_presses)

    return pattern_found


def repeat_key_up(num):
    """Repeat UP keystroke a given number of times.

    :param num: Number of times to repeat UP key stroke.
    :return: None.
    """
    for i in range(num):
        type(Key.UP)


def restore_window_control(window_type):
    """Click on restore window control.

    :param window_type: Type of window that need to be restored.
    :return: None.
    """
    find_window_controls(window_type)

    if window_type == 'auxiliary':
        if OSHelper.is_mac():
            key_down(Key.ALT)
            width, height = AuxiliaryWindow.AUXILIARY_WINDOW_CONTROLS.get_size()
            click(AuxiliaryWindow.AUXILIARY_WINDOW_CONTROLS.target_offset(width - 10, height / 2),
                  align=Alignment.TOP_LEFT)
            key_up(Key.ALT)
        else:
            if OSHelper.is_linux():
                reset_mouse()
            click(AuxiliaryWindow.ZOOM_RESTORE_BUTTON)
    else:
        if OSHelper.is_mac():
            key_down(Key.ALT)
            width, height = MainWindow.MAIN_WINDOW_CONTROLS.get_size()
            click(MainWindow.MAIN_WINDOW_CONTROLS.target_offset(width - 10, height / 2), align=Alignment.TOP_LEFT)
            key_up(Key.ALT)
        else:
            if OSHelper.is_linux():
                reset_mouse()
            click(MainWindow.RESIZE_BUTTON)


def repeat_key_up_until_image_found(image_pattern, num_of_key_up_presses=10, delay_between_presses=3):
    """
    Press the Key Up button until specified image pattern is found.

    :param image_pattern: Image Pattern to search.
    :param num_of_key_up_presses: Number of presses of the Key Up button.
    :param delay_between_presses: Number of seconds to wait between the Key Down presses
    :return: Boolean. True if image pattern found during the Key Up button pressing, False otherwise
    """

    if not isinstance(image_pattern, Pattern):
        raise ValueError(INVALID_GENERIC_INPUT)

    pattern_found = False

    for _ in range(num_of_key_up_presses):
        pattern_found = exists(image_pattern)
        if pattern_found:
            break

        type(Key.UP)
        time.sleep(delay_between_presses)

    return pattern_found


def reset_mouse():
    """Reset mouse position to location (0, 0)."""
    Mouse().move(Location(0, 0))


def select_location_bar_option(option_number):
    """Select option from the location bar menu.

    :param option_number: Option number.
    :return: None.
    """
    if OSHelper.get_os() == OSPlatform.WINDOWS:
        for i in range(option_number + 1):
            type(Key.DOWN)
        type(Key.ENTER)
    else:
        for i in range(option_number - 1):
            type(Key.DOWN)
        type(Key.ENTER)


def key_to_one_off_search(highlighted_pattern, direction='left'):
    """Iterate through the one of search engines list until the given one is
    highlighted.

    param: highlighted_pattern: The pattern image to search for.
    param: direction: direction to key to: right or left (default)
    return: None.
    """
    max_attempts = 7
    while max_attempts > 0:
        if exists(highlighted_pattern, 1):
            max_attempts = 0
        else:
            if direction == 'right':
                type(Key.RIGHT)
            else:
                type(Key.LEFT)
            max_attempts -= 1


def minimize_window_control(window_type):
    """Click on minimize window control.

    :param window_type: Type of window that need to be minimized.
    :return: None.
    """
    find_window_controls(window_type)

    if window_type == 'auxiliary':
        if OSHelper.is_mac():
            width, height = AuxiliaryWindow.AUXILIARY_WINDOW_CONTROLS.get_size()
            click(AuxiliaryWindow.AUXILIARY_WINDOW_CONTROLS.target_offset(width / 2, height / 2),
                  align=Alignment.TOP_LEFT)
        else:
            click(AuxiliaryWindow.MINIMIZE_BUTTON)
    else:
        if OSHelper.is_mac():
            width, height = MainWindow.MAIN_WINDOW_CONTROLS.get_size()
            click(MainWindow.MAIN_WINDOW_CONTROLS.target_offset(width / 2, height / 2), align=Alignment.TOP_LEFT)
        else:
            click(MainWindow.MINIMIZE_BUTTON)


def maximize_window_control(window_type):
    """Click on maximize window control.

    :param window_type: Type of window that need to be maximized.
    :return: None.
    """
    find_window_controls(window_type)

    if window_type == 'auxiliary':
        if OSHelper.is_mac():
            key_down(Key.ALT)
            width, height = AuxiliaryWindow.AUXILIARY_WINDOW_CONTROLS.get_size()
            click(AuxiliaryWindow.AUXILIARY_WINDOW_CONTROLS.target_offset(width - 10, height / 2),
                  align=Alignment.TOP_LEFT)
            key_up(Key.ALT)
        else:
            click(AuxiliaryWindow.MAXIMIZE_BUTTON)
            if OSHelper.is_linux():
                reset_mouse()
    else:
        if OSHelper.is_mac():
            key_down(Key.ALT)
            width, height = MainWindow.MAIN_WINDOW_CONTROLS.get_size()
            click(MainWindow.MAIN_WINDOW_CONTROLS.target_offset(width - 10, height / 2), align=Alignment.TOP_LEFT)
            key_up(Key.ALT)
        else:
            click(MainWindow.MAXIMIZE_BUTTON)


def navigate(url):
    """Navigates, via the location bar, to a given URL.

    :param url: The string to type into the location bar.
    :return: None.
    """
    try:
        select_location_bar()
        paste(url)
        type(Key.ENTER)
    except Exception:
        raise APIHelperError(
            'No active window found, cannot navigate to page.')


def open_library_menu(option):
    """Open the Library menu with an option as argument.

    :param option: Library menu option.
    :return: Custom region created for a more efficient and accurate image
    pattern search.
    """

    library_menu_pattern = NavBar.LIBRARY_MENU

    try:
        wait(library_menu_pattern, 10)
        region = Region(image_find(library_menu_pattern).x - Screen().width / 4,
                        image_find(library_menu_pattern).y, Screen().width / 4,
                        Screen().height / 4)
        logger.debug('Library menu found.')
    except FindError:
        raise APIHelperError(
            'Can\'t find the library menu in the page, aborting test.')
    else:
        time.sleep(Settings.DEFAULT_UI_DELAY_LONG)
        click(library_menu_pattern)
        time.sleep(Settings.DEFAULT_UI_DELAY_SHORT)
        try:
            time.sleep(Settings.DEFAULT_UI_DELAY_SHORT)
            region.wait(option, 10)
            logger.debug('Option found.')
            region.click(option)
            return region
        except FindError:
            raise APIHelperError(
                'Can\'t find the option in the page, aborting test.')


def open_about_firefox():
    """Open the 'About Firefox' window."""
    if OSHelper.get_os() == OSPlatform.MAC:
        type(Key.F3, modifier=KeyModifier.CTRL)
        type(Key.F2, modifier=KeyModifier.CTRL)

        time.sleep(0.5)
        type(Key.RIGHT)
        type(Key.DOWN)
        type(Key.DOWN)
        type(Key.ENTER)

    elif OSHelper.get_os() == OSPlatform.WINDOWS:
        type(Key.ALT)
        if args.locale != 'ar':
            type(Key.LEFT)
        else:
            type(Key.RIGHT)
        type(Key.ENTER)
        type(Key.UP)
        type(Key.ENTER)

    else:
        type(Key.F10)
        if args.locale != 'ar':
            type(Key.LEFT)
        else:
            type(Key.RIGHT)
        type(Key.UP)
        type(Key.ENTER)


def get_telemetry_info():
    """Returns telemetry information as a JSON object from 'about:telemetry'
    page.
    """

    copy_raw_data_to_clipboard_pattern = Pattern(
        'copy_raw_data_to_clipboard.png')
    raw_json_pattern = Pattern('raw_json.png')
    raw_data_pattern = Pattern('raw_data.png')

    new_tab()

    paste('about:telemetry')
    type(Key.ENTER)

    try:
        wait(raw_json_pattern, 10)
        logger.debug('\'RAW JSON\' button is present on the page.')
        click(raw_json_pattern)
    except (FindError, ValueError):
        raise APIHelperError('\'RAW JSON\' button not present in the page.')

    try:
        wait(raw_data_pattern, 10)
        logger.debug('\'Raw Data\' button is present on the page.')
        click(raw_data_pattern)
    except (FindError, ValueError):
        close_tab()
        raise APIHelperError('\'Raw Data\' button not present in the page.')

    try:
        click(copy_raw_data_to_clipboard_pattern)
        time.sleep(Settings.DEFAULT_UI_DELAY)
        json_text = get_clipboard()
        return json.loads(json_text)
    except Exception:
        raise APIHelperError('Failed to retrieve raw message information value.')
    finally:
        close_tab()


class RightClickLocationBar:
    """Class with location bar members."""

    UNDO = 0
    CUT = 1
    COPY = 2
    PASTE = 3
    PASTE_GO = 4
    DELETE = 5
    SELECT_ALL = 6


def restore_firefox_focus():
    """Restore Firefox focus by clicking the panel near HOME or REFRESH button."""

    try:
        if exists(NavBar.HOME_BUTTON, Settings.DEFAULT_UI_DELAY):
            target_pattern = NavBar.HOME_BUTTON
        else:
            target_pattern = NavBar.RELOAD_BUTTON
        w, h = target_pattern.get_size()
        horizontal_offset = w * 1.7
        click_area = target_pattern.target_offset(horizontal_offset, 0)
        click(click_area)
    except FindError:
        raise APIHelperError('Could not restore firefox focus.')


def get_pref_value(pref_name):
    """Returns the value of a provided preference from 'about:config' page.

    :param pref_name: Preference's name.
    :return: Preference's value.
    """

    new_tab()
    select_location_bar()
    paste('about:config')
    type(Key.ENTER)
    time.sleep(Settings.DEFAULT_UI_DELAY)

    type(Key.SPACE)
    time.sleep(Settings.DEFAULT_UI_DELAY)

    paste(pref_name)
    time.sleep(Settings.DEFAULT_UI_DELAY_LONG)
    type(Key.TAB)
    time.sleep(Settings.DEFAULT_UI_DELAY_LONG)

    try:
        value = copy_to_clipboard().split(';'[0])[1]
    except Exception as e:
        raise APIHelperError(
            'Failed to retrieve preference value.\n{}'.format(e))

    close_tab()
    return value


def get_firefox_version_from_about_config():
    """Returns the Firefox version from 'about:config' page."""

    try:
        return get_pref_value('extensions.lastAppVersion')
    except APIHelperError:
        raise APIHelperError('Could not retrieve firefox version information from about:config page.')


def get_firefox_build_id_from_about_config():
    """Returns the Firefox build id from 'about:config' page."""
    pref_1 = 'browser.startup.homepage_override.buildID'
    pref_2 = 'extensions.lastAppBuildId'

    try:
        return get_pref_value(pref_1)
    except APIHelperError:
        try:
            return get_pref_value(pref_2)
        except APIHelperError:
            raise APIHelperError('Could not retrieve firefox build id information from about:config page.')


def get_firefox_channel_from_about_config():
    """Returns the Firefox channel from 'about:config' page."""
    try:
        return get_pref_value('app.update.channel')
    except APIHelperError:
        raise APIHelperError('Could not retrieve firefox channel information from about:config page.')


def get_firefox_locale_from_about_config():
    """Returns the Firefox locale from 'about:config' page."""
    try:
        value_str = get_pref_value('browser.newtabpage.activity-stream.feeds.section.topstories.options')
        logger.debug(value_str)
        temp = json.loads(value_str)
        return str(temp['stories_endpoint']).split('&locale_lang=')[1].split('&')[0]
    except (APIHelperError, KeyError):
        raise APIHelperError('Pref format to determine locale has changed.')


def get_support_info():
    """Returns support information as a JSON object from 'about:support' page."""
    copy_raw_data_to_clipboard = Pattern('about_support_copy_raw_data_button.png')

    new_tab()
    select_location_bar()
    paste('about:support')
    type(Key.ENTER)
    time.sleep(Settings.DEFAULT_UI_DELAY)

    try:
        click(copy_raw_data_to_clipboard)
        time.sleep(Settings.DEFAULT_UI_DELAY_LONG)
        json_text = get_clipboard()
        return json.loads(json_text)
    except Exception as e:
        raise APIHelperError('Failed to retrieve support information value.\n{}'.format(e))
    finally:
        close_tab()


def restore_window_from_taskbar(option=None):
    """Restore firefox from task bar."""
    if OSHelper.is_mac():
        try:
            click(Pattern('main_menu_window.png'))
            if option == "browser_console":
                click(Pattern('window_browser_console.png'))
            else:
                click(Pattern('window_firefox.png'))
        except FindError:
            raise APIHelperError('Restore window from taskbar unsuccessful.')
    elif OSHelper.get_os_version() == 'win7':
        try:
            click(Pattern('firefox_start_bar.png'))
            if option == "library_menu":
                click(Pattern('firefox_start_bar_library.png'))
            if option == "browser_console":
                click(Pattern('firefox_start_bar_browser_console.png'))
        except FindError:
            raise APIHelperError('Restore window from taskbar unsuccessful.')

    else:
        type(text=Key.TAB, modifier=KeyModifier.ALT)
        if OSHelper.is_linux():
            Mouse().move(Location(0, 50))
    time.sleep(Settings.DEFAULT_UI_DELAY)


def close_customize_page():
    """Close the 'Customize...' page by pressing the 'Done' button."""
    customize_done_button_pattern = Pattern('customize_done_button.png')
    try:
        wait(customize_done_button_pattern, 10)
        logger.debug('Done button found.')
        click(customize_done_button_pattern)
    except FindError:
        raise APIHelperError(
            'Can\'t find the Done button in the page, aborting.')


def click_cancel_button():
    """Click cancel button."""
    cancel_button_pattern = Pattern('cancel_button.png')
    try:
        wait(cancel_button_pattern, 10)
        logger.debug('Cancel button found.')
        click(cancel_button_pattern)
    except FindError:
        raise APIHelperError('Can\'t find the cancel button, aborting.')
