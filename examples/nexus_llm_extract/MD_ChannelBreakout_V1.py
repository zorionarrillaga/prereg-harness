# FORGE3 LLM-proposed primitive · MD_ChannelBreakout_V1
# status=LLM_PROPOSED_HUMAN_PATCHED · target_family=momentum_multiday
# paper_ids=['03_HAWKES_LEADLAG', '01_MICROSTRUCTURE', '049_ai_signal_engine_gemini_study']
#
# BP#47 N+18c audit patch (2026-04-21). Preserves the LLM's strategy
# concept (multi-day Donchian channel breakout with ATR volatility
# filter) — only the mechanical breakout-compare is fixed. The LLM
# computed `max_high = max(self.highs)` AFTER appending the current
# bar's high, then tested `bar.close > max_high + channel_width`.
# Because `close <= high <= max(highs including current)`, the long
# leg was unreachable for all params (and the short leg symmetrically
# unreachable). Standard Donchian semantics compare close against the
# PRIOR N-bar window, not N-including-self. Fix: `self.highs[:-1]` /
# `self.lows[:-1]` so the channel excludes the current bar. No other
# behavior change.
#
# The primitive_proposer prompt was also updated in the same session
# to warn future LLM proposals about this class of off-by-one (the
# channel window should not include the bar under evaluation).
#
# BP#47 N+23 audit patch (2026-04-24). Second structural bug: the
# breakout-buffer used `channel_width = (max_high - min_low) *
# width_mul` and required `close > max_high + channel_width`. With
# width_multiplier ∈ [1.0, 3.0] that means close must exceed the
# prior-channel high by 1× to 3× the FULL channel range — essentially
# never reachable (N+19 diagnostic: 0 trades on both sampled
# lookback_bars; N+23 diagnostic: still 0 trades post-N+22 R6
# mutation). Standard buffered-Donchian semantics: the buffer is a
# few ATRs above the high, not a multiple of the channel span. Fix:
# re-interpret `width_multiplier` as an ATR-units buffer applied to
# the prior-channel edge. This preserves the LLM's "filter micro
# breaks" intent, restores long + short leg reachability, and keeps
# §17.6 compliance (primitive implementation, not gate threshold).
class MultiDayChannelBreakout(_BaseStrategy):
    def __init__(self, params):
        super().__init__(params)
        self.highs = []
        self.lows = []
        self.trs = []
        self.prev_close = None

    def _true_range(self, bar):
        if self.prev_close is None:
            return bar.high - bar.low
        return max(
            bar.high - bar.low,
            abs(bar.high - self.prev_close),
            abs(bar.low - self.prev_close)
        )

    def on_bar(self, bar):
        intents = []

        # update rolling buffers
        self.highs.append(bar.high)
        self.lows.append(bar.low)
        self.trs.append(self._true_range(bar))

        lookback = int(self.params.get('lookback_bars', 2880))
        if len(self.highs) > lookback:
            self.highs.pop(0)
            self.lows.pop(0)
            self.trs.pop(0)

        # only evaluate when enough history exists
        if len(self.highs) == lookback:
            # BP#47 N+18c — compare against the PRIOR lookback-1 bars.
            # Including the current bar made the breakout test
            # unreachable (close <= high <= max(highs)).
            prior_highs = self.highs[:-1]
            prior_lows = self.lows[:-1]
            max_high = max(prior_highs)
            min_low = min(prior_lows)
            avg_tr = sum(self.trs) / lookback

            width_mul = float(self.params.get('width_multiplier', 1.5))
            vol_thr = float(self.params.get('volatility_threshold', 0.0))

            # optional volatility filter
            if avg_tr >= vol_thr:
                # BP#47 N+23 — buffer is `width_multiplier × avg_TR`
                # (ATR-units above the channel edge), not a multiple of
                # the channel range. See header docstring.
                vol_buffer = avg_tr * width_mul

                # long breakout
                if bar.close > max_high + vol_buffer:
                    intents.append(
                        Intent(direction='LONG', quantity=1, signal_price=float(bar.close))
                    )
                # short breakout
                elif bar.close < min_low - vol_buffer:
                    intents.append(
                        Intent(direction='SHORT', quantity=1, signal_price=float(bar.close))
                    )

        self.prev_close = bar.close
        return intents
