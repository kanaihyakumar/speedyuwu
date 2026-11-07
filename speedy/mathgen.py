"""Maths question generators, a safe expression evaluator and answer checking.

Nothing here touches Discord, so everything is unit-testable. Answers typed by users are
parsed with a small hand-written parser (never eval) that understands things like
``3√2``, ``sqrt(3)/2``, ``5π/6``, ``2x^2+5x`` and ``x=2, y=3``.
"""
import math
import random
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Callable, Optional


class ExprError(Exception):
    pass


# --------------------------------------------------------------------------- parsing

_FUNCS = {
    'sqrt': math.sqrt,
    'rt': math.sqrt,
    'cbrt': math.cbrt,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'log': math.log10,
    'ln': math.log,
    'abs': abs,
}

_TOKEN_RE = re.compile(r'\s*(?:(\d+\.?\d*|\.\d+)|(sqrt|cbrt|sin|cos|tan|log|ln|abs|rt|pi)|([a-z])|(\^|[-+*/()!%°]))')

_REPLACEMENTS = [
    ('×', '*'), ('·', '*'), ('÷', '/'), ('−', '-'), ('–', '-'), ('√', 'sqrt'), ('∛', 'cbrt'), ('π', 'pi'),
    ('²', '^2'), ('³', '^3'), ('⁴', '^4'), ('**', '^'), ('degrees', '°'), ('degree', '°'), ('deg', '°'),
]

_UNIT_SUFFIX = re.compile(r'\s*(?:cm|mm|km|m|units?|sq\.?|squared|metres?|meters?|rad(?:ians?)?|°|%)(?:\^?[23²³])?$')


def normalize(text):
    text = text.strip().lower()
    for old, new in _REPLACEMENTS:
        text = text.replace(old, new)
    return text


def _tokenize(text):
    tokens = []
    pos = 0
    text = text.rstrip()
    while pos < len(text):
        match = _TOKEN_RE.match(text, pos)
        if not match or match.end() == pos:
            raise ExprError('bad token')
        number, name, letter, symbol = match.groups()
        if number is not None:
            tokens.append(('num', float(number)))
        elif name is not None:
            tokens.append(('func' if name in _FUNCS else 'const', name))
        elif letter is not None:
            tokens.append(('var', letter))
        else:
            tokens.append(('op', symbol))
        pos = match.end()
        if len(tokens) > 80:
            raise ExprError('too long')
    return tokens


class _Parser:
    def __init__(self, tokens, variables):
        self.tokens = tokens
        self.pos = 0
        self.variables = variables or {}

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else (None, None)

    def take(self):
        token = self.peek()
        self.pos += 1
        return token

    def parse(self):
        if not self.tokens:
            raise ExprError('empty')
        value = self.expr()
        if self.pos != len(self.tokens):
            raise ExprError('trailing input')
        return value

    def expr(self):
        value = self.term()
        while self.peek() in (('op', '+'), ('op', '-')):
            op = self.take()[1]
            rhs = self.term()
            value = value + rhs if op == '+' else value - rhs
        return value

    def starts_atom(self, token):
        kind, value = token
        return kind in ('func', 'const', 'var') or (kind == 'op' and value == '(')

    def term(self):
        value = self.unary()
        while True:
            token = self.peek()
            if token in (('op', '*'), ('op', '/')):
                self.take()
                rhs = self.unary()
                if token[1] == '*':
                    value *= rhs
                else:
                    if rhs == 0:
                        raise ExprError('division by zero')
                    value /= rhs
            elif self.starts_atom(token):
                value *= self.unary()
            else:
                return value

    def unary(self):
        if self.peek() == ('op', '-'):
            self.take()
            return -self.unary()
        if self.peek() == ('op', '+'):
            self.take()
            return self.unary()
        return self.power()

    def power(self):
        base = self.postfix()
        if self.peek() == ('op', '^'):
            self.take()
            exponent = self.unary()
            try:
                result = math.pow(base, exponent)
            except (ValueError, OverflowError, ZeroDivisionError):
                raise ExprError('bad power')
            return result
        return base

    def postfix(self):
        value = self.atom()
        while True:
            token = self.peek()
            if token == ('op', '!'):
                self.take()
                if value < 0 or value > 20 or value != int(value):
                    raise ExprError('bad factorial')
                value = float(math.factorial(int(value)))
            elif token == ('op', '%'):
                self.take()
                value /= 100
            elif token == ('op', '°'):
                self.take()
                value = math.radians(value)
            else:
                return value

    def atom(self):
        kind, value = self.take()
        if kind == 'num':
            return value
        if kind == 'const':
            return math.pi
        if kind == 'var':
            if value not in self.variables:
                raise ExprError('unknown variable')
            return float(self.variables[value])
        if kind == 'func':
            argument = self.postfix()
            try:
                return float(_FUNCS[value](argument))
            except (ValueError, OverflowError):
                raise ExprError('bad function argument')
        if (kind, value) == ('op', '('):
            inner = self.expr()
            if self.take() != ('op', ')'):
                raise ExprError('missing )')
            return inner
        raise ExprError('unexpected token')


def evaluate(text, variables=None):
    """Safely evaluate a maths expression. Raises ExprError on anything unsupported."""
    text = normalize(text)
    if not text or len(text) > 60:
        raise ExprError('length')
    value = _Parser(_tokenize(text), variables).parse()
    if isinstance(value, complex) or math.isnan(value) or math.isinf(value):
        raise ExprError('not finite')
    return value


def _strip_units(text):
    return _UNIT_SUFFIX.sub('', normalize(text)).strip()


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol + 1e-9 * abs(b)


# --------------------------------------------------------------------------- formatting

_SUP = str.maketrans('0123456789-+', '⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺')
_SUB = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')


def sup(value):
    return str(value).translate(_SUP)


def sub(value):
    return str(value).translate(_SUB)


def fmt(value, places=None):
    if places is not None:
        return f'{value:.{places}f}'
    if isinstance(value, Fraction):
        return str(value.numerator) if value.denominator == 1 else f'{value.numerator}/{value.denominator}'
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f'{value:.6g}'


def signed(value):
    return f'+ {value}' if value >= 0 else f'− {abs(value)}'


def coef_str(coef, var='x'):
    if coef == 1:
        return var
    if coef == -1:
        return f'−{var}'
    return f'{coef}{var}'.replace('-', '−')


def poly_str(coefs, var='x'):
    """coefs are highest power first, e.g. [1, -5, 6] -> x² − 5x + 6."""
    degree = len(coefs) - 1
    out = ''
    for index, coef in enumerate(coefs):
        power = degree - index
        if coef == 0:
            continue
        if power == 0:
            body = str(abs(coef))
        else:
            body = (var if abs(coef) == 1 else f'{abs(coef)}{var}') + (sup(power) if power > 1 else '')
        if not out:
            out = ('−' if coef < 0 else '') + body
        else:
            out += f' {"−" if coef < 0 else "+"} {body}'
    return out or '0'


def squarefree_split(n):
    """n = a² · b with b squarefree -> (a, b)."""
    outside, inside = 1, n
    factor = 2
    while factor * factor <= inside:
        while inside % (factor * factor) == 0:
            inside //= factor * factor
            outside *= factor
        factor += 1
    return outside, inside


