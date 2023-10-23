import os
import decimal
from typing import Callable
from common import (
    DECIMALS,
    ROUNDING_TO_ZERO,
    FLAG_SUBNORMAL,
    FLAG_INVALID_OPERATION,
    Context,
    Decimal,
    FlagType,
    write_line,
)

SEED = 8861684681
DECIMAL_COUNT = 50_000


def write(dir: str):
    for ctx in DECIMALS:
        ds = ctx.generate(DECIMAL_COUNT, seed=SEED)
        _write_file(dir, ctx, ds, "next_up", lambda ctx, d: ctx.next_plus(d))
        _write_file(dir, ctx, ds, "next_down", lambda ctx, d: ctx.next_minus(d))


def _write_file(
    dir: str,
    ctx: Context,
    decimals: list[Decimal],
    operation: str,
    apply: Callable[[decimal.Context, decimal.Decimal], decimal.Decimal],
):
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
            result = apply(ctx_python, d.value)

            excluded_flags: list[FlagType] = []

            if ctx_python.is_snan(d.value):
                excluded_flags.append(FLAG_INVALID_OPERATION)

            if ctx_python.is_subnormal(result):
                excluded_flags.append(FLAG_SUBNORMAL)

            ctx.flags.assert_empty(excluding=excluded_flags)

            write_line(
                f,
                context=ctx,
                operation=operation,
                rounding=rounding,
                arguments=[d],
                expected=Decimal(result),
            )
