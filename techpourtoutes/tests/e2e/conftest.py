from playwright.sync_api import expect

# Several suites may run side by side on one machine, each on every core: a page then takes far
# longer than Playwright's default 5 s to answer. A broken test still fails, 10 s later.
expect.set_options(timeout=15_000)