def surd_str(coef, radicand):
    coef = Fraction(coef)
    if radicand == 1:
        return fmt(coef)
    sign = '−' if coef < 0 else ''
    coef = abs(coef)
    head = '' if coef.numerator == 1 else str(coef.numerator)
    tail = '' if coef.denominator == 1 else f'/{coef.denominator}'
    return f'{sign}{head}√{radicand}{tail}'


def parse_surd(text):
    """'3√2', '√3/3', '2sqrt5', '-4rt(2)' -> (Fraction coef, radicand) exactly as typed, else None."""
    text = normalize(text).replace(' ', '').replace('*', '')
    match = re.fullmatch(r'(-?)(\d+)?(?:sqrt|rt)\(?(\d+)\)?(?:/(\d+))?', text)
    if match:
        sign, coef, radicand, denom = match.groups()
        value = Fraction(int(coef or 1), int(denom or 1))
        return (-value if sign else value), int(radicand)
    match = re.fullmatch(r'(-?\d+)(?:/(\d+))?', text)
    if match:
        return Fraction(int(match.group(1)), int(match.group(2) or 1)), 1
    return None


# --------------------------------------------------------------------------- questions

@dataclass
class Question:
    topic: str
    prompt: str
    kind: str
    answer: Any
    display: str
    hint: str = ''
    explanation: str = ''
    tol: float = 1e-6
    alts: list = field(default_factory=list)
    diagram: Optional[dict] = None
    forbid: list = field(default_factory=list)
    vocab: Optional[Callable[[str], bool]] = None
    level: int = 1


def num_q(topic, prompt, answer, hint='', explanation='', places=None, tol=None, alts=None, display=None, **extra):
    if tol is None:
        tol = 0.5 * 10 ** -places + 1e-9 if places is not None else 1e-6
    shown = display or (fmt(answer, places) if places is not None else fmt(answer))
    return Question(topic, prompt, 'number', float(answer), shown, hint, explanation, tol, alts or [], **extra)


def check_answer(question, text):
    """Returns 'correct', 'wrong', or None when the message doesn't look like an answer attempt."""
    text = text.strip()
    if not text or len(text) > 60:
        return None
    try:
        return _check(question, text)
    except (ExprError, ValueError, ZeroDivisionError, OverflowError):
        return None


def _check(q, text):
    kind = q.kind
    if kind == 'number':
        value = evaluate(_strip_units(text))
        targets = [q.answer] + list(q.alts)
        return 'correct' if any(close(value, target, q.tol) for target in targets) else 'wrong'

    if kind == 'fraction':
        cleaned = normalize(text).replace(' ', '')
        match = re.fullmatch(r'(-?\d+)/(\d+)', cleaned)
        if match:
            given = Fraction(int(match.group(1)), int(match.group(2)))
            reduced = math.gcd(int(match.group(1)), int(match.group(2))) == 1
            return 'correct' if given == q.answer and reduced else 'wrong'
        value = evaluate(cleaned)
        return 'correct' if close(value, float(q.answer), 1e-6) else 'wrong'

    if kind == 'surd':
        parsed = parse_surd(text)
        if parsed is None:
            evaluate(text)
            return 'wrong'
        return 'correct' if parsed == q.answer else 'wrong'

    if kind == 'expr':
        cleaned = normalize(text).replace(' ', '')
        if '(' in cleaned or cleaned in [normalize(item).replace(' ', '') for item in q.forbid]:
            return 'wrong'
        for point in (0.7, -1.3, 2.9, 4.1):
            if not close(evaluate(cleaned, {'x': point}), q.answer(point), 1e-6):
                return 'wrong'
        return 'correct'

    if kind in ('set', 'tuple'):
        return _check_collection(q, text)

    if kind == 'text':
        cleaned = re.sub(r'[^a-z0-9]', '', normalize(text))
        if q.vocab and not q.vocab(cleaned):
            return None
        return 'correct' if cleaned in q.answer else 'wrong'
    return None


def _strip_outer(text):
    text = text.strip()
    if text.startswith('(') and text.endswith(')'):
        depth = 0
        for index, char in enumerate(text):
            depth += (char == '(') - (char == ')')
            if depth == 0 and index < len(text) - 1:
                return text
        return text[1:-1]
    return text


def _check_collection(q, text):
    cleaned = re.sub(r'[\[\]{}]', '', normalize(text))
    cleaned = _strip_outer(re.sub(r'\band\b|\bor\b|&|;', ',', cleaned))
    items = [item.strip() for item in cleaned.split(',') if item.strip()]
    expected = len(q.answer)
    if len(items) == 1 and expected > 1:
        items = cleaned.split()
    if len(items) != expected:
        raise ExprError('count')

    labelled = {}
    values = []
    for item in items:
        match = re.fullmatch(r'([a-z])\s*=\s*(.+)', item)
        if match and q.kind == 'set':
            values.append(evaluate(match.group(2)))
        elif match:
            labelled[match.group(1)] = evaluate(match.group(2))
        else:
            values.append(evaluate(_strip_units(item)))
    if labelled:
        if len(labelled) != expected:
            return 'wrong'
        values = [labelled[key] for key in sorted(labelled)]
        if q.kind == 'set':
            values = sorted(values)
    elif q.kind == 'set':
        values = sorted(values)
    expected_values = sorted(q.answer) if q.kind == 'set' else list(q.answer)
    return 'correct' if all(close(a, b, q.tol) for a, b in zip(values, expected_values)) else 'wrong'


# --------------------------------------------------------------------------- generators

def _nz(r, low, high):
    value = 0
    while value == 0:
        value = r.randint(low, high)
    return value


# ---- arithmetic

def arith_add_sub(r, level):
    low, high = {1: (10, 99), 2: (100, 999), 3: (1000, 9999)}[level]
    a, b = r.randint(low, high), r.randint(low, high)
    if r.random() < 0.5:
        return num_q('arithmetic', f'{a} + {b}', a + b, 'Add the units first, then carry.')
    a, b = max(a, b), min(a, b)
    return num_q('arithmetic', f'{a} − {b}', a - b, 'Subtract column by column.')


def arith_times(r, level):
    a, b = {1: (r.randint(2, 12), r.randint(2, 12)), 2: (r.randint(11, 99), r.randint(3, 9)),
            3: (r.randint(12, 99), r.randint(12, 99))}[level]
    return num_q('arithmetic', f'{a} × {b}', a * b, 'Split one number into tens and units.')


def arith_divide(r, level):
    b = r.randint(2, 12) if level < 3 else r.randint(12, 25)
    answer = r.randint(3, 15) if level < 3 else r.randint(12, 60)
    return num_q('arithmetic', f'{b * answer} ÷ {b}', answer, f'Think: {b} × ? = {b * answer}.')


def arith_square(r, level):
    n = r.randint(6, 15) if level == 1 else r.randint(12, 30)
    return num_q('arithmetic', f'{n}²', n * n, 'Square = number × itself.')


def arith_bodmas(r, level):
    a, b, c, d = (r.randint(2, 9) for _ in range(4))
    forms = [
        (f'{a} + {b} × {c}', a + b * c),
        (f'({a} + {b}) × {c}', (a + b) * c),
        (f'{a * b} ÷ {b} + {c} × {d}', a + c * d),
        (f'{a} × ({b + c} − {d}) + {a}', a * (b + c - d) + a),
    ]
    text, answer = forms[r.randint(0, 1)] if level == 1 else r.choice(forms[1:])
    return num_q('arithmetic', f'Work out: {text}', answer, 'BODMAS: brackets, orders, ÷×, then +−.')


