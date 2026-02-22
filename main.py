# Standard Library
import asyncio
import logging
import os
import sys
import traceback

# Third Party
import httpx

# Local
from trade_worker import TradeWorker
from user import User
from utilities import (
    load_config,
    setup_logging,
    print_timestamp,
    check_for_update_loop,
    InvalidCookie,
)

version = "v0.3.3-alpha"
os.system("title " + f"Horizon {version}")

logger = logging.getLogger("horizon.main")


async def main():

    if getattr(sys, "frozen", False):
        main_folder_path = os.path.dirname(sys.executable)
    else:
        main_folder_path = os.path.dirname(os.path.abspath(__file__))

    # 🔎 DEBUG: show config path being used
    config_path = os.path.join(main_folder_path, "horizon_config.ini")
    print("CONFIG PATH BEING USED:", config_path)

    config = load_config(config_path)
    setup_logging(main_folder_path, level=config["logging_level"])

    print_timestamp(
        f"Horizon Trade Notifier {version} - https://discord.gg/Xu8pqDWmgE - https://github.com/JartanFTW"
    )

    users = []
    tasks = []

    # 🔎 DEBUG: show cookies read from config (shortened)
    print("COOKIES FOUND IN CONFIG:")
    for cookie in config["cookies"]:
        print(" -", cookie[:60] + "...")

    for cookie in config["cookies"]:
        try:
            user = await User.create(cookie)
            users.append(user)
        except InvalidCookie:
            print_timestamp(f"An invalid cookie was detected: {cookie[:80]}...")
            continue

    if users:
        max_username_length = max([len(user.display_name) for user in users])

        for user in users:
            if config["completed"]["enabled"]:
                worker = await TradeWorker.create(
                    main_folder_path,
                    user,
                    config["completed"]["webhook"],
                    config["completed"]["update_interval"],
                    config["completed"]["theme_name"],
                    trade_type="Completed",
                    add_unvalued_to_value=config["add_unvalued_to_value"],
                    testing=config["testing"],
                    webhook_content=config["completed"]["webhook_content"],
                    max_username_length=max_username_length,
                )
                tasks.append(asyncio.create_task(worker.check_trade_loop()))

    if tasks:
        await asyncio.wait(tasks)
    else:
        if not users:
            print_timestamp("All cookies are invalid! There is nothing for me to do :(")
        else:
            print_timestamp(
                "Looks like you don't have any trade types enabled in the config! There is nothing for me to do :("
            )

    for user in users:
        await user.client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logger.critical(f"An unknown critical error occurred: {traceback.format_exc()}")
        print(f"An unknown critical error occurred: {traceback.format_exc()}")
    finally:
        input("Operations have complete. Press Enter to exit.")
