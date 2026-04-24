import asyncio

from ai_pc_kit.tui import AccelScopeApp, run_tui


def test_tui_exports_app_and_runner() -> None:
    assert callable(run_tui)
    assert AccelScopeApp.NAV[0] == ("dashboard", "Dashboard")
    assert ("benchmark", "Benchmark") in AccelScopeApp.NAV


def test_tui_mounts_dashboard() -> None:
    async def run() -> None:
        app = AccelScopeApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.current_section == "dashboard"

    asyncio.run(run())
