import io
import random
import decimal
from dataclasses import dataclass
from typing_extensions import TypeAlias


@dataclass
class Rounding:
    swift_name: str
    encoded: str
    python: str

    def __str__(self) -> str:
        return self.swift_name

    def __eq__(self, o: object) -> bool:
        return id(self) == id(o)


ROUNDING_UP = Rounding("up", ">", decimal.ROUND_CEILING)
ROUNDING_DOWN = Rounding("down", "<", decimal.ROUND_FLOOR)
ROUNDING_TO_ZERO = Rounding("towardZero", "0", decimal.ROUND_DOWN)
ROUNDING_TO_NEAREST_OR_EVEN = Rounding("toNearestOrEven", "=0", decimal.ROUND_HALF_EVEN)
ROUNDING_TO_NEAREST_OR_AWAY_FROM_ZERO = Rounding(
    "toNearestOrAwayFromZero", "h>", decimal.ROUND_HALF_UP
)

ROUNDINGS: list[Rounding] = [
    ROUNDING_UP,
    ROUNDING_DOWN,
    ROUNDING_TO_ZERO,
    ROUNDING_TO_NEAREST_OR_EVEN,
    ROUNDING_TO_NEAREST_OR_AWAY_FROM_ZERO,
]


@dataclass
class DecimalTuple:
    is_negative: bool
    significand: int
    exponent: int


@dataclass
class Decimal:
    value: decimal.Decimal

    def __str__(self) -> str:
        t = self.as_tuple()

        if t is None:
            return self.value.to_eng_string()

        sign = "" if t.is_negative == 0 else "-"
        return f"{sign}{t.significand}E{t.exponent}"

    def as_tuple(self) -> DecimalTuple | None:
        if not self.value.is_finite():
            return None

        t = self.value.as_tuple()

        significand = 0
        for d in t.digits:
            significand *= 10
            significand += d

        sign = bool(t.sign)
        exponent = int(t.exponent)
        return DecimalTuple(sign, significand, exponent)

    @staticmethod
    def from_tuple(ctx: "Context", t: DecimalTuple) -> "Decimal":
        significand = t.significand
        exponent = t.exponent

        if significand == ctx.max_decimal_digits + 1:
            significand //= 10
            exponent += 1

        # We are not allowed to modify flags on the original 'ctx'.
        ctx_copy = ctx._python_context.copy()
        result = ctx_copy.scaleb(significand, exponent)

        if t.is_negative:
            result = result.copy_negate()

        return Decimal(result)


FlagType: TypeAlias = type[decimal.DecimalException]
FLAG_UNDERFLOW: FlagType = decimal.Underflow
FLAG_OVERFLOW: FlagType = decimal.Overflow
FLAG_INEXACT: FlagType = decimal.Inexact
FLAG_INVALID_OPERATION: FlagType = decimal.InvalidOperation
FLAG_DIVISION_BY_ZERO: FlagType = decimal.DivisionByZero
FLAG_ROUNDED: FlagType = decimal.Rounded
FLAG_SUBNORMAL: FlagType = decimal.Subnormal
FLAG_CLAMPED: FlagType = decimal.Clamped


class Flags:
    def __init__(self, context: decimal.Context) -> None:
        self._python_context = context
        self._all = [
            decimal.Underflow,
            decimal.Overflow,
            decimal.Inexact,
            decimal.InvalidOperation,
            decimal.DivisionByZero,
            decimal.Subnormal,
            # We don't care about those:
            # decimal.Rounded,
            # decimal.Clamped,
        ]

    def is_set(self, flag: FlagType):
        return self._python_context.flags[flag]

    def set(self, flag: FlagType):
        self._python_context.flags[flag] = True

    def clear(self, *args: FlagType):
        for a in args:
            self._python_context.flags[a] = False

    def clear_all(self):
        self._python_context.clear_flags()

    def disable_exceptions(self):
        self._python_context.clear_traps()

    def assert_is_set(self, flag: FlagType, message: str = ""):
        is_set = self._python_context.flags[flag]
        if not is_set:
            m = self._create_assert_message(message, [flag])
            assert False, m

    def assert_empty(
        self,
        message: str = "",
        *,
        excluding: FlagType | list[FlagType] | None = None,
    ):
        flags: list[FlagType] = []

        for f in self._all:
            is_excluded = False

            if isinstance(excluding, list):
                for e in excluding:
                    is_excluded = is_excluded or id(f) == id(e)
            else:
                is_excluded = id(f) == id(excluding)

            if self._python_context.flags[f] and not is_excluded:
                flags.append(f)

        if flags:
            m = self._create_assert_message(message, flags)
            assert False, m

    def _create_assert_message(self, message: str, flags: list[FlagType]) -> str:
        result = ""
        if message:
            result += message
            result += ": "

        return result + ", ".join(map(lambda f: f.__name__, flags))


