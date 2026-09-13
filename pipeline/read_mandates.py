"""
Reads the current mandate list straight from the rendered page — the same
approach that would be needed against a real bank (parse what's visibly
on screen), rather than peeking at the mock bank's localStorage directly.
This is what both the "before" and "after" reads for the Verification
Agent should use.
"""

def read_mandates_from_dom(page, base_url: str) -> list:
    url_lower = page.url.lower()
    base_lower = (base_url or "").lower()

    # If already on the Mandate Dashboard, read directly from the dashboard DOM without leaving
    if "mandate.html" in url_lower or "mandate.html" in base_lower:
        if "mandate.html" not in url_lower:
            page.goto(base_url)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=4000)
            except Exception:
                pass

        # Read from the dashboard table rows
        rows = page.locator(".m-row[data-id]").all()
        mandates = []
        for row in rows:
            m_id = row.get_attribute("data-id")
            if not m_id:
                continue
            
            # Merchant name
            name_el = row.locator(".m-row-name")
            merchant = name_el.inner_text().strip() if name_el.count() > 0 else m_id
            
            # Status: prefer explicit data-status attribute, fallback to tag text
            status = row.get_attribute("data-status")
            if not status:
                tag_el = row.locator("[class*='tag-']")
                if tag_el.count() > 0:
                    tag_text = tag_el.first.inner_text().strip().lower()
                    status = "cancelled" if "cancel" in tag_text else "active"
                else:
                    status = "active"
            else:
                status = status.strip().lower()

            mandates.append({"id": m_id, "merchant": merchant, "status": status})

        if mandates:
            return mandates

    # Standalone mock bank fallback
    target_url = f"{base_url}?page=mandates" if "?" not in base_url else base_url
    if page.url != target_url:
        page.goto(target_url)
        page.wait_for_load_state("networkidle")

    rows = page.locator("table tr").all()
    mandates = []
    for row in rows[1:]:  # skip header row
        cells = row.locator("td").all()
        if len(cells) < 5:
            continue
        merchant = cells[0].inner_text().strip()
        status = cells[3].inner_text().strip()

        # Check for data-id attribute first
        mandate_id = row.get_attribute("data-id")

        if not mandate_id:
            links = row.locator("a")
            if links.count() > 0:
                href = links.first.get_attribute("href") or ""
                if "id=" in href:
                    mandate_id = href.split("id=")[1].split("&")[0]

        if mandate_id is None:
            # When cancelled on mock bank without data-id, row has '—' instead of 'Manage' link
            mandate_id = merchant

        mandates.append({"id": mandate_id, "merchant": merchant, "status": status})
    return mandates
