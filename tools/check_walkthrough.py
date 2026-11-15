"""Exercise the first-use explanation and recovery path against the real local API."""
from pathlib import Path
import os, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temp:
    env={**os.environ,'AFTERMATH_DB':str(Path(temp)/'test.sqlite3')}
    server=subprocess.Popen([sys.executable,'-m','backend.server'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for attempt in range(100):
            try:
                urllib.request.urlopen('http://127.0.0.1:8000/api/runs',timeout=1).close()
                break
            except OSError: time.sleep(.1)
        else: raise RuntimeError('Local API did not start')
        with sync_playwright() as p:
            browser=p.chromium.launch()
            out=ROOT/'artifacts';out.mkdir(exist_ok=True)
            for width in [390,1440]:
                page=browser.new_page(viewport={'width':width,'height':1000},color_scheme='dark')
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto('http://127.0.0.1:8000')
                expect(page.get_by_role('heading',name='Test a payment system crash')).to_be_visible()
                expect(page.locator('.start-guide')).to_contain_text('four copies')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                page.screenshot(path=str(out/f'first-use-{width}.png'),full_page=True)
                page.get_by_role('button',name='Create simulation',exact=True).click()
                expect(page.locator('.proof strong')).to_have_text('0 payment records saved')
                page.get_by_role('button',name='Run next step',exact=True).click()
                expect(page.locator('.timeline')).to_contain_text('Connection unavailable')
                page.get_by_role('button',name='Run next step',exact=True).click()
                expect(page.get_by_role('button',name='Restart the processor',exact=True)).to_be_enabled()
                expect(page.locator('.proof strong')).to_have_text('1 payment record saved')
                page.get_by_role('button',name='Restart the processor',exact=True).click()
                for step in range(8):
                    nxt=page.get_by_role('button',name='Run next step',exact=True)
                    expect(nxt).to_be_visible()
                    if not nxt.is_enabled():break
                    nxt.click()
                    # Wait for the request by observing the button leave its busy state or completion.
                    page.wait_for_function('document.querySelector(".complete") || !document.querySelector(".timeline-head button").disabled')
                expect(page.locator('.complete')).to_contain_text('The payment was recorded once.')
                expect(page.locator('.proof strong')).to_have_text('1 payment record saved')
                expect(page.locator('.timeline details').first).to_be_visible()
                page.locator('.timeline details summary').first.click()
                expect(page.locator('.timeline details').first).to_have_attribute('open','')
                assert not errors,errors
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                page.screenshot(path=str(out/f'recovered-{width}.png'),full_page=True)
                page.close()
            browser.close()
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait()
print('Walkthrough completed with one saved payment at phone and desktop widths.')