class Context:
    def __init__(
        self,
        file_header: str,
        swift_name: str,
        bit_width: int,
        precision: int,
        trailing_significand_width: int,
        max_decimal_digits: int,
        min_signed_exponent: int,
        max_signed_exponent: int,
    ) -> None:
        self.file_header = file_header
        self.swift_name = swift_name
        self.bit_width = bit_width
        self.precision = precision
        self.trailing_significand_width = trailing_significand_width
        self.max_decimal_digits = max_decimal_digits
        self.min_signed_exponent = min_signed_exponent
        self.max_signed_exponent = max_signed_exponent

        self._python_context = decimal.Context(
            prec=precision,
            rounding=ROUNDING_TO_ZERO.python,
            Emin=min_signed_exponent + precision - 1,
            Emax=max_signed_exponent + precision - 1,
            capitals=True,
            clamp=1,
            flags=None,
            traps=None,
        )

        self.flags = Flags(self._python_context)
        self.flags.disable_exceptions()
        self.flags.clear_all()

        self._special_values: list[Decimal] = []

        self.nan = Decimal(self._python_context.create_decimal("nan"))
        self.snan = Decimal(self._python_context.create_decimal("snan"))
        self.infinity = Decimal(self._python_context.create_decimal("inf"))
        # Strings because of weird parsing issues
        self.greatest_finite_magnitude = f"{max_decimal_digits}E{max_signed_exponent}"
        self.least_nonzero_magnitude = f"1E{min_signed_exponent}"

        for s in (
            "nan",
            "snan",
            "inf",
            "0E0",
            f"0E{min_signed_exponent}",
            f"0E{max_signed_exponent}",
            f"1E{min_signed_exponent}",
            f"1E{max_signed_exponent}",
            f"{max_decimal_digits}E{min_signed_exponent}",
            f"{max_decimal_digits}E{max_signed_exponent}",
        ):
            d = self._python_context.create_decimal(s)
            self._special_values.append(Decimal(d.copy_abs()))
            self._special_values.append(Decimal(d.copy_negate()))
            self.flags.assert_empty(s, excluding=FLAG_SUBNORMAL)

    def generate(self, count: int, *, seed: int) -> list[Decimal]:
        # Copy all special values
        result = list(self._special_values)

        # Div by 2: both signs.
        all_count = count - len(result)
        subnormal_count = all_count // 30
        normal_count = (all_count - subnormal_count) // 2

        random.seed(seed)
        self.flags.clear_all()

        for _ in range(normal_count):
            significand = random.randint(0, self.max_decimal_digits)
            exponent = random.randint(
                self.min_signed_exponent, self.max_signed_exponent
            )

            d = self._python_context.scaleb(significand, exponent)
            result.append(Decimal(d.copy_abs()))
            result.append(Decimal(d.copy_negate()))

            # It may happen that this value is subnormal.
            self.flags.assert_empty(
                f"{significand}E{exponent}", excluding=FLAG_SUBNORMAL
            )

        subnormals = self.generate_subnormals(subnormal_count, seed=seed)
        result.extend(subnormals)

        return result

    def generate_subnormals(self, count: int, *, seed: int) -> list[Decimal]:
        result: list[Decimal] = []
        # Div by 2: both signs.
        all_count = count // 2

        # We need to be between:
        # - 1E(min_signed_exponent + precision - 1) = 1E(-398+16-1) = 1E−383
        # - 1E(min_signed_exponent)                 = 1E-398
        e_min = self.min_signed_exponent + self.precision - 1  # _python_context.Emin
        random.seed(seed)

        for _ in range(all_count):
            digit_count = random.randint(1, self.precision - 1)
            significand = random.randint(0, pow(10, digit_count) - 1)

            max_exponent = e_min - digit_count
            exponent = random.randint(self.min_signed_exponent, max_exponent)

            d = self._python_context.scaleb(significand, exponent)
            result.append(Decimal(d.copy_abs()))
            result.append(Decimal(d.copy_negate()))

            message = f"{significand}E{exponent}"
            self.flags.assert_is_set(FLAG_SUBNORMAL, message)
            self.flags.assert_empty(message, excluding=FLAG_SUBNORMAL)

        return result


