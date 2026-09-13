import os
from pipeline.session_manager import session_manager

ARTIFACT_DIR = r"C:\Users\ASUS\.gemini\antigravity-ide\brain\4cf7464f-9abc-4ebb-b32a-0e5d24771141"

def main():
    def _capture():
        page = session_manager.get_or_create_page(headless=True)
        page.set_viewport_size({"width": 1440, "height": 960})
        page.goto("http://localhost:8000/ui/mandate.html")
        page.wait_for_timeout(1000)

        os.makedirs(ARTIFACT_DIR, exist_ok=True)

        # 1. Landing Screen
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "1_landing_screen.png"))
        print("[OK] 1_landing_screen.png captured")

        # 2. Open Bank Selection
        page.click("text=Connect Bank Account")
        page.wait_for_timeout(600)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "2_bank_select_modal.png"))
        print("[OK] 2_bank_select_modal.png captured")

        # 3. Choose Demo Bank
        page.click("text=Demo Bank (Hackathon)")
        page.wait_for_timeout(600)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "3_auth_login_modal.png"))
        print("[OK] 3_auth_login_modal.png captured")

        # 4. Submit Auth & Enter Dashboard
        page.click("button.btn-submit-auth")
        page.wait_for_timeout(3500)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "4_dashboard_refined.png"), full_page=True)
        print("[OK] 4_dashboard_refined.png captured")

        # 5. Click Approve Cancellation & Wait for Proof Modal
        page.click("#btn-approve-cancel")
        page.wait_for_timeout(6500)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "5_final_proof_modal.png"))
        print("[OK] 5_final_proof_modal.png captured")

    try:
        session_manager.execute(_capture)
    finally:
        session_manager.close_session()

if __name__ == "__main__":
    main()