# ---- fractions & percentages

def frac_simplify(r, level):
    p, q = r.choice([(1, 2), (2, 3), (3, 4), (3, 5), (5, 6), (4, 7), (5, 8), (7, 9), (7, 10), (7, 12)])
    k = r.randint(2, 5 + level * 3)
    frac = Fraction(p * k, q * k)
    return Question('fractions', f'Simplify {p * k}/{q * k}', 'fraction', frac, fmt(frac),
                    'Divide top and bottom by their HCF. Answer as a/b.', level=level)


def frac_add(r, level):
    a, b = Fraction(r.randint(1, 5), r.choice([2, 3, 4, 5, 6])), Fraction(r.randint(1, 5), r.choice([3, 4, 6, 8]))
    op = r.choice(['+', '−'] if level > 1 else ['+'])
    if op == '−' and a < b:
        a, b = b, a
    result = a + b if op == '+' else a - b
    if level == 3 and r.random() < 0.5:
        result, text = a * b, f'({a}) × ({b})'
    else:
        text = f'{a} {op} {b}'
    return Question('fractions', f'Work out {text}. Give your answer as a simplified fraction.', 'fraction', result,
                    fmt(result), 'Use a common denominator (or multiply tops and bottoms).', level=level)


def percent_of(r, level):
    pct = r.choice([10, 20, 25, 50, 75] if level == 1 else [5, 12, 15, 35, 45, 60, 80])
    base = r.choice([40, 80, 120, 200, 360] if level == 1 else [60, 150, 240, 480, 640])
    return num_q('fractions', f'What is {pct}% of {base}?', pct * base / 100, 'Find 10% first, then scale.')


def percent_change(r, level):
    old = r.choice([50, 80, 120, 200, 250, 400])
    pct = r.choice([10, 15, 20, 25, 40])
    if r.random() < 0.5:
        new = old * (100 + pct) / 100
        return num_q('fractions', f'A price of {old} rises by {pct}%. What is the new price?', new, f'Multiply by {1 + pct / 100:g}.')
    new = old * (100 - pct) / 100
    return num_q('fractions', f'A {old} jacket is {pct}% off. What is the sale price?', new, f'Multiply by {1 - pct / 100:g}.')


def percent_reverse(r, level):
    original = r.choice([60, 80, 120, 150, 200, 250])
    pct = r.choice([20, 25, 40, 10])
    final = original * (100 - pct) // 100
    return num_q('fractions', f'After a {pct}% discount, a coat costs {final}. What was the original price?', original,
                 f'{final} is {100 - pct}% of the original → divide by {(100 - pct) / 100:g}.')


# ---- algebra

def alg_one_step(r, level):
    x = r.randint(2, 15)
    if r.random() < 0.5:
        a = r.randint(2, 12)
        return num_q('algebra', f'Solve {a}x = {a * x}', x, f'Divide both sides by {a}.')
    b = r.randint(3, 30)
    return num_q('algebra', f'Solve x + {b} = {x + b}', x, f'Subtract {b} from both sides.')


def alg_two_step(r, level):
    x, a, b = r.randint(-8, 12), r.randint(2, 9), r.randint(-15, 15)
    c = a * x + b
    return num_q('algebra', f'Solve {a}x {signed(b)} = {c}', x, f'Undo the {signed(b)} first, then divide by {a}.',
                 f'{a}x = {c - b} → x = {x}')


def alg_both_sides(r, level):
    x, a, c, b = r.randint(-6, 9), r.randint(4, 9), r.randint(1, 3), r.randint(-9, 9)
    d = a * x + b - c * x
    return num_q('algebra', f'Solve {a}x {signed(b)} = {c}x {signed(d)}', x,
                 'Collect the x terms on one side, numbers on the other.', f'{a - c}x = {d - b} → x = {x}')


def alg_substitute(r, level):
    a, b, c, x = r.randint(2, 5), _nz(r, -7, 7), _nz(r, -9, 9), r.randint(-4, 4)
    value = a * x * x + b * x + c
    return num_q('algebra', f'Find the value of {poly_str([a, b, c])} when x = {x}', value, 'Substitute carefully: use brackets for negatives.')


def alg_brackets(r, level):
    x, a, b, c = r.randint(-5, 8), r.randint(2, 5), r.randint(1, 6), r.randint(1, 4)
    rhs = a * (x + b) + c
    return num_q('algebra', f'Solve {a}(x + {b}) + {c} = {rhs}', x, 'Expand the bracket, then solve.')


def alg_simultaneous(r, level):
    x, y = r.randint(-4, 6), r.randint(-4, 6)
    a1, b1 = r.randint(1, 3), r.randint(1, 3)
    a2, b2 = r.randint(1, 4), -r.randint(1, 3)
    if a1 * b2 - a2 * b1 == 0:
        b2 -= 1
    c1, c2 = a1 * x + b1 * y, a2 * x + b2 * y
    prompt = f'Solve simultaneously:\n{a1}x + {b1}y = {c1}\n{a2}x {signed(b2)}y = {c2}\nAnswer as x, y'
    return Question('algebra', prompt.replace('1x', 'x').replace('1y', 'y'), 'tuple', [x, y], f'x = {x}, y = {y}',
                    'Eliminate one variable by adding/subtracting multiples of the equations.', level=level)


def alg_expand(r, level):
    a, b = _nz(r, -7, 7), _nz(r, -7, 7)
    if level == 2:
        text = f'(x {signed(a)})(x {signed(b)})'
        return Question('algebra', f'Expand and simplify {text}', 'expr', lambda x: (x + a) * (x + b),
                        poly_str([1, a + b, a * b]), 'FOIL: first, outer, inner, last. Type like x^2+5x+6.',
                        forbid=[text], level=level)
    p, q = r.randint(2, 4), _nz(r, -5, 5)
    text = f'({p}x {signed(a)})(x {signed(q)})'
    return Question('algebra', f'Expand and simplify {text}', 'expr', lambda x: (p * x + a) * (x + q),
                    poly_str([p, p * q + a, a * q]), 'Multiply every term in the first bracket by every term in the second.',
                    forbid=[text], level=level)


# ---- quadratics

def quad_roots(r, level):
    r1, r2 = _nz(r, -9, 9), _nz(r, -9, 9)
    while r2 == r1:
        r2 = _nz(r, -9, 9)
    a = 1 if level < 3 else r.randint(2, 3)
    coefs = [a, -a * (r1 + r2), a * r1 * r2]
    return Question('quadratics', f'Solve {poly_str(coefs)} = 0 (give both roots)', 'set', sorted([r1, r2]),
                    f'{min(r1, r2)}, {max(r1, r2)}', 'Factorise into two brackets, or use the formula.', level=level)


def quad_discriminant(r, level):
    a, b, c = r.randint(1, 4), _nz(r, -9, 9), _nz(r, -9, 9)
    return num_q('quadratics', f'Find the discriminant b² − 4ac of {poly_str([a, b, c])}', b * b - 4 * a * c,
                 f'a = {a}, b = {b}, c = {c}.')


