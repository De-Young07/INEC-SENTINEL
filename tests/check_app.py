"""Integration smoke check: python tests/check_app.py."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'src/app.py'), default_timeout=90).run()
assert not app.exception, list(app.exception)
assert app.metric[0].value == '774'
app.number_input[0].set_value(0).run()
assert not app.exception
assert next(metric for metric in app.metric if metric.label == 'Proposed visits').value == '0'
next(button for button in app.button if button.label == 'Show suggested next step').click().run()
assert not app.exception
assert len(app.session_state['rehearsals']) == 1
next(field for field in app.text_input if field.label == 'Find an LGA').set_value('NO_MATCH_123').run()
assert not app.exception
assert any('No areas match' in warning.value for warning in app.warning)
print('PASS: initial render, zero budget, rehearsal submission, empty filter')
