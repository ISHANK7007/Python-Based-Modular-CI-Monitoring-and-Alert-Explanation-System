import operator

class StreamFilterEngine:
    """
    Applies dynamic filters to a stream of segment objects.
    Supports expressions like:
        - label=BUILD_FAILURE
        - confidence>0.6
    """

    OPERATORS = {
        "=": operator.eq,
        "==": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
    }

    def __init__(self, filter_expr=""):
        self.filter_expr = filter_expr.strip()

    def apply(self, segments):
        if not self.filter_expr:
            return segments
        try:
            key, op_str, value = self._parse_expression(self.filter_expr)
            op_func = self.OPERATORS.get(op_str)
            if not op_func:
                raise ValueError(f"Unsupported operator: {op_str}")
            return [s for s in segments if self._match(s, key, op_func, value)]
        except Exception as e:
            print(f"[Filter Error] {e}")
            return segments  # fallback to no filtering

    def _parse_expression(self, expr):
        for op in sorted(self.OPERATORS, key=len, reverse=True):
            if op in expr:
                parts = expr.split(op)
                if len(parts) != 2:
                    raise ValueError(f"Malformed expression: {expr}")
                return parts[0].strip(), op, parts[1].strip()
        raise ValueError(f"No valid operator found in: {expr}")

    def _match(self, segment, key, op_func, value):
        attr = getattr(segment, key, None)
        if attr is None:
            return False
        try:
            if isinstance(attr, (int, float)):
                value = float(value)
            return op_func(attr, value)
        except Exception:
            return False