def quad_vertex(r, level):
    a, h, k = r.randint(1, 3), r.randint(-5, 6), r.randint(-9, 9)
    b, c = -2 * a * h, a * h * h + k
    if level == 1:
        return num_q('quadratics', f'The graph of y = {poly_str([a, b, c])} has its turning point at x = ?', h,
                     'x = −b / 2a.')
    return num_q('quadratics', f'Find the minimum value of y = {poly_str([a, b, c])}', k, 'Complete the square, or substitute x = −b/2a.')


def quad_sum_product(r, level):
    r1, r2 = _nz(r, -8, 8), _nz(r, -8, 8)
    coefs = [1, -(r1 + r2), r1 * r2]
    if r.random() < 0.5:
        return num_q('quadratics', f'Without solving, what is the sum of the roots of {poly_str(coefs)} = 0?', r1 + r2, 'Sum = −b/a.')
    return num_q('quadratics', f'Without solving, what is the product of the roots of {poly_str(coefs)} = 0?', r1 * r2, 'Product = c/a.')


def quad_equal_roots(r, level):
    m = r.randint(2, 9)
    return num_q('quadratics', f'For what positive value of k does x² + kx + {m * m} = 0 have equal roots?', 2 * m,
                 'Equal roots ⇒ discriminant = 0.')


# ---- surds

def surd_simplify(r, level):
    a, b = r.randint(2, 7 if level == 1 else 12), r.choice([2, 3, 5, 6, 7, 10, 11])
    n = a * a * b
    return Question('surds', f'Simplify √{n}', 'surd', (Fraction(a), b), surd_str(a, b),
                    'Pull out the largest square factor. Type like 3√2.', f'√{n} = √{a * a} × √{b} = {a}√{b}', level=level)


def surd_multiply(r, level):
    a, b, c, d = r.randint(1, 4), r.choice([2, 3, 5, 6]), r.randint(2, 5), r.choice([2, 3, 5, 6, 8])
    outside, inside = squarefree_split(b * d)
    coef = a * c * outside
    text = f'{"" if a == 1 else a}√{b} × {c}√{d}'
    return Question('surds', f'Simplify {text}', 'surd', (Fraction(coef), inside), surd_str(coef, inside),
                    'Multiply the numbers outside, multiply the surds, then simplify.', level=level)


def surd_add(r, level):
    n = r.choice([2, 3, 5, 6, 7])
    a, b = r.randint(2, 5), r.randint(2, 4)
    big, small = a * a * n, b * b * n
    if r.random() < 0.5 or level == 1:
        return Question('surds', f'Simplify √{big} + √{small}', 'surd', (Fraction(a + b), n), surd_str(a + b, n),
                        'Simplify each surd first — then they are "like" surds.', level=level)
    if a == b:
        a += 1
        big = a * a * n
    return Question('surds', f'Simplify √{big} − √{small}', 'surd', (Fraction(a - b), n), surd_str(a - b, n),
                    'Simplify each surd first.', level=level)


def surd_rationalise(r, level):
    n = r.choice([2, 3, 5, 7])
    k = r.randint(1, 9)
    m = 1 if level == 2 else r.randint(2, 3)
    coef = Fraction(k, m * n)
    bottom = f'{"" if m == 1 else m}√{n}'
    return Question('surds', f'Rationalise the denominator of {k}/{bottom}', 'surd', (coef, n), surd_str(coef, n),
                    f'Multiply top and bottom by √{n}. Type like 2√3/3.', level=level)


def surd_numeric(r, level):
    a, n = r.randint(2, 5), r.choice([2, 3, 5, 7])
    if r.random() < 0.5:
        return num_q('surds', f'Calculate ({a}√{n})²', a * a * n, 'Square the number and square the root.')
    p = r.randint(3, 9)
    return num_q('surds', f'Calculate (√{p * p + n} + {p})(√{p * p + n} − {p})', n, 'Difference of two squares: (a+b)(a−b) = a² − b².')


# ---- indices

def idx_basic(r, level):
    base, power = r.choice([(2, 6), (3, 4), (5, 3), (2, 9), (4, 3), (7, 2), (6, 3), (10, 4)])
    return num_q('indices', f'Evaluate {base}{sup(power)}', base ** power, 'Multiply the base by itself that many times.')


def idx_negative(r, level):
    base, power = r.choice([(2, 3), (3, 2), (5, 2), (2, 4), (10, 3), (4, 2)])
    value = Fraction(1, base ** power)
    return Question('indices', f'Evaluate {base}{sup(-power)} (as a fraction)', 'fraction', value, fmt(value),
                    'A negative power means reciprocal: a⁻ⁿ = 1/aⁿ.', level=level)


def idx_fractional(r, level):
    base, num, den = r.choice([(8, 1, 3), (16, 1, 4), (25, 1, 2), (27, 2, 3), (16, 3, 4), (64, 2, 3), (32, 3, 5), (81, 3, 4)])
    value = round(base ** (num / den))
    return num_q('indices', f'Evaluate {base}^({num}/{den})', value, f'Take the {den}th root first, then raise to the power {num}.')


def idx_combine(r, level):
    base, m, n = r.randint(2, 5), r.randint(2, 9), r.randint(2, 9)
    if r.random() < 0.5:
        return num_q('indices', f'{base}{sup(m)} × {base}{sup(n)} = {base}^?  Find the missing power', m + n, 'Add the powers when multiplying.')
    m += n
    return num_q('indices', f'{base}{sup(m)} ÷ {base}{sup(n)} = {base}^?  Find the missing power', m - n, 'Subtract the powers when dividing.')


def idx_solve(r, level):
    base, x = r.choice([2, 3, 4, 5]), r.randint(2, 5)
    shift = r.randint(1, 3)
    return num_q('indices', f'Solve {base}^(x + {shift}) = {base ** (x + shift)}', x, f'Write the right side as {base} to a power.')


# ---- logarithms

def log_basic(r, level):
    base, power = r.choice([(2, 3), (2, 5), (3, 3), (10, 3), (5, 2), (3, 4), (2, 7), (4, 3), (10, 5)])
    return num_q('logs', f'Evaluate log{sub(base)} {base ** power}', power, f'What power of {base} gives {base ** power}?')


def log_add(r, level):
    base = r.choice([2, 3, 5, 10])
    p, q = r.randint(1, 4), r.randint(1, 4)
    if r.random() < 0.5:
        return num_q('logs', f'Evaluate log{sub(base)} {base ** p} + log{sub(base)} {base ** q}', p + q, 'log a + log b = log(ab).')
    p += q
    return num_q('logs', f'Evaluate log{sub(base)} {base ** p} − log{sub(base)} {base ** q}', p - q, 'log a − log b = log(a/b).')


def log_inverse(r, level):
    base, x = r.choice([2, 3, 5]), r.randint(2, 5)
    return num_q('logs', f'If log{sub(base)} x = {x}, find x', base ** x, f'x = {base}^{x}.')


def log_exponent_eq(r, level):
    base, x = r.choice([2, 3, 5]), r.randint(2, 5)
    return num_q('logs', f'Solve {base}^x = {base ** x}', x, 'Take logs, or match the powers.')


def log_fractional(r, level):
    base, num, den = r.choice([(4, 3, 2), (8, 2, 3), (9, 3, 2), (16, 3, 4), (27, 2, 3)])
    n = round(base ** (num / den))
    return num_q('logs', f'Evaluate log{sub(base)} {n}  (give a fraction or decimal)', num / den, f'{base}^? = {n}.', tol=5e-3, display=f'{num}/{den}')


