"""
Shared test setup.

One job so far: process-level caches must not leak between tests.

farmer.answer_writer keeps finished answers in a module-level dict so a repeat
question does not pay for the model twice. That is correct in the app -- the
same question against the same documents has the same answer -- but in a test
run it means whichever test asks a question first silently decides the result
for every later test that asks it again. It cost exactly that once already:
test_a_broken_council_still_answers_the_farmer passed alone and failed in the
suite, because an earlier test had cached a working council answer under the
identical key.
"""

from __future__ import annotations

import pytest

from farmer import answer_writer


@pytest.fixture(autouse=True)
def _clear_answer_cache():
    answer_writer.clear_cache()
    yield
    answer_writer.clear_cache()
