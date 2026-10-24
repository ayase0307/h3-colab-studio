"""UI multi-reference list (ref_1..ref_9) in a headless browser. Skips if playwright/chromium is unavailable."""
import base64, json, sys, tempfile
from pathlib import Path
UI = Path(__file__).resolve().parents[1] / "src" / "ui.html"
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP no playwright"); sys.exit(0)
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
BRIDGE = """window.H3_RUNS=[];let n=0;window.H3_TEST_BRIDGE=async(name,...a)=>{if(name==='about')return {ok:true,value:{ready:true,environment:{},results:[]}};
if(name==='upload')return {ok:true,value:{filename:'h3ref_'+(++n)+'.png',width:1,height:1}};if(name==='run'){H3_RUNS.push(a[0]);return {ok:true,value:{id:'j'}}}
if(name==='status')return {ok:true,value:{state:'running',message:'',stage:'loading'}};return {ok:true,value:{}}};"""
tmp = Path(tempfile.mkdtemp()); img = tmp / "a.png"; img.write_bytes(PNG)
with sync_playwright() as p:
    try: b = p.chromium.launch()
    except Exception as e: print("SKIP no chromium", e); sys.exit(0)
    pg = b.new_page(); pg.add_init_script(BRIDGE); pg.goto(UI.as_uri()); pg.wait_for_function("window.H3_UI_TEST")
    pg.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)")
    for _ in range(3):
        pg.set_input_files("#refFile", str(img)); pg.wait_for_timeout(150)
    labels = pg.evaluate("H3_UI_TEST.refLabels()"); assert labels == ["<Picture 1>（ref_1）", "<Picture 2>（ref_2）", "<Picture 3>（ref_3）"], labels
    c = pg.evaluate("H3_UI_TEST.config()"); assert [c.get(f"ref_{i}") for i in (1, 2, 3)] == ["h3ref_1.png", "h3ref_2.png", "h3ref_3.png"] and "first_frame" not in c, c
    pg.locator("#refList button").nth(0).click()  # remove Picture 1 -> renumber
    c = pg.evaluate("H3_UI_TEST.config()"); assert c.get("ref_1") == "h3ref_2.png" and c.get("ref_2") == "h3ref_3.png" and "ref_3" not in c, c
    assert pg.evaluate("H3_UI_TEST.refLabels()") == ["<Picture 1>（ref_1）", "<Picture 2>（ref_2）"]
    for _ in range(8):
        pg.set_input_files("#refFile", str(img)); pg.wait_for_timeout(120)
    assert len(pg.evaluate("H3_UI_TEST.refLabels()")) == 9 and pg.is_disabled("#addRef") and pg.inner_text("#addRef") == "已達 9 張上限"
    # generate sends ref_N
    pg.select_option("#mode", "omni"); pg.click("#generate"); pg.wait_for_timeout(200)
    run = pg.evaluate("H3_RUNS[0]"); assert all(run.get(f"ref_{i}") for i in range(1, 10)), run
    # restore: reuse (keepRefs) from a report with config.refs; load-config clears
    pg.evaluate("H3_UI_TEST.restore({config:{prompt:'x',size:'landscape',seconds:'5',mode:'omni',refs:['h3ref_a.png','h3ref_b.png']}},true)")
    c = pg.evaluate("H3_UI_TEST.config()"); assert c["ref_1"] == "h3ref_a.png" and c["ref_2"] == "h3ref_b.png" and "ref_3" not in c, c
    pg.evaluate("H3_UI_TEST.restore({config:{prompt:'x',size:'landscape',seconds:'5',mode:'omni',ref_1:'h3ref_a.png'}})")
    c = pg.evaluate("H3_UI_TEST.config()"); assert "ref_1" not in c and c.get("first_frame") == "", c
    # no refs: first/last frame behaviour unchanged
    pg.set_input_files("#firstImage", str(img)); pg.wait_for_timeout(150)
    c = pg.evaluate("H3_UI_TEST.config()"); assert c["first_frame"].startswith("h3ref_") and "ref_1" not in c and c["prompt"].startswith("For the target video"), c
    b.close()
print("ui multiref OK")
