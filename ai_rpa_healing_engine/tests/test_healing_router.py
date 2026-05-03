from src.engine.healing_router import decide


def test_decide_allows_ui_selector_changed_for_locator_actions():
    inp = {
        "failure_context": {
            "action": "locator",
            "error_type": "UI_SELECTOR_CHANGED",
        },
        "dom_context": {
            "new_element_html": '<button id="update-profile">Update Profile</button>',
        },
    }

    assert decide(inp) is None