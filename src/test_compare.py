import os
import decimal
from typing import Callable
from common import (
    DECIMALS,
    ROUNDING_TO_ZERO,
    FLAG_SUBNORMAL,
    FLAG_INVALID_OPERATION,
    Decimal,
    Context,
    FlagType,
    write_line,
)

# We will do cartesian product on them.
DECIMAL_COUNT = 300

# Compare is important, so it will have multiple files.
# This will also make tests more 'parallel'.
# Other operations have only 1 file.
SEEDS: tuple[int, ...] = (
    1191299818,
    68198198,
    849465118,
    16819818,
)


def write(dir: str):
    for ctx in DECIMALS:
        # Compare has multiple files
        for index, seed in enumerate(SEEDS):
            _write_compare_file(dir, ctx, index, seed)

        # Everything else has 1 file.
        ds = ctx.generate(DECIMAL_COUNT, seed=SEEDS[0])

        _write_min_max_file(dir, ctx, ds, "min", lambda c, l, r: c.min(l, r))
        _write_min_max_file(dir, ctx, ds, "min_mag", lambda c, l, r: c.min_mag(l, r))
        _write_min_max_file(dir, ctx, ds, "max", lambda c, l, r: c.max(l, r))
        _write_min_max_file(dir, ctx, ds, "max_mag", lambda c, l, r: c.max_mag(l, r))

        _write_compare_total(
            dir, ctx, ds, "compare_total", lambda c, l, r: c.compare_total(l, r)
        )
        _write_compare_total(
            dir, ctx, ds, "compare_total_mag", lambda c, l, r: c.compare_total_mag(l, r)
        )


def _write_compare_file(
    dir: str,
    ctx: Context,
    file_index: int,
    seed: int,
):
    operation = "compare"
    decimals = ctx.generate(DECIMAL_COUNT, seed=seed)

    file_name = f"{operation}_{ctx.file_header}_{file_index}.txt"
    path = os.path.join(dir, file_name)
    print(file_name)

    # Rounding does not matter
    rounding = ROUNDING_TO_ZERO
    ctx_python = ctx._python_context
    ctx_python.rounding = rounding.python

    with open(path, "w") as f:
        for lhs in decimals:
            for rhs in decimals:
                ctx.flags.clear_all()
                result_decimal = ctx_python.compare(lhs.value, rhs.value)

                excluded_flags: list[FlagType] = []

                if ctx_python.is_snan(lhs.value) or ctx_python.is_snan(rhs.value):
                    excluded_flags.append(FLAG_INVALID_OPERATION)

                ctx.flags.assert_empty(excluding=excluded_flags)

                result: str

                if ctx_python.is_nan(result_decimal):
                    result = "nan"
                elif ctx_python.is_zero(result_decimal):
                    result = "eq"
                elif ctx_python.is_signed(result_decimal):
                    result = "lt"
                else:
                    result = "gt"

                write_line(
                    f,
                    context=ctx,
                    operation=operation,
                    rounding=rounding,
                    arguments=[lhs, rhs],
                    expected=result,
                )


def _write_min_max_file(
    dir: str,
    ctx: Context,
    decimals: list[Decimal],
    operation: str,
    apply: Callable[
        [decimal.Context, decimal.Decimal, decimal.Decimal], decimal.Decimal
    ],
):
    file_name = f"{operation}_{ctx.file_header}.txt"
    path = os.path.join(dir, file_name)
    print(file_name)

    # Rounding does not matter
    rounding = ROUNDING_TO_ZERO
    ctx_python = ctx._python_context
    ctx_python.rounding = rounding.python

    with open(path, "w") as f:
        for lhs in decimals:
            for rhs in decimals:
                ctx.flags.clear_all()
                result = apply(ctx_python, lhs.value, rhs.value)

                # min(qNaN, -sNaN) -> qNaN, Python returns -qNaN
                if ctx_python.is_qnan(lhs.value) and ctx_python.is_snan(rhs.value):
                    result = ctx_python.copy_sign(result, lhs.value)

                # min(0E5, 0E2) -> 0E5, Python returns 0E2 (lower exponent)
                if ctx_python.is_zero(lhs.value) and ctx_python.is_zero(rhs.value):
                    result = lhs.value

                excluded_flags: list[FlagType] = []

                if ctx_python.is_snan(lhs.value) or ctx_python.is_snan(rhs.value):
                    excluded_flags.append(FLAG_INVALID_OPERATION)

                if ctx_python.is_subnormal(result):
                    excluded_flags.append(FLAG_SUBNORMAL)

                ctx.flags.assert_empty(excluding=excluded_flags)

                write_line(
                    f,
                    context=ctx,
                    operation=operation,
                    rounding=rounding,
                    arguments=[lhs, rhs],
                    expected=Decimal(result),
                )


def _write_compare_total(
    dir: str,
    ctx: Context,
    decimals: list[Decimal],
    operation: str,
    apply: Callable[
        [decimal.Context, decimal.Decimal, decimal.Decimal], decimal.Decimal
    ],
):
    file_name = f"{operation}_{ctx.file_header}.txt"
    path = os.path.join(dir, file_name)
    print(file_name)

    # Rounding does not matter
    rounding = ROUNDING_TO_ZERO
    ctx_python = ctx._python_context
    ctx_python.rounding = rounding.python

    with open(path, "w") as f:
        for lhs in decimals:
            for rhs in decimals:
                ctx.flags.clear_all()
                result_decimal = apply(ctx_python, lhs.value, rhs.value)
                ctx.flags.assert_empty()

                result: str

                if ctx_python.is_zero(result_decimal):
                    result = "eq"
                elif ctx_python.is_signed(result_decimal):
                    result = "lt"
                else:
                    result = "gt"

                write_line(
                    f,
                    context=ctx,
                    operation=operation,
                    rounding=rounding,
                    arguments=[lhs, rhs],
                    expected=result,
                )
