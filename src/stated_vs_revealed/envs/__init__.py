"""Explicit environment registry -- not auto-discovery. Adding an env is one
line here, nothing else in this package changes."""

from __future__ import annotations

from stated_vs_revealed.envs.eval_tampering import EvalTamperingEnv
from stated_vs_revealed.envs.funding_email import FundingEmailEnv

ENVS = {
    "funding_email": FundingEmailEnv(),
    "eval_tampering": EvalTamperingEnv(),
}