# ---- trigonometry

_EXACT = [
    (0.0, '0'), (0.5, '1/2'), (-0.5, '−1/2'), (math.sqrt(2) / 2, '√2/2'), (-math.sqrt(2) / 2, '−√2/2'),
    (math.sqrt(3) / 2, '√3/2'), (-math.sqrt(3) / 2, '−√3/2'), (1.0, '1'), (-1.0, '−1'),
    (math.sqrt(3) / 3, '√3/3'), (-math.sqrt(3) / 3, '−√3/3'), (math.sqrt(3), '√3'), (-math.sqrt(3), '−√3'),
]


def exact_str(value):
    for target, text in _EXACT:
        if abs(value - target) < 1e-9:
            return text
    return fmt(value)


def trig_exact(r, level):
    angles = {1: [0, 30, 45, 60, 90], 2: [0, 30, 45, 60, 90, 120, 135, 150, 180],
              3: [120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330]}[level]
    func = r.choice(['sin', 'cos', 'tan'] if level > 1 else ['sin', 'cos'])
    angle = r.choice(angles)
    if func == 'tan' and angle % 180 == 90:
        func = 'sin'
    value = {'sin': math.sin, 'cos': math.cos, 'tan': math.tan}[func](math.radians(angle))
    return num_q('trig', f'Find the exact value of {func} {angle}°', value, 'Use the special-angle triangles. Type like √3/2.',
                 tol=1e-3, display=exact_str(value))


def trig_side(r, level):
    theta = r.choice([25, 30, 35, 40, 50, 55, 60, 65])
    hyp = r.randint(8, 20)
    t = math.radians(theta)
    opp, adj = hyp * math.sin(t), hyp * math.cos(t)
    mode = r.choice(['opp', 'adj'] if level == 1 else ['opp', 'adj', 'hyp', 'tan'])
    if mode == 'opp':
        diagram = {'type': 'triangle', 'angle': theta, 'hyp': str(hyp), 'opp': 'x', 'adj': ''}
        return num_q('trig', f'Find x, the side opposite {theta}° (hypotenuse = {hyp}). Give 1 decimal place.', round(opp, 1),
                     'SOH: sin θ = opposite ÷ hypotenuse.', places=1, diagram=diagram, tol=0.06)
    if mode == 'adj':
        diagram = {'type': 'triangle', 'angle': theta, 'hyp': str(hyp), 'opp': '', 'adj': 'x'}
        return num_q('trig', f'Find x, the side next to the {theta}° angle (hypotenuse = {hyp}). Give 1 decimal place.', round(adj, 1),
                     'CAH: cos θ = adjacent ÷ hypotenuse.', places=1, diagram=diagram, tol=0.06)
    if mode == 'hyp':
        diagram = {'type': 'triangle', 'angle': theta, 'hyp': 'x', 'opp': f'{opp:.1f}', 'adj': ''}
        return num_q('trig', f'Find the hypotenuse x when the opposite side is {opp:.1f} and the angle is {theta}°. Give 1 decimal place.',
                     round(hyp, 1), 'Rearrange sin θ = opp ÷ hyp.', places=1, diagram=diagram, tol=0.2)
    diagram = {'type': 'triangle', 'angle': theta, 'hyp': '', 'opp': 'x', 'adj': f'{adj:.1f}'}
    return num_q('trig', f'Find x (opposite) when the adjacent side is {adj:.1f} and the angle is {theta}°. Give 1 decimal place.',
                 round(opp, 1), 'TOA: tan θ = opposite ÷ adjacent.', places=1, diagram=diagram, tol=0.2)


def trig_angle(r, level):
    a, b, c = r.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (6, 8, 10)])
    if r.random() < 0.5:
        angle = math.degrees(math.atan2(a, b))
        diagram = {'type': 'triangle', 'angle': '?', 'hyp': '', 'opp': str(a), 'adj': str(b), 'angle_value': angle}
        return num_q('trig', f'Find the angle θ (opposite = {a}, adjacent = {b}). Give 1 decimal place.', round(angle, 1),
                     'θ = tan⁻¹(opp ÷ adj).', places=1, diagram=diagram, tol=0.06)
    angle = math.degrees(math.asin(a / c))
    diagram = {'type': 'triangle', 'angle': '?', 'hyp': str(c), 'opp': str(a), 'adj': '', 'angle_value': angle}
    return num_q('trig', f'Find the angle θ (opposite = {a}, hypotenuse = {c}). Give 1 decimal place.', round(angle, 1),
                 'θ = sin⁻¹(opp ÷ hyp).', places=1, diagram=diagram, tol=0.06)


def trig_radians(r, level):
    degrees = r.choice([30, 45, 60, 90, 120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330, 360])
    frac = Fraction(degrees, 180)
    shown = 'π' if frac == 1 else (f'{frac.numerator if frac.numerator != 1 else ""}π' + (f'/{frac.denominator}' if frac.denominator != 1 else ''))
    if r.random() < 0.5:
        return num_q('trig', f'Convert {degrees}° to radians (in terms of π, e.g. 5π/6)', math.radians(degrees),
                     'Multiply by π/180.', tol=1e-3, display=shown)
    return num_q('trig', f'Convert {shown} radians to degrees', degrees, 'Multiply by 180/π.', tol=1e-3)


def trig_identity(r, level):
    a, b, c = r.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29)])
    if level == 1 or r.random() < 0.34:
        return num_q('trig', f'θ is acute and sin θ = {a}/{c}. Find cos θ.', b / c, 'Use sin²θ + cos²θ = 1.', display=f'{b}/{c}', tol=5e-3)
    if level == 2 or r.random() < 0.5:
        return num_q('trig', f'θ is acute and sin θ = {a}/{c}. Find tan θ.', a / b, 'tan θ = sin θ ÷ cos θ.', display=f'{a}/{b}', tol=5e-3)
    return num_q('trig', f'θ is acute and sin θ = {a}/{c}. Find sin 2θ.', 2 * a * b / (c * c), 'sin 2θ = 2 sin θ cos θ.',
                 display=f'{2 * a * b}/{c * c}', tol=5e-3)


_SOLVE = [
    ('sin x = 1/2', [30, 150]), ('sin x = √2/2', [45, 135]), ('sin x = √3/2', [60, 120]),
    ('cos x = 1/2', [60, 300]), ('cos x = √2/2', [45, 315]), ('cos x = −1/2', [120, 240]),
    ('tan x = 1', [45, 225]), ('tan x = √3', [60, 240]), ('sin x = −1/2', [210, 330]), ('cos x = −√3/2', [150, 210]),
]


def trig_solve(r, level):
    text, solutions = r.choice(_SOLVE)
    return Question('trig', f'Solve {text} for 0° ≤ x ≤ 360°. Give all solutions.', 'set', solutions, ', '.join(map(str, solutions)),
                    'Find the first angle, then use the CAST diagram / symmetry.', tol=1e-6, level=level)


def trig_area(r, level):
    a, b, angle = r.randint(4, 12), r.randint(4, 12), r.choice([30, 45, 60, 90, 150])
    return num_q('trig', f'Area of a triangle with sides {a} and {b} and the angle {angle}° between them? (1 decimal place)',
                 round(0.5 * a * b * math.sin(math.radians(angle)), 1), 'Area = ½ab sin C.', places=1, tol=0.06)


