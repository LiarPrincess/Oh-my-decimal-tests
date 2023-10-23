import os
from common import (
    DECIMALS,
    ROUNDING_TO_ZERO,
    Context,
    Decimal,
    write_line,
)

SEED = 5191561918
# We will do cartesian product on them.
COPY_SIGN_COUNT = 150


def write(dir: str):
    for ctx in DECIMALS:
        _write_copy_sign(dir, ctx)


def _write_copy_sign(dir: str, ctx: Context):
    operation = "copy_sign"
    file_name = f"{operation}_{ctx.file_header}.txt"
    path = os.path.join(dir, file_name)
    print(file_name)

    # Rounding does not matter
    rounding = ROUNDING_TO_ZERO
    ctx_python = ctx._python_context
    ctx_python.rounding = rounding.python

    decimals = ctx.generate(COPY_SIGN_COUNT, seed=SEED)

    with open(path, "w") as f:
        for lhs in decimals:
            for rhs in decimals:
                ctx.flags.clear_all()
                result = ctx_python.copy_sign(lhs.value, rhs.value)
                ctx.flags.assert_empty()

                write_line(
                    f,
                    context=ctx,
                    operation=operation,
                    rounding=rounding,
                    arguments=[lhs, rhs],
                    expected=Decimal(result),
                )
