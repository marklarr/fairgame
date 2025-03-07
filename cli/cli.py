#      FairGame - Automated Purchasing Program
#      Copyright (C) 2021  Hari Nagarajan
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU General Public License as published by
#      the Free Software Foundation, either version 3 of the License, or
#      (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU General Public License for more details.
#
#      You should have received a copy of the GNU General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#      The author may be contacted through the project's GitHub, at:
#      https://github.com/Hari-Nagarajan/fairgame

import os
import platform
import shutil
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from signal import SIGINT, signal

import click

from common.globalconfig import AMAZON_CREDENTIAL_FILE, GlobalConfig
from notifications.notifications import NotificationHandler, TIME_FORMAT
from stores.amazon import Amazon
from utils.logger import log
from utils.version import is_latest, version, get_latest_version

LICENSE_PATH = os.path.join(
    "cli",
    "license",
)


def get_folder_size(folder):
    return sizeof_fmt(sum(file.stat().st_size for file in Path(folder).rglob("*")))


def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)


# see https://docs.python.org/3/library/signal.html
def interrupt_handler(signal_num, frame):
    log.info(f"Caught the interrupt signal.  Exiting.")
    exit(0)


def notify_on_crash(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except KeyboardInterrupt:
            pass
        else:
            notification_handler.send_notification(f"FairGame has crashed.")
            raise

    return decorator


@click.group()
def main():
    pass


# @click.command()
# @click.option(
#     "--gpu",
#     type=click.Choice(GPU_DISPLAY_NAMES, case_sensitive=False),
#     prompt="What GPU are you after?",
#     cls=QuestionaryOption,
# )
# @click.option(
#     "--locale",
#     type=click.Choice(CURRENCY_LOCALE_MAP.keys(), case_sensitive=False),
#     prompt="What locale shall we use?",
#     cls=QuestionaryOption,
# )
# @click.option("--test", is_flag=True)
# @click.option("--interval", type=int, default=5)
# @notify_on_crash
# def nvidia(gpu, locale, test, interval):
#     nv = NvidiaBuyer(
#         gpu,
#         notification_handler=notification_handler,
#         locale=locale,
#         test=test,
#         interval=interval,
#     )
#     nv.run_items()


@click.command()
@click.option("--no-image", is_flag=True, help="Do not load images")
@click.option("--headless", is_flag=True, help="Headless mode.")
@click.option(
    "--test",
    is_flag=True,
    help="Run the checkout flow, but do not actually purchase the item[s]",
)
@click.option(
    "--delay", type=float, default=3.0, help="Time to wait between checks for item[s]"
)
@click.option(
    "--checkshipping",
    is_flag=True,
    help="Factor shipping costs into reserve price and look for items with a shipping price",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Take more screenshots. !!!!!! This could cause you to miss checkouts !!!!!!",
)
@click.option(
    "--used",
    is_flag=True,
    help="Show used items in search listings.",
)
@click.option("--single-shot", is_flag=True, help="Quit after 1 successful purchase")
@click.option(
    "--no-screenshots",
    is_flag=True,
    help="Take NO screenshots, do not bother asking for help if you use this... Screenshots are the best tool we have for troubleshooting",
)
@click.option(
    "--disable-presence",
    is_flag=True,
    help="Disable Discord Rich Presence functionallity",
)
@click.option(
    "--disable-sound",
    is_flag=True,
    default=False,
    help="Disable local sounds.  Does not affect Apprise notification " "sounds.",
)
@click.option(
    "--slow-mode",
    is_flag=True,
    default=False,
    help="Uses normal page load strategy for selenium. Default is none",
)
@click.option(
    "--p",
    type=str,
    default=None,
    help="Pass in encryption file password as argument",
)
@click.option(
    "--log-stock-check",
    is_flag=True,
    default=False,
    help="writes stock check information to terminal and log",
)
@click.option(
    "--shipping-bypass",
    is_flag=True,
    default=False,
    help="Will attempt to click ship to address button. USE AT YOUR OWN RISK!",
)
@click.option(
    "--clean-profile",
    is_flag=True,
    default=False,
    help="Purge the user profile that Fairgame uses for browsing",
)
@click.option(
    "--clean-credentials",
    is_flag=True,
    default=False,
    help="Purge Amazon credentials and prompt for new credentials",
)
@click.option(
    "--alt-offers",
    is_flag=True,
    default=False,
    help="Directly hit the offers page.  Preferred, but deprecated by Amazon.",
)
@click.option(
    "--captcha-wait",
    is_flag=True,
    default=False,
    help="Wait if captcha could not be solved. Only occurs if enters captcha handler during checkout.",
)
@click.option(
    "--autobuy-config-path",
)

@notify_on_crash
def amazon(
    no_image,
    headless,
    test,
    delay,
    checkshipping,
    detailed,
    used,
    single_shot,
    no_screenshots,
    disable_presence,
    disable_sound,
    slow_mode,
    p,
    log_stock_check,
    shipping_bypass,
    clean_profile,
    clean_credentials,
    alt_offers,
    captcha_wait,
    autobuy_config_path,
):
    notification_handler.sound_enabled = not disable_sound
    if not notification_handler.sound_enabled:
        log.info("Local sounds have been disabled.")

    if clean_profile and os.path.exists(global_config.get_browser_profile_path()):
        log.info(
            f"Removing existing profile at '{global_config.get_browser_profile_path()}'"
        )
        profile_size = get_folder_size(global_config.get_browser_profile_path())
        shutil.rmtree(global_config.get_browser_profile_path())
        log.info(f"Freed {profile_size}")

    if clean_credentials and os.path.exists(AMAZON_CREDENTIAL_FILE):
        log.info(f"Removing existing Amazon credentials from {AMAZON_CREDENTIAL_FILE}")
        os.remove(AMAZON_CREDENTIAL_FILE)

    amzn_obj = Amazon(
        headless=headless,
        notification_handler=notification_handler,
        checkshipping=checkshipping,
        detailed=detailed,
        used=used,
        single_shot=single_shot,
        no_screenshots=no_screenshots,
        disable_presence=disable_presence,
        slow_mode=slow_mode,
        no_image=no_image,
        encryption_pass=p,
        log_stock_check=log_stock_check,
        shipping_bypass=shipping_bypass,
        alt_offers=alt_offers,
        wait_on_captcha_fail=captcha_wait,
        autobuy_config_path=autobuy_config_path
    )
    try:
        amzn_obj.run(delay=delay, test=test)
    except RuntimeError:
        del amzn_obj
        log.error("Exiting Program...")
        time.sleep(5)


@click.option(
    "--disable-sound",
    is_flag=True,
    default=False,
    help="Disable local sounds.  Does not affect Apprise notification " "sounds.",
)
@click.command()
def test_notifications(disable_sound):
    enabled_handlers = ", ".join(notification_handler.enabled_handlers)
    message_time = datetime.now().strftime(TIME_FORMAT)
    notification_handler.send_notification(
        f"Beep boop. This is a test notification from FairGame. Sent {message_time}."
    )
    log.info(f"A notification was sent to the following handlers: {enabled_handlers}")
    if not disable_sound:
        log.info("Testing notification sound...")
        notification_handler.play_notify_sound()
        time.sleep(2)  # Prevent audio overlap
        log.info("Testing alert sound...")
        notification_handler.play_alarm_sound()
        time.sleep(2)  # Prevent audio overlap
        log.info("Testing purchase sound...")
        notification_handler.play_purchase_sound()
    else:
        log.info("Local sounds disabled for this test.")

    # Give the notifications a chance to get out before we quit
    time.sleep(5)


@click.command()
@click.option("--w", is_flag=True)
@click.option("--c", is_flag=True)
def show(w, c):
    show_file = "show_c.txt"
    if w and c:
        print("Choose one option. Program Quitting")
        exit(0)
    elif w:
        show_file = "show_w.txt"
    elif c:
        show_file = "show_c.txt"
    else:
        print(
            "Option missing, you must include w or c with show argument. Program Quitting"
        )
        exit(0)

    if os.path.exists(LICENSE_PATH):

        with open(os.path.join(LICENSE_PATH, show_file)) as file:
            try:
                print(file.read())
            except FileNotFoundError:
                log.error("License File Missing. Quitting Program")
                exit(0)
    else:
        log.error("License File Missing. Quitting Program.")
        exit(0)


@click.command()
@click.option(
    "--domain",
    help="Specify the domain you want to find endpoints for (e.g. www.amazon.de, www.amazon.com, smile.amazon.com.",
)
def find_endpoints(domain):
    import dns.resolver

    if not domain:
        log.error("You must specify a domain to resolve for endpoints with --domain.")
        exit(0)
    log.info(f"Attempting to resolve '{domain}'")
    # Default
    my_resolver = dns.resolver.Resolver()
    try:
        resolved = my_resolver.resolve(domain)
        for rdata in resolved:
            log.info(f"Your computer resolves {domain} to {rdata.address}")
    except Exception as e:
        log.error(f"Failed to use local resolver due to: {e}")
        exit(1)

    # Find endpoints from various DNS servers
    endpoints, resolutions = resolve_domain(domain)
    log.info(
        f"{domain} resolves to at least {len(endpoints)} distinct IP addresses across {resolutions} lookups:"
    )
    endpoints = sorted(endpoints)
    for endpoint in endpoints:
        log.info(f" {endpoint}")

    return endpoints


def resolve_domain(domain):
    import dns.resolver

    public_dns_servers = global_config.get_fairgame_config().get("public_dns_servers")
    resolutions = 0
    endpoints = set()

    # Resolve the domain for each DNS server to find out how many end points we have
    for provider in public_dns_servers:
        # Provider is Google, Verisign, etc.
        log.info(f"Testing {provider}")
        for server in public_dns_servers[provider]:
            # Server is 8.8.8.8 or 1.1.1.1
            my_resolver = dns.resolver.Resolver()
            my_resolver.nameservers = [server]

            try:
                resolved = my_resolver.resolve(domain)
            except Exception as e:
                log.warning(
                    f"Unable to resolve using {provider} server {server} due to: {e}"
                )
                continue
            for rdata in resolved:
                ipv4_address = rdata.address
                endpoints.add(ipv4_address)
                resolutions += 1
                log.debug(f"{domain} resolves to {ipv4_address} via {server}")
    return endpoints, resolutions


@click.command()
@click.option(
    "--domain", help="Specify the domain you want to generate traceroute commands for."
)
def show_traceroutes(domain):
    if not domain:
        log.error("You must specify a domain to test routes using --domain.")
        exit(0)

    # Get the endpoints to test
    endpoints, resolutions = resolve_domain(domain=domain)

    if platform.system() == "Windows":
        trace_command = "tracert -d "
    else:
        trace_command = "traceroute -n "

    # Spitball test routes via Python's traceroute
    for endpoint in endpoints:
        log.info(f" {trace_command}{endpoint}")


# Register Signal Handler for Interrupt
signal(SIGINT, interrupt_handler)

main.add_command(amazon)
main.add_command(test_notifications)
main.add_command(show)
main.add_command(find_endpoints)
main.add_command(show_traceroutes)

# Global scope stuff here
if is_latest():
    log.info(f"FairGame v{version}")
elif version.is_prerelease:
    log.warning(f"FairGame PRE-RELEASE v{version}")
else:
    log.warning(
        f"You are running FairGame v{version}, but the most recent version is v{get_latest_version()}. "
        f"Consider upgrading "
    )

global_config = GlobalConfig()
notification_handler = NotificationHandler()
