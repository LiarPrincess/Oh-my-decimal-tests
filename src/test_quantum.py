import os
from common import (
    DECIMALS,
    ROUNDINGS,
    ROUNDING_TO_ZERO,
    FLAG_INEXACT,
    FLAG_SUBNORMAL,
    FLAG_INVALID_OPERATION,
    Context,
    Decimal,
    FlagType,
    write_line,
)

DECIMAL_COUNT = 300  # + common_precisions, and then cartesian product for all roundings

# Quantize is important, so it will have multiple files.
# This will also make tests more 'parallel'.
SEEDS: tuple[int, ...] = (
    563456784524,
    5464567824524,
    8945618998262,
    9841566511651,
)


def write(dir: str):
    for ctx in DECIMALS:
        common_precisions: list[Decimal] = []

        # 1000000000000000
        # 100000000000000
        # 10000000000000
        # …
        # 1
        for digit_count in range(ctx.precision, 0, -1):
            zero_count = digit_count - 1
            zeros = "0" * zero_count

            ctx.flags.clear_all()
            s = "1" + zeros
            d = ctx._python_context.create_decimal(s)
            ctx.flags.assert_empty()

            common_precisions.append(Decimal(d.copy_abs()))
            common_precisions.append(Decimal(d.copy_negate()))

        # 0.1
        # 0.01
        # 0.001
        # 0.0001
        # 0.00001
        for zero_count in range(ctx.precision - 1):
            zeros = "0" * zero_count

            for trailing__digit in ("1", "0"):
                ctx.flags.clear_all()
                s = "0." + zeros + trailing__digit
                d = ctx._python_context.create_decimal(s)
                ctx.flags.assert_empty()

                common_precisions.append(Decimal(d.copy_abs()))
                common_precisions.append(Decimal(d.copy_negate()))

        for file_index, seed in enumerate(SEEDS):
            decimals = ctx.generate(DECIMAL_COUNT, seed=seed)

            # Insert common just after special values
            special_end_index = -1

            for index, d in enumerate(decimals):
                is_special = (
                    ctx._python_context.is_nan(d.value)
                    or ctx._python_context.is_infinite(d.value)
                    or ctx._python_context.is_zero(d.value)
                )

                if not is_special:
                    special_end_index = index
                    break

            special = decimals[:special_end_index]
            after_special = decimals[special_end_index:]
            decimals = special + common_precisions + after_special

            _write_quantize(dir, ctx, file_index, decimals)
            _write_same_quantum(dir, ctx, file_index, decimals)


def _write_quantize(
    dir: str,
    ctx: Context,
    file_index: int,
    decimals: list[Decimal],
):
    operation = "quantize"
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
                for precision in decimals:
                    ctx.flags.clear_all()

                    result = ctx_python.quantize(d.value, precision.value)

                    if ctx_python.is_nan(d.value):
                        # If we have 'qNaN' and 'sNaN' in the same operation
                        # then Python returns 'sNaN' sign, even if 'sNaN' is
                        # the 'precision' argument.
                        result = ctx_python.copy_sign(result, d.value)

                    excluded_flags: list[FlagType] = [
                        FLAG_INEXACT,
                        FLAG_INVALID_OPERATION,
                    ]

                    if ctx_python.is_subnormal(result):
                        excluded_flags.append(FLAG_SUBNORMAL)

                    ctx.flags.assert_empty(excluding=excluded_flags)

                    write_line(
                        f,
                        context=ctx,
                        operation=operation,
                        rounding=rounding,
                        arguments=[d, precision],
                        expected=Decimal(result),
                    )


def _write_same_quantum(
    dir: str,
    ctx: Context,
    file_index: int,
    decimals: list[Decimal],
):
    operation = "same_quantum"

    file_name = f"{operation}_{ctx.file_header}_{file_index}.txt"
    path = os.path.join(dir, file_name)
    print(file_name)

    # Rounding does not matter
    rounding = ROUNDING_TO_ZERO
    ctx_python = ctx._python_context
    ctx_python.rounding = rounding.python

    with open(path, "w") as f:
        for d in decimals:
            for precision in decimals:
                pass
                ctx.flags.clear_all()
                result = ctx_python.same_quantum(d.value, precision.value)
                ctx.flags.assert_empty()

                write_line(
                    f,
                    context=ctx,
                    operation=operation,
                    rounding=rounding,
                    arguments=[d, precision],
                    expected=result,
                )
