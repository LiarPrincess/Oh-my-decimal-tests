import os
from common import (
    DECIMALS,
    ROUNDINGS,
    ROUNDING_TO_ZERO,
    FLAG_INEXACT,
    FLAG_INVALID_OPERATION,
    Context,
    Decimal,
    FlagType,
    write_line,
)

DECIMAL_COUNT = 80_000

# Round is important, so it will have multiple files.
# This will also make tests more 'parallel'.
SEEDS: tuple[int, ...] = (
    1191299818,
    68198198,
)


def write(dir: str):
    for ctx in DECIMALS:
        for index, seed in enumerate(SEEDS):
            decimals = ctx.generate(DECIMAL_COUNT, seed=seed)
            _write_round_file(dir, ctx, index, decimals)
            _write_round_exact_file(dir, ctx, index, decimals)


def _write_round_file(
    dir: str,
    ctx: Context,
    file_index: int,
    decimals: list[Decimal],
):
    operation = "round"
    ctx_python = ctx._python_context

    for rounding in ROUNDINGS:
        file_name = (
            f"{operation}_{ctx.file_header}_{rounding.swift_name}_{file_index}.txt"
        )
        path = os.path.join(dir, file_name)
        print(file_name)

        # The most important line:
        ctx_python.rounding = rounding.python

        with open(path, "w") as f:
            for d in decimals:
                ctx.flags.clear_all()
                result = ctx_python.to_integral_exact(d.value)

                excluded_flags: list[FlagType] = [FLAG_INEXACT]

                if ctx_python.is_snan(d.value):
                    excluded_flags.append(FLAG_INVALID_OPERATION)

                ctx.flags.assert_empty(excluding=excluded_flags)

                write_line(
                    f,
                    context=ctx,
                    operation=operation,
                    rounding=rounding,
                    arguments=[d],
                    expected=Decimal(result),
                )


def _write_round_exact_file(
    dir: str,
    ctx: Context,
    file_index: int,
    decimals: list[Decimal],
):
    operation = "round_exact"

    file_name = f"{operation}_{ctx.file_header}_{file_index}.txt"
    path = os.path.join(dir, file_name)
    print(file_name)

    # Rounding does not matter
    rounding = ROUNDING_TO_ZERO
    ctx_python = ctx._python_context
    ctx_python.rounding = rounding.python

    with open(path, "w") as f:
        for d in decimals:
            ctx.flags.clear_all()
            result = ctx_python.to_integral_exact(d.value)

            excluded_flags: list[FlagType] = [FLAG_INEXACT]

            if ctx_python.is_snan(d.value):
                excluded_flags.append(FLAG_INVALID_OPERATION)

            ctx.flags.assert_empty(excluding=excluded_flags)

            compare = ctx_python.compare(d.value, result)
            is_exact = ctx_python.is_zero(compare)

            if not ctx.flags.is_set(FLAG_INEXACT):
                write_line(
                    f,
                    context=ctx,
                    operation=operation,
                    rounding=rounding,
                    arguments=[d],
                    expected=Decimal(result),
                )
