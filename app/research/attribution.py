import numpy as np
import pandas as pd


def linked_contribution(simulation):
    result = simulation["contributions"].sum().sort_values(ascending=False)
    expected = simulation["path"].wealth.iloc[-1] - 1
    if not np.isclose(result.sum(), expected, atol=1e-10):
        raise ValueError("Attribution does not reconcile to wealth")
    return result


def brinson(wp, wb, rp, rb):
    """Single-period Brinson–Fachler; caller supplies aligned category returns."""
    frame = pd.DataFrame({"wp": wp, "wb": wb, "rp": rp, "rb": rb})
    if (
        frame.isna().any().any()
        or not np.isfinite(frame).all().all()
        or not np.isclose(frame.wp.sum(), 1)
        or not np.isclose(frame.wb.sum(), 1)
        or (frame[["wp", "wb"]] < 0).any().any()
    ):
        raise ValueError("Complete aligned long-only category weights summing to one required")
    benchmark = float((frame.wb * frame.rb).sum())
    allocation = (frame.wp - frame.wb) * (frame.rb - benchmark)
    selection = frame.wb * (frame.rp - frame.rb)
    interaction = (frame.wp - frame.wb) * (frame.rp - frame.rb)
    return pd.DataFrame(
        {
            "allocation": allocation,
            "selection": selection,
            "interaction": interaction,
            "active_contribution": allocation + selection + interaction,
        }
    )