# ---- geometry

def geo_rectangle(r, level):
    w, h = r.randint(3, 15), r.randint(3, 15)
    if r.random() < 0.5:
        return num_q('geometry', f'Area of a {w} × {h} rectangle?', w * h, 'Area = length × width.')
    return num_q('geometry', f'Perimeter of a {w} × {h} rectangle?', 2 * (w + h), 'Add all four sides.')


def geo_triangle(r, level):
    b, h = r.randint(4, 20), r.randint(3, 15)
    return num_q('geometry', f'Area of a triangle with base {b} and height {h}?', b * h / 2, 'Area = ½ × base × height.')


def geo_circle(r, level):
    radius = r.randint(2, 12)
    if r.random() < 0.5:
        return num_q('geometry', f'Area of a circle with radius {radius}? (1 dp)', math.pi * radius ** 2, 'Area = πr².', places=1, tol=0.06)
    return num_q('geometry', f'Circumference of a circle with radius {radius}? (1 dp)', 2 * math.pi * radius, 'C = 2πr.', places=1, tol=0.06)


def geo_pythagoras(r, level):
    a, b, c = r.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (6, 8, 10), (9, 12, 15), (20, 21, 29)])
    if r.random() < 0.5:
        diagram = {'type': 'triangle', 'angle': '', 'hyp': 'x', 'opp': str(a), 'adj': str(b)}
        return num_q('geometry', f'A right-angled triangle has legs {a} and {b}. Find the hypotenuse x.', c, 'a² + b² = c².', diagram=diagram)
    diagram = {'type': 'triangle', 'angle': '', 'hyp': str(c), 'opp': str(a), 'adj': 'x'}
    return num_q('geometry', f'A right-angled triangle has hypotenuse {c} and one leg {a}. Find the other leg x.', b, 'b² = c² − a².', diagram=diagram)


def geo_polygon(r, level):
    n = r.randint(5, 12)
    if r.random() < 0.5:
        return num_q('geometry', f'What is the sum of the interior angles of a polygon with {n} sides?', (n - 2) * 180, 'Sum = (n − 2) × 180°.')
    n = r.choice([5, 6, 8, 9, 10, 12])
    return num_q('geometry', f'What is each exterior angle of a regular {n}-sided polygon?', 360 / n, 'Exterior angles add to 360°.')


def geo_volume(r, level):
    radius, height = r.randint(2, 8), r.randint(3, 12)
    if r.random() < 0.5:
        return num_q('geometry', f'Volume of a cylinder: radius {radius}, height {height}? (nearest whole number)',
                     round(math.pi * radius ** 2 * height), 'V = πr²h.', tol=0.51)
    return num_q('geometry', f'Volume of a sphere with radius {radius}? (nearest whole number)', round(4 / 3 * math.pi * radius ** 3),
                 'V = 4/3 πr³.', tol=0.51)


