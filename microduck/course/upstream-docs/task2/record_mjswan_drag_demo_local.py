from argparse import ArgumentParser
from pathlib import Path
import re
import shutil

from playwright.sync_api import sync_playwright


def wait_for_scene(page, timeout_ms=60_000):
    # The packaged browser build does not expose a stable readiness flag.
    # Its scene and ONNX assets are local, so a fixed warm-up is more reliable
    # than waiting on a UI label that can remain mounted while hidden.
    page.wait_for_timeout(min(timeout_ms, 25_000))


def reset_scene(page):
    buttons = page.get_by_role("button")
    labels = [label.strip() for label in buttons.all_inner_texts()]
    for label in labels:
        if re.search(r"reset|restart|重新", label, re.IGNORECASE):
            buttons.get_by_text(label, exact=True).click()
            page.wait_for_timeout(1_500)
            return "button"

    page.reload(wait_until="domcontentloaded", timeout=60_000)
    wait_for_scene(page)
    return "reload"


def drag_canvas(page, start, moves, hold_ms=700):
    canvas = page.locator("canvas").first
    box = canvas.bounding_box()
    if not box:
        raise RuntimeError("mjswan canvas has no bounding box")

    sx = box["x"] + box["width"] * start[0]
    sy = box["y"] + box["height"] * start[1]
    page.mouse.move(sx, sy)
    page.mouse.down()
    for relative_x, relative_y in moves:
        page.mouse.move(
            sx + box["width"] * relative_x,
            sy + box["height"] * relative_y,
            steps=18,
        )
        page.wait_for_timeout(180)
    page.wait_for_timeout(hold_ms)
    page.mouse.up()


def main():
    parser = ArgumentParser(description="Record manual mjswan MicroDuck drag demos.")
    parser.add_argument("--url", default="http://127.0.0.1:8092/")
    parser.add_argument("--output-dir", type=Path, default=Path("recordings"))
    parser.add_argument("--seconds-after-drag", type=float, default=3.0)
    parser.add_argument(
        "--browser-executable",
        type=Path,
        help="Use an installed Chromium/Edge binary instead of Playwright's download.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    temporary_dir = args.output_dir / "playwright_tmp"
    temporary_dir.mkdir(parents=True, exist_ok=True)

    demos = [
        ("rightward lift", (0.50, 0.50), [(0.18, -0.05), (0.28, -0.12)]),
        ("leftward shove", (0.50, 0.50), [(-0.16, 0.02), (-0.25, 0.10)]),
        ("diagonal swing", (0.50, 0.50), [(0.12, -0.16), (0.22, 0.12)]),
    ]

    with sync_playwright() as playwright:
        executable = args.browser_executable
        if executable is None:
            candidates = [
                shutil.which("chromium"),
                shutil.which("google-chrome"),
                Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
                Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            ]
            executable = next(
                (Path(candidate) for candidate in candidates if candidate and Path(candidate).is_file()),
                None,
            )
        launch_options = {"headless": True}
        if executable is not None:
            launch_options["executable_path"] = str(executable)
        browser = playwright.chromium.launch(**launch_options)
        context = browser.new_context(
            viewport={"width": 1280, "height": 820},
            device_scale_factor=1,
            record_video_dir=str(temporary_dir),
            record_video_size={"width": 1280, "height": 820},
        )
        page = context.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=60_000)
        wait_for_scene(page)
        page.wait_for_timeout(3_000)

        for index, (name, start, moves) in enumerate(demos, start=1):
            if index > 1:
                mode = reset_scene(page)
                print(f"RESET_{index}={mode}")
                page.wait_for_timeout(1_500)
            drag_canvas(page, start, moves)
            page.wait_for_timeout(int(args.seconds_after_drag * 1_000))
            print(f"DEMO_{index}={name}")

        page.wait_for_timeout(2_000)
        page.close()
        context.close()
        webm_path = Path(page.video.path())
        browser.close()

    target = args.output_dir / "mjswan_microduck_manual_drag_demo.webm"
    webm_path.replace(target)
    print(f"WEBM={target.resolve()}")


if __name__ == "__main__":
    main()
