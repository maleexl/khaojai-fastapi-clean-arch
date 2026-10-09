"""End-to-end browser test: Register → Login → Profile → Logout.

Requires:
    - Backend running at http://localhost:8000 (docker compose up -d)
    - Frontend running at http://localhost:5173 (npm run dev)

Run with:
    pytest tests/e2e/test_frontend_flow.py -v -s
"""
from __future__ import annotations

import uuid

import pytest
from playwright.async_api import async_playwright, Page, expect

FRONTEND_URL = "http://localhost:5173"


@pytest.mark.asyncio
async def test_full_user_journey() -> None:
    """Register a new user, log in, view profile, and log out."""
    # unique email per run so the test is idempotent
    unique = uuid.uuid4().hex[:8]
    email = f"e2e-{unique}@example.com"
    username = f"e2e_{unique}"
    password = "password123"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page: Page = await context.new_page()

        # ---- 1. Register ------------------------------------------------
        await page.goto(f"{FRONTEND_URL}/register")
        await expect(page.get_by_role("heading", name="Create Account")).to_be_visible()

        await page.get_by_label("Email").fill(email)
        await page.get_by_label("Username").fill(username)
        await page.get_by_label("Password").fill(password)
        await page.get_by_role("button", name="Create Account").click()

        # should show success banner and redirect to /login
        await expect(page).to_have_url(f"{FRONTEND_URL}/login", timeout=5000)

        # ---- 2. Login ---------------------------------------------------
        await expect(page.get_by_role("heading", name="Login")).to_be_visible()
        await page.get_by_label("Email").fill(email)
        await page.get_by_label("Password").fill(password)
        await page.get_by_role("button", name="Login").click()

        # ---- 3. Profile -------------------------------------------------
        await expect(page).to_have_url(f"{FRONTEND_URL}/profile", timeout=5000)
        await expect(page.get_by_test_id("profile-username")).to_have_text(username)
        await expect(page.get_by_test_id("profile-email")).to_have_text(email)
        await expect(page.get_by_text("Active")).to_be_visible()

        # ---- 4. Logout --------------------------------------------------
        await page.get_by_role("button", name="Logout").click()
        await expect(page).to_have_url(f"{FRONTEND_URL}/login", timeout=5000)

        await browser.close()