def geo_coordinates(r, level):
    x1, y1 = r.randint(-5, 5), r.randint(-5, 5)
    if r.random() < 0.5:
        dx, dy, dist = r.choice([(3, 4, 5), (5, 12, 13), (6, 8, 10), (8, 15, 17)])
        return num_q('geometry', f'Distance between ({x1}, {y1}) and ({x1 + dx}, {y1 + dy})?', dist, 'd = √(Δx² + Δy²).')
    x2, y2 = x1 + 2 * r.randint(1, 5), y1 + 2 * r.randint(-4, 4)
    mid = [(x1 + x2) // 2, (y1 + y2) // 2]
    return Question('geometry', f'Midpoint of ({x1}, {y1}) and ({x2}, {y2})? Answer as x, y', 'tuple', mid, f'({mid[0]}, {mid[1]})',
                    'Average the x-values and the y-values.', level=level)


# ---- sequences

def seq_arith(r, level):
    a, d, n = r.randint(1, 12), _nz(r, -5, 8), r.randint(10, 30)
    terms = ', '.join(str(a + d * i) for i in range(4))
    return num_q('sequences', f'Arithmetic sequence: {terms}, … Find term number {n}.', a + (n - 1) * d, 'uₙ = a + (n − 1)d.')


def seq_sum(r, level):
    a, d, n = r.randint(1, 10), r.randint(1, 6), r.randint(8, 20)
    return num_q('sequences', f'Sum of the first {n} terms of the sequence {a}, {a + d}, {a + 2 * d}, …?', n * (2 * a + (n - 1) * d) // 2,
                 'Sₙ = n/2 × (2a + (n − 1)d).')


def seq_geo(r, level):
    a, ratio, n = r.randint(1, 5), r.randint(2, 4), r.randint(4, 7)
    terms = ', '.join(str(a * ratio ** i) for i in range(3))
    return num_q('sequences', f'Geometric sequence: {terms}, … Find term number {n}.', a * ratio ** (n - 1), 'uₙ = a·rⁿ⁻¹.')


def seq_next(r, level):
    shift = r.randint(0, 5)
    kind = r.choice(['squares', 'tri', 'cubes'])
    if kind == 'squares':
        terms = [i * i + shift for i in range(1, 6)]
        nxt = 36 + shift
    elif kind == 'tri':
        terms = [i * (i + 1) // 2 for i in range(1, 6)]
        nxt = 21
    else:
        terms = [i ** 3 for i in range(1, 5)]
        nxt = 125
    return num_q('sequences', f'Next term: {", ".join(map(str, terms))}, …', nxt, 'Look at the differences between terms.')


def seq_infinite(r, level):
    a = r.randint(1, 9) * 2
    ratio = r.choice([Fraction(1, 2), Fraction(1, 3), Fraction(2, 3), Fraction(1, 4), Fraction(3, 4)])
    total = Fraction(a) / (1 - ratio)
    return num_q('sequences', f'Sum to infinity of the geometric series with first term {a} and common ratio {ratio}?', float(total),
                 'S∞ = a / (1 − r).', display=fmt(total))


# ---- calculus

def calc_derivative(r, level):
    a, n, k = r.randint(1, 5), r.randint(2, 4), r.randint(1, 3)
    b = r.randint(1, 9)
    func = f'{a if a > 1 else ""}x{sup(n)} + {b}x'
    return num_q('calculus', f'f(x) = {func}. Find f′({k}).', a * n * k ** (n - 1) + b, 'Power rule: d/dx xⁿ = n·xⁿ⁻¹.')


def calc_integral(r, level):
    a, k = r.randint(1, 6), r.randint(1, 4)
    return num_q('calculus', f'Evaluate the definite integral of {2 * a}x from 0 to {k}', a * k * k, '∫ 2ax dx = a x².')


def calc_stationary(r, level):
    h, k = r.randint(1, 8), r.randint(-9, 9)
    b, c = -2 * h, h * h + k
    return num_q('calculus', f'y = {poly_str([1, b, c])}. Find the x-coordinate of the stationary point.', h, 'Set dy/dx = 0.')


def calc_integral2(r, level):
    a, b, k = r.randint(1, 4), r.randint(1, 6), r.randint(1, 3)
    value = Fraction(a * k ** 3, 3) + Fraction(b * k ** 2, 2)
    return num_q('calculus', f'Evaluate ∫ from 0 to {k} of ({a}x² + {b}x) dx. Give a fraction or decimal.', float(value),
                 'Integrate term by term then substitute the limits.', display=fmt(value), tol=5e-3)


def calc_chain(r, level):
    a, k = r.randint(2, 4), r.randint(1, 3)
    inner = k * k + 1
    return num_q('calculus', f'f(x) = (x² + 1){sup(a)}. Find f′({k}).', a * inner ** (a - 1) * 2 * k, 'Chain rule: f′ = n(x²+1)ⁿ⁻¹ · 2x.')


# ---- statistics & probability

def stats_mean(r, level):
    count = r.randint(4, 6)
    values = [r.randint(2, 20) for _ in range(count)]
    values[-1] += (count - sum(values) % count) % count
    return num_q('stats', f'Find the mean of {", ".join(map(str, values))}', sum(values) / count, 'Add them up, divide by how many.')


def stats_median(r, level):
    values = [r.randint(1, 30) for _ in range(r.choice([5, 7]))]
    shown = ', '.join(map(str, values))
    if r.random() < 0.5:
        return num_q('stats', f'Find the median of {shown}', sorted(values)[len(values) // 2], 'Sort first, take the middle.')
    return num_q('stats', f'Find the range of {shown}', max(values) - min(values), 'Range = largest − smallest.')


def stats_prob(r, level):
    red, blue, green = r.randint(2, 6), r.randint(2, 6), r.randint(1, 5)
    total = red + blue + green
    color = r.choice([('red', red), ('blue', blue), ('green', green)])
    p = Fraction(color[1], total)
    return Question('stats', f'A bag has {red} red, {blue} blue and {green} green balls. P({color[0]}) as a simplified fraction?', 'fraction', p,
                    fmt(p), 'P = favourable ÷ total. Simplify!', level=level)


def stats_dice(r, level):
    target = r.randint(2, 12)
    ways = 6 - abs(target - 7)
    p = Fraction(ways, 36)
    return Question('stats', f'Two fair dice are rolled. P(sum = {target}) as a simplified fraction?', 'fraction', p, fmt(p),
                    'Count the pairs that make that sum out of 36.', level=level)


def stats_combinations(r, level):
    n, k = r.randint(5, 10), r.randint(2, 4)
    if r.random() < 0.5:
        return num_q('stats', f'How many ways to choose {k} people from {n}? (ⁿCᵣ)', math.comb(n, k), 'nCr = n! / (r!(n−r)!).')
    return num_q('stats', f'How many ways to arrange {k} of {n} different books on a shelf? (ⁿPᵣ)', math.perm(n, k), 'nPr = n! / (n−r)!.')


def stats_without_replacement(r, level):
    red, blue = r.randint(3, 6), r.randint(2, 5)
    total = red + blue
    p = Fraction(red, total) * Fraction(red - 1, total - 1)
    return Question('stats', f'A bag has {red} red and {blue} blue balls. Two are drawn without replacement. P(both red) as a simplified fraction?',
                    'fraction', p, fmt(p), 'Multiply: P(first red) × P(second red | first red).', level=level)


# ---- number theory

def _is_prime(n):
    return n > 1 and all(n % d for d in range(2, int(n ** 0.5) + 1))


def num_gcd_lcm(r, level):
    g = r.randint(2, 9)
    a, b = g * r.randint(2, 7), g * r.randint(2, 7)
    if r.random() < 0.5:
        return num_q('numbers', f'Find the HCF of {a} and {b}', math.gcd(a, b), 'The largest number dividing both.')
    return num_q('numbers', f'Find the LCM of {a} and {b}', a * b // math.gcd(a, b), 'The smallest number both divide into.')


def num_prime(r, level):
    n = r.randint(20, 120 if level < 3 else 400)
    answer = ['yes', 'y', 'true'] if _is_prime(n) else ['no', 'n', 'false']
    return Question('numbers', f'Is {n} a prime number? (yes / no)', 'text', answer, answer[0], 'Try dividing by 2, 3, 5, 7, 11…',
                    vocab=lambda s: s in ('yes', 'no', 'y', 'n', 'true', 'false'), level=level)


def num_remainder(r, level):
    divisor = r.randint(3, 9)
    n = r.randint(50, 400)
    if level == 3:
        base, power = r.randint(2, 7), r.randint(3, 6)
        return num_q('numbers', f'What is {base}{sup(power)} mod {divisor}? (the remainder)', pow(base, power, divisor), 'Work it out step by step, reducing mod early.')
    return num_q('numbers', f'What is the remainder when {n} is divided by {divisor}?', n % divisor, 'Find the biggest multiple below, then subtract.')


def num_binary(r, level):
    n = r.randint(5, 60)
    if r.random() < 0.5:
        return num_q('numbers', f'Convert binary {n:b} to decimal', n, 'Powers of two: 32, 16, 8, 4, 2, 1.')
    return Question('numbers', f'Convert {n} to binary', 'text', [f'{n:b}'], f'{n:b}', 'Divide by 2 repeatedly; read remainders upward.',
                    vocab=lambda s: bool(re.fullmatch(r'[01]+', s)), level=level)


def num_factors(r, level):
    n = r.choice([12, 18, 20, 24, 28, 30, 36, 40, 48, 60, 72, 84, 90, 96, 100])
    count = sum(1 for d in range(1, n + 1) if n % d == 0)
    return num_q('numbers', f'How many factors does {n} have?', count, 'Pair them up: d and n/d.')


# ---- vectors & matrices

def vec_dot(r, level):
    a, b = [r.randint(-5, 6) for _ in range(2)], [r.randint(-5, 6) for _ in range(2)]
    return num_q('vectors', f'Dot product of ({a[0]}, {a[1]}) and ({b[0]}, {b[1]})', a[0] * b[0] + a[1] * b[1], 'a·b = a₁b₁ + a₂b₂.')


def vec_add(r, level):
    a, b = [r.randint(-6, 8) for _ in range(2)], [r.randint(-6, 8) for _ in range(2)]
    k = r.randint(2, 3)
    if level == 1:
        return Question('vectors', f'Add the vectors ({a[0]}, {a[1]}) + ({b[0]}, {b[1]}). Answer as x, y', 'tuple', [a[0] + b[0], a[1] + b[1]],
                        f'({a[0] + b[0]}, {a[1] + b[1]})', 'Add the matching components.', level=level)
    result = [k * a[0] - b[0], k * a[1] - b[1]]
    return Question('vectors', f'Find {k}a − b where a = ({a[0]}, {a[1]}) and b = ({b[0]}, {b[1]}). Answer as x, y', 'tuple', result,
                    f'({result[0]}, {result[1]})', 'Scale first, then subtract.', level=level)


def vec_magnitude(r, level):
    a, b, c = r.choice([(3, 4, 5), (5, 12, 13), (6, 8, 10), (8, 15, 17)])
    if level < 3:
        return num_q('vectors', f'Magnitude of the vector ({a}, {b})', c, '|v| = √(x² + y²).')
    x, y = r.randint(1, 5), r.randint(1, 5)
    outside, inside = squarefree_split(x * x + y * y)
    return Question('vectors', f'Exact magnitude of ({x}, {y}). Give a surd in simplest form (or an integer).', 'surd',
                    (Fraction(outside), inside), surd_str(outside, inside), '|v| = √(x² + y²), then simplify the surd.', level=level)


def vec_determinant(r, level):
    a, b, c, d = (r.randint(-4, 7) for _ in range(4))
    return num_q('vectors', f'Determinant of the matrix [[{a}, {b}], [{c}, {d}]]', a * d - b * c, 'det = ad − bc.')


def vec_matrix_entry(r, level):
    a, b, c, d = (r.randint(1, 5) for _ in range(4))
    e, f, g, h = (r.randint(1, 5) for _ in range(4))
    entry = a * e + b * g
    return num_q('vectors', f'Multiply [[{a}, {b}], [{c}, {d}]] × [[{e}, {f}], [{g}, {h}]]. What is the top-left entry?', entry,
                 'Row 1 of the first × column 1 of the second.')


@dataclass
class Topic:
    key: str
    title: str
    emoji: str
    blurb: str
    colors: tuple
    generators: dict
    aliases: tuple = ()


def _by_level(*groups):
    return {level: list(gens) for level, gens in enumerate(groups, start=1)}


TOPICS = {
    'arithmetic': Topic('arithmetic', 'Arithmetic', '🔢', 'Mental maths: add, times, divide, squares, BODMAS.', ((255, 154, 68), (255, 94, 98)),
                        _by_level([arith_add_sub, arith_times, arith_divide, arith_square, arith_bodmas],
                                  [arith_add_sub, arith_times, arith_divide, arith_square, arith_bodmas],
                                  [arith_add_sub, arith_times, arith_divide, arith_square, arith_bodmas]), ('mental', 'arith')),
    'fractions': Topic('fractions', 'Fractions & Percentages', '🍕', 'Simplify, add, percentages, discounts.', ((255, 195, 113), (255, 95, 109)),
                       _by_level([frac_simplify, frac_add, percent_of], [frac_add, percent_of, percent_change], [frac_add, percent_change, percent_reverse]),
                       ('percent', 'percentages', 'fraction')),
    'algebra': Topic('algebra', 'Algebra', '🧮', 'Equations, brackets, expanding, simultaneous equations.', ((106, 17, 203), (37, 117, 252)),
                     _by_level([alg_one_step, alg_two_step], [alg_two_step, alg_both_sides, alg_substitute, alg_brackets, alg_expand],
                               [alg_both_sides, alg_brackets, alg_simultaneous, alg_expand, alg_substitute]), ('alg',)),
    'quadratics': Topic('quadratics', 'Quadratics', '📈', 'Roots, discriminant, turning points, completing the square.', ((0, 198, 255), (0, 114, 255)),
                        _by_level([quad_roots, quad_discriminant, quad_sum_product], [quad_roots, quad_vertex, quad_sum_product, quad_discriminant],
                                  [quad_roots, quad_vertex, quad_equal_roots]), ('quadratic', 'quad')),
    'surds': Topic('surds', 'Surds', '🌱', 'Simplify, multiply, add and rationalise surds.', ((17, 153, 142), (56, 239, 125)),
                   _by_level([surd_simplify, surd_numeric], [surd_simplify, surd_multiply, surd_add, surd_numeric],
                             [surd_multiply, surd_add, surd_rationalise, surd_numeric]), ('surd', 'roots')),
    'indices': Topic('indices', 'Indices & Powers', '⚡', 'Powers, negative and fractional indices, index laws.', ((247, 151, 30), (255, 210, 0)),
                     _by_level([idx_basic, idx_combine], [idx_basic, idx_negative, idx_combine, idx_fractional], [idx_negative, idx_fractional, idx_solve]),
                     ('index', 'powers', 'exponents')),
    'logs': Topic('logs', 'Logarithms', '🪵', 'Evaluate and solve with logs.', ((161, 140, 209), (251, 194, 235)),
                  _by_level([log_basic, log_inverse], [log_basic, log_add, log_exponent_eq], [log_add, log_fractional, log_inverse, log_exponent_eq]),
                  ('log', 'logarithm', 'logarithms')),
    'trig': Topic('trig', 'Trigonometry', '📐', 'Exact values, right triangles, radians, identities, equations.', ((255, 65, 108), (255, 75, 43)),
                  _by_level([trig_exact, trig_side, trig_identity], [trig_exact, trig_side, trig_angle, trig_radians, trig_identity],
                            [trig_exact, trig_side, trig_angle, trig_radians, trig_identity, trig_solve, trig_area]),
                  ('trigonometry', 'sincos')),
    'geometry': Topic('geometry', 'Geometry', '🔷', 'Area, volume, Pythagoras, polygons, coordinates.', ((67, 206, 162), (24, 90, 157)),
                      _by_level([geo_rectangle, geo_triangle, geo_pythagoras], [geo_circle, geo_pythagoras, geo_polygon, geo_triangle],
                                [geo_circle, geo_volume, geo_coordinates, geo_polygon]), ('geo', 'shapes')),
    'sequences': Topic('sequences', 'Sequences & Series', '🪜', 'Arithmetic, geometric, sums and patterns.', ((131, 58, 180), (253, 29, 29)),
                       _by_level([seq_arith, seq_next], [seq_arith, seq_sum, seq_geo], [seq_sum, seq_geo, seq_infinite]), ('sequence', 'series', 'seq')),
    'calculus': Topic('calculus', 'Calculus', '♾️', 'Differentiate and integrate polynomials.', ((20, 30, 48), (36, 59, 85)),
                      _by_level([calc_derivative, calc_integral], [calc_derivative, calc_integral, calc_stationary],
                                [calc_integral2, calc_stationary, calc_chain, calc_derivative]), ('calc', 'derivative', 'differentiation')),
    'stats': Topic('stats', 'Statistics & Probability', '🎲', 'Averages, probability, combinations.', ((255, 128, 8), (255, 200, 55)),
                   _by_level([stats_mean, stats_median, stats_prob], [stats_prob, stats_dice, stats_median, stats_combinations],
                             [stats_dice, stats_combinations, stats_without_replacement]), ('statistics', 'probability', 'prob')),
    'numbers': Topic('numbers', 'Number Theory', '🧩', 'HCF/LCM, primes, remainders, binary.', ((0, 180, 219), (0, 131, 176)),
                     _by_level([num_gcd_lcm, num_prime, num_factors], [num_gcd_lcm, num_prime, num_remainder, num_binary],
                               [num_remainder, num_binary, num_factors, num_prime]), ('number', 'numtheory', 'primes')),
    'vectors': Topic('vectors', 'Vectors & Matrices', '🧭', 'Dot products, magnitudes, determinants.', ((86, 204, 242), (47, 128, 237)),
                     _by_level([vec_dot, vec_add, vec_determinant], [vec_add, vec_magnitude, vec_determinant, vec_dot],
                               [vec_magnitude, vec_matrix_entry, vec_determinant]), ('vector', 'matrix', 'matrices')),
}

LEVELS = {'easy': 1, 'medium': 2, 'hard': 3, 'e': 1, 'm': 2, 'h': 3, '1': 1, '2': 2, '3': 3}
LEVEL_NAMES = {1: 'Easy', 2: 'Medium', 3: 'Hard'}


def find_topic(name):
    name = (name or '').lower().strip()
    for key, topic in TOPICS.items():
        if name == key or name in topic.aliases:
            return topic
    return None


def generate(topic_key, level=2, rng=None):
    rng = rng or random.Random()
    topic = TOPICS[topic_key]
    question = rng.choice(topic.generators[level])(rng, level)
    question.topic = topic_key
    question.level = level
    return question
