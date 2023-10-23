import os
import decimal
from typing import Callable
from common import (
    DECIMALS,
    ROUNDING_TO_ZERO,
    FLAG_SUBNORMAL,
    Context,
    Decimal,
    write_line,
)

SEED = 1984816
DECIMAL_COUNT = 20_000


def write(dir: str):
    for ctx in DECIMALS:
        ds = ctx.generate(DECIMAL_COUNT, seed=SEED)
        _write_file(dir, ctx, ds, "plus", lambda ctx, d: ctx.copy_decimal(d))
        _write_file(dir, ctx, ds, "minus", lambda ctx, d: ctx.copy_negate(d))
        _write_file(dir, ctx, ds, "abs", lambda ctx, d: ctx.copy_abs(d))


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
            ctx.flags.assert_empty(excluding=FLAG_SUBNORMAL)

            write_line(
                f,
                context=ctx,
                operation=operation,
                rounding=rounding,
                arguments=[d],
                expected=Decimal(result),
            )
