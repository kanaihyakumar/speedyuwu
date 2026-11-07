import random

import pytest

from speedy import mathgen
from speedy.mathgen import ExprError, check_answer, evaluate, parse_surd


@pytest.mark.parametrize('text,expected', [
    ('3√2', 3 * 2 ** 0.5), ('sqrt(3)/2', 3 ** 0.5 / 2), ('√3/2', 3 ** 0.5 / 2), ('5π/6', 5 * 3.141592653589793 / 6),
    ('2^-3', 0.125), ('-2^2', -4), ('(1+2)(3+4)', 21), ('1/2x', None), ('50%', 0.5), ('1,000', None),
    ('√2^2', 2.0000000000000004), ('sin(30°)', 0.5), ('3!', 6), ('2 ** 3', 8), ('10÷4', 2.5),
])
def test_evaluate(text, expected):
    if expected is None:
        with pytest.raises(ExprError):
            evaluate(text, None) if text != '1/2x' else evaluate(text)
        return
    assert evaluate(text) == pytest.approx(expected)


@pytest.mark.parametrize('text', ['9^9^9^9', '__import__("os")', 'hello', 'a b c', '1/0', '(-8)^(1/3)', '2' * 70, 'sqrt', 'import os'])
def test_evaluate_rejects(text):
    with pytest.raises(ExprError):
        evaluate(text)


def test_variables_only_when_provided():
    assert evaluate('2x^2+5x', {'x': 2}) == 18
    with pytest.raises(ExprError):
        evaluate('2x')


def test_parse_surd():
    assert parse_surd('3√2') == (3, 2)
    assert parse_surd('3 rt 2') == (3, 2)
    assert parse_surd('-√3/3')[0] < 0
    assert parse_surd('7') == (7, 1)
    assert parse_surd('hello') is None


def test_surd_form_enforced():
    q = mathgen.Question('surds', 'Simplify √18', 'surd', (3, 2), '3√2')
    assert check_answer(q, '3√2') == 'correct'
    assert check_answer(q, '3sqrt(2)') == 'correct'
    assert check_answer(q, '√18') == 'wrong'
    assert check_answer(q, '4.24') == 'wrong'
    assert check_answer(q, 'hello') is None


def test_fraction_must_be_reduced():
    from fractions import Fraction
    q = mathgen.Question('fractions', '?', 'fraction', Fraction(2, 3), '2/3')
    assert check_answer(q, '2/3') == 'correct'
    assert check_answer(q, '4/6') == 'wrong'
    assert check_answer(q, '0.6666667') == 'correct'


def test_expr_equivalence_and_forbid():
    q = mathgen.Question('algebra', '?', 'expr', lambda x: (x + 2) * (x + 3), 'x²+5x+6', forbid=['(x+2)(x+3)'])
    assert check_answer(q, 'x^2+5x+6') == 'correct'
    assert check_answer(q, 'x² + 5x + 6') == 'correct'
    assert check_answer(q, '(x+2)(x+3)') == 'wrong'
    assert check_answer(q, 'x^2+5x+7') == 'wrong'


def test_collections():
    roots = mathgen.Question('q', '?', 'set', [2, 3], '2, 3')
    for good in ['2, 3', '3,2', 'x=2 or x=3', '2 and 3', '2 3']:
        assert check_answer(roots, good) == 'correct', good
    assert check_answer(roots, '2, 4') == 'wrong'
    pair = mathgen.Question('q', '?', 'tuple', [1, 5], '(1, 5)')
    for good in ['1, 5', '(1,5)', 'x=1, y=5', 'y=5 x=1'.replace(' x', ', x')]:
        assert check_answer(pair, good) == 'correct', good
    assert check_answer(pair, '5, 1') == 'wrong'


def test_text_only_reacts_to_vocab():
    q = mathgen.Question('numbers', '?', 'text', ['yes', 'y'], 'yes', vocab=lambda s: s in ('yes', 'no', 'y', 'n'))
    assert check_answer(q, 'Yes') == 'correct'
    assert check_answer(q, 'no') == 'wrong'
    assert check_answer(q, 'lol what') is None


def test_units_and_percent_suffix():
    q = mathgen.num_q('geometry', '?', 25, places=None)
    assert check_answer(q, '25%') == 'correct'
    assert check_answer(q, '25 cm') == 'correct'
    assert check_answer(q, '25°') == 'correct'


@pytest.mark.parametrize('topic', list(mathgen.TOPICS))
@pytest.mark.parametrize('level', [1, 2, 3])
def test_every_generated_question_accepts_its_own_answer(topic, level):
    rng = random.Random(f'{topic}{level}')
    for _ in range(150):
        q = mathgen.generate(topic, level, rng)
        assert q.prompt and q.display
        assert check_answer(q, q.display) == 'correct', (q.prompt, q.display)
        assert check_answer(q, q.display.replace('−', '-')) == 'correct', (q.prompt, q.display)


def test_find_topic_aliases():
    assert mathgen.find_topic('Trigonometry').key == 'trig'
    assert mathgen.find_topic('percent').key == 'fractions'
    assert mathgen.find_topic('nope') is None


def test_expand_rejects_any_bracketed_answer():
    q = mathgen.Question('algebra', '?', 'expr', lambda x: (x - 4) * (x + 2), 'x²−2x−8', forbid=['(x−4)(x+2)'])
    assert check_answer(q, '(x + 2)(x - 4)') == 'wrong'
    assert check_answer(q, 'x^2-2x-8') == 'correct'


def test_rounded_decimals_accepted_when_prompt_allows():
    q = next(mathgen.generate('logs', 3, random.Random(i)) for i in range(200) if 'give a fraction' in mathgen.generate('logs', 3, random.Random(i)).prompt)
    assert check_answer(q, f'{q.answer:.3f}') == 'correct'
