from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest


@pytest.mark.parametrize("page",["Overview","Customers","Sales & forecast","Marketing","Statistical lab","Reports","Data quality"])
def test_dashboard_views(page):
    if not Path("data/warehouse.duckdb").exists(): pytest.skip("Run python -m customer360 demo for UI smoke tests")
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py",default_timeout=40).run()
    assert not app.exception
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception


def test_filter_rerun():
    if not Path("data/warehouse.duckdb").exists(): pytest.skip("Demo warehouse required")
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py",default_timeout=40).run()
    app.sidebar.selectbox[0].set_value("US").run()
    app.sidebar.selectbox[1].set_value("Web").run()
    assert not app.exception
    assert app.metric[0].value!="$0"


def test_report_generation_and_persistence():
    if not Path("data/warehouse.duckdb").exists(): pytest.skip("Demo warehouse required")
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py",default_timeout=40).run()
    app.sidebar.radio[0].set_value("Reports").run()
    app.button[0].click().run()
    assert not app.exception
    assert len(app.get("download_button"))==1
    app.run()
    assert len(app.get("download_button"))==1


@pytest.mark.parametrize("page",["Customers","Sales & forecast","Marketing","Statistical lab"])
def test_narrow_and_empty_filters(page):
    if not Path("data/warehouse.duckdb").exists(): pytest.skip("Demo warehouse required")
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py",default_timeout=40).run()
    app.sidebar.radio[0].set_value(page)
    app.sidebar.selectbox[0].set_value("PK")
    app.sidebar.selectbox[1].set_value("Store")
    from datetime import date
    app.sidebar.date_input[0].set_value((date(2024,1,1),date(2024,1,1))).run()
    assert not app.exception
