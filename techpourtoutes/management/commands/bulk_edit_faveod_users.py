import argparse
import asyncio

from playwright.async_api import async_playwright


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--user_ids", required=True, help="Comma-separated list of user IDs")
    args = parser.parse_args()
    return args.login, args.password, [uid.strip() for uid in args.user_ids.split(",")]


async def main():
    """
    Bulk edit faveod users on techpourtoutes.io.
    To run locally - this example deactivate users, but can be edited for other purposes

    Example usage:
        python bulk_edit_faveod_users.py --login admin --password secret --user_ids 101,202,303

    You can gather ids of faveod users imported to the new website running :
    pros = Pro.objects.exclude(faveod_id=None)
    ids = list(map(lambda pro: pro.faveod_id, pros))

    """

    login, password, user_ids = parse_args()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set True to run in background
        page = await browser.new_page()

        # --- Login ---
        await page.goto("https://www.techpourtoutes.io/users/login")
        await page.fill("#user_0_login", login)
        await page.fill("#user_0_password", password)
        await page.click("#btn_submit")
        await page.wait_for_url(lambda url: "login" not in url)
        print("Logged in successfully.")

        for user_id in user_ids:
            print(f"Processing user {user_id}...")
            try:
                await page.goto(
                    f"https://www.techpourtoutes.io/users/profil/{user_id}?",
                    wait_until="domcontentloaded",
                )

                await page.click("#edit_user_btn")
                await page.wait_for_load_state("networkidle")

                # --- deactivate users (edit this part for another bulk edit) ---
                checkbox = page.locator(f"input#user_{user_id}_active")
                if await checkbox.is_checked():
                    await checkbox.uncheck()
                    print(f"  Unchecked 'user_{user_id}_active'.")
                else:
                    print("  Already unchecked, skipping.")
                # --- end of deactivate part ---

                await page.click("#edit_save_form_submit")
                await page.wait_for_load_state("networkidle")
                print(f"  Saved changes for user {user_id}.")

            except Exception as e:
                print(f"  Skipping user {user_id}: {e}")
                continue

        print("All users processed.")
        await browser.close()


asyncio.run(main())
