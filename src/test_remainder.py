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

SEED = 6816518918

# big % small -> some num
# We will do cartesian product on them.
# Though a LOT of the inputs will be removed, because of the different semantic.
# (See comment inside the function.)
DECIMAL_BIG_REM_SMALL_COUNT = 1500

# small % big -> small
# This is a simpler case, so we do not need that many tests.
DECIMAL_SMALL_REM_BIG_COUNT = 200


def write(dir: str):
    for ctx in DECIMALS:
        decimals = ctx.generate(DECIMAL_BIG_REM_SMALL_COUNT, seed=SEED)

        _write_file(
            dir,
            ctx,
            decimals,
            operation="rem_near",
            file_name="rem_near_big_small",
            sort_operands=_big_rem_small,
            apply=_remainder_near,
        )

        _write_file(
            dir,
            ctx,
            decimals,
            operation="rem_trunc",
            file_name="rem_trunc_big_small",
            sort_operands=_big_rem_small,
            apply=_remainder_trunc,
        )

        decimals = ctx.generate(DECIMAL_SMALL_REM_BIG_COUNT, seed=SEED)

        _write_file(
            dir,
            ctx,
            decimals,
            operation="rem_near",
            file_name="rem_near_small_big",
            sort_operands=_small_rem_big,
            apply=_remainder_near,
        )

        _write_file(
            dir,
            ctx,
            decimals,
            operation="rem_trunc",
            file_name="rem_trunc_small_big",
            sort_operands=_small_rem_big,
            apply=_remainder_trunc,
        )


def _remainder_near(
    ctx: decimal.Context, lhs: decimal.Decimal, rhs: decimal.Decimal
) -> decimal.Decimal:
    return ctx.remainder_near(lhs, rhs)


def _remainder_trunc(
    ctx: decimal.Context, lhs: decimal.Decimal, rhs: decimal.Decimal
) -> decimal.Decimal:
    return ctx.remainder(lhs, rhs)


def _big_rem_small(big: Decimal, small: Decimal) -> tuple[Decimal, Decimal]:
    return (big, small)


def _small_rem_big(big: Decimal, small: Decimal) -> tuple[Decimal, Decimal]:
    return (small, big)


def _write_file(
    dir: str,
    ctx: Context,
    decimals: list[Decimal],
    operation: str,
    file_name: str,
    sort_operands: Callable[[Decimal, Decimal], tuple[Decimal, Decimal]],
    apply: Callable[
        [decimal.Context, decimal.Decimal, decimal.Decimal], decimal.Decimal
    ],
):
    file_name = f"{file_name}_{ctx.file_header}.txt"
    path = os.path.join(dir, file_name)
    print(file_name)

    # Rounding does not matter
    rounding = ROUNDING_TO_ZERO
    ctx_python = ctx._python_context
    ctx_python.rounding = rounding.python

    with open(path, "w") as f:
        for big, small in _generate_pairs(ctx, decimals):
            ctx.flags.clear_all()
            lhs, rhs = sort_operands(big, small)
            result = apply(ctx_python, lhs.value, rhs.value)

            # https://speleotrove.com/decimal/daops.html#refremain
            # https://speleotrove.com/decimal/daops.html#refremnear
            # This operation will fail under the same conditions as integer division
            # (that is, if integer division on the same two operands would fail, the
            # remainder cannot be calculated), except when the quotient is very close
            # to 10 raised to the power of the precision.[10]
            #
            # In plain words:
            # Swift: the remainder is always returned even if the result of the integer
            #        division (quotient) is not representable in a given format.
            # Speleotrove: if the result of the division (quotient) is not representable
            #        in a given format (overflow) then 'nan' is returned  with
            #        'invalidOperation' flag raised.
            is_lhs_finite = ctx_python.is_finite(lhs.value)
            is_rhs_finite = ctx_python.is_finite(rhs.value)

            if is_lhs_finite and is_rhs_finite and ctx_python.is_nan(result):
                continue

            if ctx_python.is_nan(lhs.value):
                # If we have 'qNaN' and 'sNaN' in the same operation
                # then Python returns 'sNaN' sign, even if 'sNaN' is
                # the 'precision' argument.
                result = ctx_python.copy_sign(result, lhs.value)

            excluded_flags: list[FlagType] = []

            if not is_lhs_finite or not is_rhs_finite:
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


def _generate_pairs(ctx: Context, decimals: list[Decimal]):
    ctx_python = ctx._python_context

    for lhs in decimals:
        lhs_mag = ctx_python.copy_abs(lhs.value)
        is_lhs_finite = ctx_python.is_finite(lhs.value)

        for rhs in decimals:
            rhs_mag = ctx_python.copy_abs(rhs.value)
            is_rhs_finite = ctx_python.is_finite(rhs.value)

            if is_lhs_finite and is_rhs_finite:
                cmp = ctx_python.compare(lhs_mag, rhs_mag)
                is_lhs_less = ctx_python.is_signed(cmp)
                pair = (rhs, lhs) if is_lhs_less else (lhs, rhs)
            else:
                pair = (lhs, rhs)

            yield pair