DECIMAL_64 = Context(
    "d64",
    "Decimal64",
    bit_width=64,
    precision=16,
    trailing_significand_width=50,
    max_decimal_digits=9_999_999_999_999_999,
    min_signed_exponent=-398,
    max_signed_exponent=369,
)

DECIMAL_128 = Context(
    "d128",
    "Decimal128",
    bit_width=128,
    precision=34,
    trailing_significand_width=110,
    max_decimal_digits=9_999_999_999_999_999_999_999_999_999_999_999,
    min_signed_exponent=-6176,
    max_signed_exponent=6111,
)

DECIMALS = (DECIMAL_64, DECIMAL_128)


def write_line(
    f: io.TextIOWrapper,
    context: Context,
    operation: str,
    rounding: Rounding,
    arguments: list[Decimal | int | float],
    expected: str | bool | Decimal,
):
    f.write(context.file_header)
    f.write(operation)
    f.write(" ")
    f.write(rounding.encoded)

    for d in arguments:
        f.write(" ")
        f.write(str(d))

    f.write(" -> ")

    if isinstance(expected, bool):
        f.write("1" if expected else "0")
    else:
        f.write(str(expected))

    flags = ""

    if context.flags.is_set(FLAG_INEXACT):
        flags += "x"
    if context.flags.is_set(FLAG_UNDERFLOW):
        flags += "u"
    if context.flags.is_set(FLAG_OVERFLOW):
        flags += "o"
    if context.flags.is_set(FLAG_DIVISION_BY_ZERO):
        flags += "z"
    if context.flags.is_set(FLAG_INVALID_OPERATION):
        flags += "i"

    if flags:
        f.write(" ")
        f.write(flags)

    f.write("\n")


def round_infinitely_big_value(
    ctx: Context,
    d: Decimal,
    rounding: Rounding,
) -> Decimal | str:
    # We sometimes return string because:
    # negative(9999999999999999999999999999999999E6111) -> -1000000000000000000000000000E6118
    is_negative = ctx._python_context.is_signed(d.value)
    minus_inf = Decimal(-ctx.infinity.value)

    ctx.flags.set(FLAG_INEXACT)
    ctx.flags.set(FLAG_OVERFLOW)

    if rounding == ROUNDING_UP:
        if is_negative:
            return "-" + ctx.greatest_finite_magnitude

        return ctx.infinity

    if rounding == ROUNDING_DOWN:
        if is_negative:
            return minus_inf

        return ctx.greatest_finite_magnitude

    if rounding == ROUNDING_TO_ZERO:
        if is_negative:
            return "-" + ctx.greatest_finite_magnitude

        return ctx.greatest_finite_magnitude

    if is_negative:
        return minus_inf

    return ctx.infinity


def round_infinitely_small_value(
    ctx: Context,
    d: Decimal,
    rounding: Rounding,
    preferred_exponent_for_zero: int,
) -> Decimal | str:
    # We return 'str' because for '0' Python always sets the exponent to '0'.
    is_negative = ctx._python_context.is_signed(d.value)
    zero = f"0E{preferred_exponent_for_zero}"
    minus_zero = "-" + zero

    ctx.flags.set(FLAG_INEXACT)
    ctx.flags.set(FLAG_UNDERFLOW)

    if rounding == ROUNDING_UP:
        if is_negative:
            return minus_zero

        return ctx.least_nonzero_magnitude

    if rounding == ROUNDING_DOWN:
        if is_negative:
            return "-" + ctx.least_nonzero_magnitude

        return zero

    if is_negative:
        return minus_zero

    return zero


def random_ints(count: int, *, min: int, max: int, seed: int) -> list[int]:
    # Div by 2: both signs.
    count = count // 2
    random.seed(seed)
    result: list[int] = []

    for _ in range(count):
        i = random.randint(min, max)
        result.append(+i)
        result.append(-i)

    return result


def random_floats(count, *, seed: int) -> list[float]:
    result: list[float] = []

    for s in ("nan", "inf", "0"):
        d = float(s)
        result.append(+d)
        result.append(-d)

    # Div by 2: both signs.
    rest_count = count - len(result)
    rest_count = rest_count // 2
    random.seed(seed)

    for _ in range(rest_count):
        d = random.random()
        result.append(+d)
        result.append(-d)

    return result
