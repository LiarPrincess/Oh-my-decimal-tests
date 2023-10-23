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

SEED = 1238488
DECIMAL_COUNT = 20_000
SUBNORMAL_DECIMAL_COUNT = 5_000


def write(dir: str):
    for ctx in DECIMALS:
        ds = ctx.generate(DECIMAL_COUNT, seed=SEED)

        # Subnormal = normal + a few more
        ds_subnormal = list(ds)
        ds_subnormal.extend(ctx.generate_subnormals(SUBNORMAL_DECIMAL_COUNT, seed=SEED))

        _write_file(dir, ctx, ds, "is_zero", lambda ctx, d: ctx.is_zero(d))
        _write_file(dir, ctx, ds, "is_finite", lambda ctx, d: ctx.is_finite(d))
        _write_file(dir, ctx, ds, "is_infinite", lambda ctx, d: ctx.is_infinite(d))
        _write_file(dir, ctx, ds, "is_nan", lambda ctx, d: ctx.is_nan(d))
        _write_file(dir, ctx, ds, "is_qnan", lambda ctx, d: ctx.is_qnan(d))
        _write_file(dir, ctx, ds, "is_snan", lambda ctx, d: ctx.is_snan(d))
        _write_file(dir, ctx, ds, "is_normal", lambda ctx, d: ctx.is_normal(d))
        _write_file(dir, ctx, ds, "is_negative", lambda ctx, d: ctx.is_signed(d))

        _write_file(
            dir, ctx, ds_subnormal, "is_subnormal", lambda ctx, d: ctx.is_subnormal(d)
        )

        # This test is not the best because in Python all decimals are canonical:
        #   canonical()
        #   Return the canonical encoding of the argument. Currently, the encoding
        #   of a Decimal instance is always canonical, so this operation returns
        #   its argument unchanged.
        #   https://docs.python.org/3/library/decimal.html#decimal.Decimal.canonical
        _write_file(dir, ctx, ds, "is_canonical", lambda ctx, d: ctx.is_canonical(d))


def _write_file(
    dir: str,
    ctx: Context,
    decimals: list[Decimal],
    operation: str,
    apply: Callable[[decimal.Context, decimal.Decimal], bool],
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
                expected=result,
            )
