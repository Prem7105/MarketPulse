from app.research.returns import equity


def drawdown(returns):
    wealth = equity(returns)
    return wealth / wealth.cummax().clip(lower=1) - 1


def episodes(returns):
    """Peak date None means the initial pre-observation wealth of one."""
    dd = drawdown(returns)
    result, peak, start, trough, depth, length = [], None, None, None, 0.0, 0
    for date, value in dd.items():
        if value < -1e-12:
            if start is None:
                start, trough, depth, length = date, date, value, 0
            length += 1
            if value < depth:
                trough, depth = date, value
        else:
            if start is not None:
                result.append(
                    {
                        "peak": peak,
                        "start": start,
                        "trough": trough,
                        "recovery": date,
                        "maximum_loss": float(depth),
                        "duration": length,
                        "recovered": True,
                    }
                )
                start = None
            peak = date
    if start is not None:
        result.append(
            {
                "peak": peak,
                "start": start,
                "trough": trough,
                "recovery": None,
                "maximum_loss": float(depth),
                "duration": length,
                "recovered": False,
            }
        )
    return sorted(result, key=lambda x: x["maximum_loss"])
