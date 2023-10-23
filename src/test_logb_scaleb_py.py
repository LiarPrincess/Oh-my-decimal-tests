import os
from common import (
    DECIMALS,
    ROUNDINGS,
    ROUNDING_TO_ZERO,
    FLAG_INVALID_OPERATION,
    FLAG_DIVISION_BY_ZERO,
    Context,
    Decimal,
    write_line,
    random_ints,
    round_infinitely_big_value,
    round_infinitely_small_value,
)

SEED = 1981519856
LOGB_DECIMAL_COUNT = 50_000

SCALEB_DECIMAL_COUNT = 2_000
SCALEB_EXPONENT_COUNT = 50
SCALEB_EXPONENT_ABOVE_MAX_COUNT = 5
SCALEB_EXPONENT_BELOW_MIN_COUNT = 5

INT32_MAX = 2147483647
INT32_MIN = -2147483648
INT64_MAX = 9223372036854775807
INT64_MIN = -9223372036854775808


def write(dir: str):
    for ctx in DECIMALS:
        _write_logb(dir, ctx)
        _write_scaleb(dir, ctx)


def _write_logb(dir: str, ctx: Context):
    operation = "logb"
    decimals = ctx.generate(LOGB_DECIMAL_COUNT, seed=SEED)

    file_name = f"{operation}_{ctx.file_header}.txt"
    path = os.path.join(dir, file_name)
    print(file_name)

    # Rounding does not matter
    rounding = ROUNDING_TO_ZERO
    ctx_python = ctx._python_context
    ctx_python.rounding = rounding.python

    with open(path, "w") as f:
        for d in decimals:
            ctx.flags.clear_all()

            # In Python 'logb' is floating point -> raise 'div0' for 0.
            # In Swift 'logb' is an 'Int' -> raise IO for NaN, Inf and 0.
            result_decimal = ctx_python.logb(d.value)
            result_int = ""

            if ctx_python.is_infinite(d.value):
                result_int = "max"
                ctx.flags.set(FLAG_INVALID_OPERATION)
            elif ctx_python.is_nan(d.value):
                result_int = "max"
                ctx.flags.set(FLAG_INVALID_OPERATION)
            elif ctx_python.is_zero(d.value):
                result_int = "min"
                ctx.flags.set(FLAG_INVALID_OPERATION)
                # When exponent is 'Int' this exception should not be raised.
                ctx.flags.clear(FLAG_DIVISION_BY_ZERO)
            else:
                r = Decimal(result_decimal)
                t = r.as_tuple()
                assert t is not None
                assert t.exponent == 0
                result_int = str(-t.significand if t.is_negative else t.significand)

            ctx.flags.assert_empty(excluding=FLAG_INVALID_OPERATION)

            write_line(
                f,
                context=ctx,
                operation=operation,
                rounding=rounding,
                arguments=[d],
                expected=result_int,
            )


def _write_scaleb(dir: str, ctx: Context):
    operation = "scaleb"
    decimals = ctx.generate(SCALEB_DECIMAL_COUNT, seed=SEED)
    ctx_python = ctx._python_context

    exponents: list[int] = [
        ctx_python.Emin,
        ctx_python.Etiny(),
        ctx_python.Emax,
        ctx_python.Etop(),
        INT32_MAX,
        INT32_MIN,
        INT64_MAX,
        INT64_MIN,
    ]

    exponents.extend(
        random_ints(
            SCALEB_EXPONENT_COUNT - len(exponents),
            min=ctx_python.Emin,
            max=ctx_python.Emax,
            seed=SEED,
        )
    )

    exponents.extend(
        random_ints(
            SCALEB_EXPONENT_BELOW_MIN_COUNT,
            min=INT32_MIN,
            max=ctx_python.Emin,
            seed=SEED,
        )
    )

    exponents.extend(
        random_ints(
            SCALEB_EXPONENT_ABOVE_MAX_COUNT,
            min=ctx_python.Emax,
            max=INT32_MAX,
            seed=SEED,
        )
    )

    for rounding in ROUNDINGS:
        file_name = f"{operation}_{ctx.file_header}_{rounding.swift_name}.txt"
        path = os.path.join(dir, file_name)
        print(file_name)

        # The most important line:
        ctx_python.rounding = rounding.python

        with open(path, "w") as f:
            for d in decimals:
                for e in exponents:
                    ctx.flags.clear_all()

                    result: Decimal | str

                    if ctx_python.is_snan(d.value):
                        # Swift is 'ok' with sNaN
                        result = d
                    elif ctx_python.is_infinite(d.value):
                        # Python returns NaN
                        result = d
                    elif ctx_python.is_zero(d.value):
                        # Python returns NaN
                        t = d.as_tuple()
                        assert t is not None
                        new_exponent = t.exponent + e

                        # Clamp between min/max.
                        t.exponent = min(
                            ctx.max_signed_exponent,
                            max(ctx.min_signed_exponent, new_exponent),
                        )

                        result = Decimal.from_tuple(ctx, t)
                    else:
                        # Python returns NaN with IO for underflow/overflow.
                        r = ctx_python.scaleb(d.value, e)
                        # No 'ctx.flags.assert_empty', because a lot of them may fire.

                        if ctx.flags.is_set(FLAG_INVALID_OPERATION):
                            ctx.flags.clear(FLAG_INVALID_OPERATION)

                            t = d.as_tuple()
                            assert t is not None
                            new_exponent = t.exponent + e

                            if new_exponent > 0:
                                result = round_infinitely_big_value(ctx, d, rounding)
                            else:
                                result = round_infinitely_small_value(
                                    ctx,
                                    d,
                                    rounding,
                                    preferred_exponent_for_zero=ctx.min_signed_exponent,
                                )

                        else:
                            result = Decimal(r)

                    write_line(
                        f,
                        context=ctx,
                        operation=operation,
                        rounding=rounding,
                        arguments=[d, e],
                        expected=result,
                    )
